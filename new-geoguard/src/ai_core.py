# src/ai_core.py
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import types as gen_types

# ----------------------- Config -----------------------
load_dotenv()

GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
LEGAL_DB_PATH = os.getenv("LEGAL_DB_PATH", os.path.join("data", "legal_db.json"))

# Deterministic for factual tasks (per TODO)
GEN_TEMPERATURE = float(os.getenv("GEN_TEMPERATURE", "0.1"))
GEN_MAX_TOKENS = int(os.getenv("GEN_MAX_TOKENS", "1200"))
RULES_TOP_K = int(os.getenv("RULES_TOP_K", "25"))  # reduce prompt noise

# Structured output schema: use only Gemini-safe keywords
RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["classification", "reasoning", "regulation"],
    "properties": {
        "classification": {"type": "string", "enum": ["YES", "NO", "UNSURE"]},
        "reasoning": {"type": "string"},
        "regulation": {"type": "string"},  # must be one of allowed IDs or "None" (validated post-gen)
        "confidence": {"type": "number"},  # clamp at runtime to [0,1]
        "triggered_rules": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["rule_id", "verdict", "explanation"],
                "properties": {
                    "rule_id": {"type": "string"},  # validated post-gen
                    "verdict": {"type": "string", "enum": ["violated", "not_applicable", "unclear"]},
                    "explanation": {"type": "string"},
                },
            },
        },
        "recommendations": {"type": "array", "items": {"type": "string"}},
    },
}

# ----------------------- Model init -----------------------
def _init_model() -> Optional[genai.GenerativeModel]:
    try:
        if not GOOGLE_API_KEY:
            return None
        genai.configure(api_key=GOOGLE_API_KEY)
        return genai.GenerativeModel(model_name=GEMINI_MODEL)
    except Exception:
        return None


_MODEL = _init_model()

# ----------------------- Legal context helpers -----------------------
def _load_legal_context() -> List[Dict[str, Any]]:
    """
    Load legal_db.json and normalize to a list of rule objects with at least:
    id, title, jurisdiction, severity, summary, keywords (optional)
    """
    try:
        with open(LEGAL_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    if isinstance(data, list):
        rules = data
    elif isinstance(data, dict):  # backward-compat with dict-shaped KBs
        rules = []
        for k, v in data.items():
            rule = v.copy() if isinstance(v, dict) else {"summary": str(v)}
            rule.setdefault("id", str(k))
            rule.setdefault("title", str(k))
            rule.setdefault("jurisdiction", "unspecified")
            rule.setdefault("severity", "medium")
            rule.setdefault("keywords", [])
            rules.append(rule)
    else:
        rules = []
    return rules


def _severity_weight(sev: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get((sev or "").lower(), 2)


def _score_rule(rule: Dict[str, Any], text_lc: str) -> float:
    """Crude relevance: keyword hits + tiny title/id boost + severity weight."""
    hits = 0
    for kw in rule.get("keywords", []) or []:
        if isinstance(kw, str) and kw.lower() in text_lc:
            hits += 2
    for f in ("id", "title"):
        val = str(rule.get(f, "")).lower()
        if val and val in text_lc:
            hits += 1
    return hits + 0.1 * _severity_weight(str(rule.get("severity", "medium")))


def _select_relevant_rules(feature_text: str, rules: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    if top_k <= 0 or top_k >= len(rules):
        return rules
    text_lc = (feature_text or "").lower()
    scored = sorted(rules, key=lambda r: _score_rule(r, text_lc), reverse=True)
    return scored[:top_k]


def _context_block(rules: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for r in rules:
        rid = r.get("id", "")
        title = r.get("title", "")
        jur = r.get("jurisdiction", "unspecified")
        sev = r.get("severity", "medium")
        summary = r.get("summary", "")
        lines.append(f"[{rid}] {title} ({jur}, {sev}): {summary}")
    return "\n".join(lines)


# ----------------------- Prompt -----------------------
def _build_master_prompt(feature_text: str, rules: List[Dict[str, Any]]) -> str:
    allowed_ids = ", ".join([str(r.get("id", "")) for r in rules if r.get("id")]) or "None"
    context_text = _context_block(rules)
    return f"""
You are a legal compliance analysis AI for a global tech company.

Your task: determine if the feature requires geo-specific **legal** compliance logic.
Always distinguish **legal obligations** from **business decisions** (e.g., market testing is a business decision, not a legal requirement).

STRICT CONSTRAINTS (follow exactly):
1) You **MUST** base your reasoning and any regulation citation **ONLY** on the information in the "REFERENCE LEGAL CONTEXT".
2) You **MUST NOT** invent or reference any law/regulation that is not present in the "REFERENCE LEGAL CONTEXT".
3) If the feature artifacts **explicitly mention** a law/regulation that is **NOT** present in the context, your classification **MUST** be "UNSURE".
   Your reasoning **MUST** state that a potential legal requirement was found but is not in your knowledge base.
4) When you cite a rule, use its **id** exactly as given. The only valid rule identifiers are: {allowed_ids}.
5) If no rule applies, set "regulation": "None" and explain briefly.

REFERENCE LEGAL CONTEXT:
{context_text}

FEATURE ARTIFACTS TO ANALYZE:
{feature_text}

Return ONLY a single valid JSON object with these keys:
- "classification": "YES" | "NO" | "UNSURE"
- "reasoning": short, plain-English rationale
- "regulation": one allowed rule id from the context above OR "None"
Optional (include when helpful):
- "confidence": number
- "triggered_rules": array of {{ "rule_id": <allowed id>, "verdict": "violated"|"not_applicable"|"unclear", "explanation": str }}
- "recommendations": array of short, actionable suggestions
""".strip()


# ----------------------- Low-level helpers -----------------------
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> Optional[str]:
    m = _JSON_RE.search(text or "")
    return m.group(0) if m else None


def _try_json_load(s: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(s)
    except Exception:
        return None


# ----------------------- Public API -----------------------
def get_ai_analysis(feature_text: str) -> Optional[str]:
    """
    Calls Gemini with strict prompt + low temperature and returns the model's raw JSON text.
    Returns a JSON string (never None) to keep downstream code simple.
    """
    if not _MODEL:
        return json.dumps({
            "classification": "UNSURE",
            "reasoning": "[MODEL_NOT_CONFIGURED] Missing or invalid GOOGLE_API_KEY.",
            "regulation": "None",
            "confidence": 0.0,
            "triggered_rules": [],
            "recommendations": []
        })

    all_rules = _load_legal_context()
    selected_rules = _select_relevant_rules(feature_text, all_rules, RULES_TOP_K)
    prompt = _build_master_prompt(feature_text, selected_rules)

    generation_config = gen_types.GenerationConfig(
        temperature=GEN_TEMPERATURE,                # lowered per TODO
        max_output_tokens=GEN_MAX_TOKENS,
        candidate_count=1,
        response_mime_type="application/json",      # JSON only
        response_schema=RESPONSE_SCHEMA,            # structured output
    )

    try:
        resp = _MODEL.generate_content(prompt, generation_config=generation_config)
        raw = getattr(resp, "text", "") or ""
    except Exception as e:
        # Fallback if schema validation is the issue: retry without response_schema but keep JSON MIME
        if "Schema" in str(e) or "schema" in str(e):
            try:
                fallback_cfg = gen_types.GenerationConfig(
                    temperature=GEN_TEMPERATURE,
                    max_output_tokens=GEN_MAX_TOKENS,
                    candidate_count=1,
                    response_mime_type="application/json",
                )
                resp = _MODEL.generate_content(prompt, generation_config=fallback_cfg)
                raw = getattr(resp, "text", "") or ""
            except Exception as e2:
                return json.dumps({
                    "classification": "UNSURE",
                    "reasoning": f"[LLM_CALL_FAILED] {e2}",
                    "regulation": "None",
                    "confidence": 0.0,
                    "triggered_rules": [],
                    "recommendations": []
                })
        else:
            return json.dumps({
                "classification": "UNSURE",
                "reasoning": f"[LLM_CALL_FAILED] {e}",
                "regulation": "None",
                "confidence": 0.0,
                "triggered_rules": [],
                "recommendations": []
            })

    # Defensive: extract JSON object if any extra prose leaked
    if not raw.strip().startswith("{"):
        candidate = _extract_json(raw)
        if candidate:
            raw = candidate

    if not raw:
        return json.dumps({
            "classification": "UNSURE",
            "reasoning": "[EMPTY_RESPONSE] Model returned no content.",
            "regulation": "None",
            "confidence": 0.0,
            "triggered_rules": [],
            "recommendations": []
        })

    return raw


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """
    Parses + validates the LLM response.
    - Ensures JSON shape.
    - Ensures cited rule ids appear in the current legal context.
    - If invalid citations are found, flips classification to "UNSURE" and amends reasoning.
    - Clamps confidence to [0, 1].
    """
    if not response_text:
        return {
            "classification": "ERROR",
            "reasoning": "No response from AI.",
            "regulation": "None",
        }

    text = response_text.strip()

    # Strip markdown fences if present
    if "```json" in text:
        try:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        except Exception:
            pass
    elif text.startswith("```") and text.endswith("```"):
        text = text.strip("`")

    payload = _try_json_load(text)
    if payload is None:
        candidate = _extract_json(text)
        payload = _try_json_load(candidate or "")
    if payload is None:
        return {
            "classification": "ERROR",
            "reasoning": "Failed to parse the AI's response. The format was invalid.",
            "regulation": "None",
        }

    # Normalize + validate
    rules = _load_legal_context()
    allowed_ids = {str(r.get("id", "")) for r in rules if r.get("id")}
    amended_reason_parts: List[str] = []

    # Classification normalization (map MAYBE->UNSURE defensively)
    cls = str(payload.get("classification", "UNSURE")).upper().strip()
    if cls == "MAYBE":
        cls = "UNSURE"
    if cls not in {"YES", "NO", "UNSURE"}:
        cls = "UNSURE"

    # Regulation validation
    regulation = payload.get("regulation", "None")
    if regulation not in allowed_ids and regulation != "None":
        amended_reason_parts.append(
            f"Cited regulation '{regulation}' is not in the reference context; setting classification to UNSURE."
        )
        regulation = "None"
        cls = "UNSURE"

    # Triggered rules validation
    trig = payload.get("triggered_rules", []) or []
    valid_trig = []
    invalid_found = False
    for item in trig:
        rid = str(item.get("rule_id", ""))
        if rid in allowed_ids:
            valid_trig.append(item)
        else:
            invalid_found = True
    if invalid_found:
        amended_reason_parts.append(
            "One or more triggered_rules referenced rules outside the reference context; they were dropped and classification set to UNSURE."
        )
        cls = "UNSURE"

    # Confidence clamp
    try:
        conf = float(payload.get("confidence", 0.5))
    except Exception:
        conf = 0.5
    conf = 0.0 if conf < 0 else 1.0 if conf > 1 else conf

    # Construct sanitized payload
    sanitized = {
        "classification": cls,
        "reasoning": payload.get("reasoning", ""),
        "regulation": regulation,
        "confidence": conf,
        "triggered_rules": valid_trig,
        "recommendations": payload.get("recommendations", []),
    }

    if amended_reason_parts:
        sanitized["reasoning"] = (sanitized["reasoning"] + " " + " ".join(amended_reason_parts)).strip()

    return sanitized
