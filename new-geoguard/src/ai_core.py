# src/ai_core.py
from __future__ import annotations

import json
import os
import re
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import types as gen_types

# ============================== Config ==============================
load_dotenv()

# NOTE: matches your current file (uses GEMINI_API_KEY)
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
LEGAL_DB_PATH = os.getenv("LEGAL_DB_PATH", os.path.join("data", "legal_db.json"))
TERMINOLOGY_PATH = os.getenv("TERMINOLOGY_PATH", os.path.join("data", "terminology.json"))

GEN_TEMPERATURE = float(os.getenv("GEN_TEMPERATURE", "0.1"))
GEN_MAX_TOKENS   = int(os.getenv("GEN_MAX_TOKENS", "1200"))

# Pass a shortlist of rules to the LLM (set 0 to pass all)
RULES_TOP_K = int(os.getenv("RULES_TOP_K", "12"))

# -------- Audit behaviour (no file writes; only return meta to DB) --------
# Kept as flags for UI display, but we never write snapshots to disk.
PROMPT_INCLUDED_IN_AUDIT  = True
CONTEXT_INCLUDED_IN_AUDIT = True

# Module-level cache so callers can fetch metadata to store in DB
_LAST_AUDIT_META: Optional[Dict[str, Any]] = None


# ============================ Utilities =============================
def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _sha256_text(s: str) -> str:
    return _sha256_bytes((s or "").encode("utf-8"))

def _file_sha256(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return _sha256_bytes(f.read())
    except Exception:
        return "unavailable"


# ======================= Model init (Gemini) ========================
def _init_model() -> Optional[genai.GenerativeModel]:
    try:
        if not GOOGLE_API_KEY:
            return None
        genai.configure(api_key=GOOGLE_API_KEY)
        return genai.GenerativeModel(model_name=GEMINI_MODEL)
    except Exception:
        return None

_MODEL = _init_model()


# ===================== Legal DB & Rule Selection =====================
_STOPWORDS = {
    "the","and","for","with","that","this","from","into","over","under","their","your","ours",
    "must","shall","should","will","would","can","could","may","might","not","none","about",
    "user","users","data","personal","service","services","platform","online","act","law",
    "laws","code","regulation","regulations","requirement","requirements","rule","rules"
}

def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", (s or "").strip().lower()).strip("_")

def _derive_keywords(title: str, summary: str, limit: int = 10) -> List[str]:
    text = f"{title} {summary}".lower()
    tokens = re.split(r"[^a-z0-9]+", text)
    out: List[str] = []
    seen = set()
    for t in tokens:
        if len(t) < 4:
            continue
        if t in _STOPWORDS:
            continue
        if t not in seen:
            out.append(t); seen.add(t)
        if len(out) >= limit:
            break
    return out

def _severity_weight(sev: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get((sev or "").lower(), 2)

def _normalize_rule(obj_key: str, value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        value = {"summary": str(value)}
    rid = value.get("id") or _slugify(obj_key)
    value["id"] = str(rid)
    value.setdefault("title", obj_key.replace("_", " ").title())
    value.setdefault("jurisdiction", "unspecified")
    value.setdefault("severity", "medium")
    value.setdefault("summary", "")
    if not value.get("keywords"):
        value["keywords"] = _derive_keywords(value.get("title", ""), value.get("summary", ""))
    return value

def _load_legal_context() -> List[Dict[str, Any]]:
    try:
        with open(LEGAL_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    rules: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            rule = _normalize_rule(str(k), v)
            if rule: rules.append(rule)
    elif isinstance(data, list):
        for i, v in enumerate(data):
            rule = _normalize_rule(str(v.get("id") or f"rule_{i}"), v)
            if rule: rules.append(rule)
    return rules

def _score_rule(rule: Dict[str, Any], text_lc: str) -> float:
    hits = 0
    for kw in rule.get("keywords", []) or []:
        if isinstance(kw, str) and kw.lower() in text_lc:
            hits += 2
    for f in ("id", "title"):
        val = str(rule.get(f, "")).lower()
        if val and val in text_lc:
            hits += 1
    return hits + 0.1 * _severity_weight(rule.get("severity", "medium"))

def _select_relevant_rules(feature_text: str, rules: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    text_lc = (feature_text or "").lower()
    ranked = sorted(rules, key=lambda r: _score_rule(r, text_lc), reverse=True)
    if top_k <= 0 or top_k >= len(rules):  # pass all
        return ranked
    return ranked[:top_k]

def _context_block(rules: List[Dict[str, Any]]) -> str:
    return "\n".join(
        f"[{r.get('id','')}] {r.get('title','')} ({r.get('jurisdiction','unspecified')}, {r.get('severity','medium')}): {r.get('summary','')}"
        for r in rules
    )


# ==================== Terminology (acronym/codename) =================
def _load_terminology() -> Dict[str, str]:
    try:
        with open(TERMINOLOGY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        terms: Dict[str, str] = {}
        for k, v in (data or {}).items():
            if isinstance(k, str) and isinstance(v, str):
                terms[k] = v
        return terms
    except Exception:
        return {}

_TERMINOLOGY = _load_terminology()

def _expand_terminology_text(text: str, terms: Dict[str, str]) -> Tuple[str, List[Dict[str, Any]]]:
    if not text or not terms:
        return text or "", []
    replaced_meta: List[Dict[str, Any]] = []
    for key in sorted(terms.keys(), key=lambda s: len(s), reverse=True):
        expansion = terms[key]
        pattern = re.compile(rf"(?<![A-Za-z0-9])({re.escape(key)})(?![A-Za-z0-9])", re.IGNORECASE)
        def _repl(m: re.Match) -> str:
            token = m.group(1)
            return f"{token} ({expansion})"
        new_text, count = pattern.subn(_repl, text)
        if count > 0:
            replaced_meta.append({"term": key, "expansion": expansion, "count": count})
            text = new_text
    return text, replaced_meta

def _prepare_feature_text(feature_text: str,
                          feature_topic: Optional[str],
                          feature_description: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    if feature_topic or feature_description:
        raw = f"Title: {feature_topic or ''}\n\nDescription: {feature_description or ''}".strip()
    else:
        raw = feature_text or ""
    expanded, replacements = _expand_terminology_text(raw, _TERMINOLOGY)
    meta = {
        "terminology_applied": replacements,  # not stored in DB; just useful for debugging if needed
    }
    return expanded, meta


# ============================ Prompt ================================
def _build_master_prompt(feature_text_normalized: str, rules: List[Dict[str, Any]]) -> str:
    allowed_ids = ", ".join([str(r.get("id", "")) for r in rules if r.get("id")]) or "None"
    context_text = _context_block(rules)
    return f"""
You are a legal compliance analysis AI for a global tech company.

Your task: determine if the feature requires geo-specific **legal** compliance logic.
Always distinguish **legal obligations** from **business decisions** (e.g., market testing is a business decision, not a legal requirement).

STRICT CONSTRAINTS (follow exactly):
1) You **MUST** base your reasoning and any regulation citation **ONLY** on the "REFERENCE LEGAL CONTEXT" below.
2) You **MUST NOT** invent or reference any law/regulation that is not present in the "REFERENCE LEGAL CONTEXT".
3) If the feature artifacts **explicitly mention** a law/regulation that is **NOT** present in the context, your classification **MUST** be "UNSURE".
   Your reasoning **MUST** state that a potential legal requirement was found but is not in your knowledge base.

LOCATION → JURISDICTION APPLICATION (do this within your reasoning):
A) Identify the **implementation location** of the feature (where it is deployed/hosted/rolled out). Prefer explicit statements such as
   country/state/province/city, cloud region names (e.g., "us-east-1" ⇒ United States), or phrases like "US-only rollout", "available in India".
B) If multiple locations are present, pick the **most specific** for analysis (state/province > country > regional bloc). If both implementation
   location and general references exist, **prioritize the implementation location**.
C) Apply rules **only when their jurisdiction equals, contains, or is contained by** the implementation location:
   - If a **state/province** is given and you have both state and country rules, prefer the **state** rule(s); country/region rules may also apply.
   - If only country-level rules exist for that location, those may apply to a state-level implementation.
D) If **no implementation location is stated**, your classification **MUST** be "UNSURE", "regulation" must be "None", and the reasoning must say
   that a location is required to determine legality for a jurisdiction.
E) If a location is stated but **no matching rule** exists in the reference context, classification **MUST** be "UNSURE" with "regulation":"None"
   and reasoning noting that the relevant jurisdiction is not represented in the context.

CITATION RULES:
- When you cite a rule, use its **id** exactly as given. The only valid ids are: {allowed_ids}.
- Mention **only rules you cite** in "regulation" or "triggered_rules". Do **not** list other rules in the reasoning.
- In your "reasoning", do not mention any law name, code, bill number, or acronym that is not in the REFERENCE LEGAL CONTEXT. 
- If you would otherwise need to reference one (e.g., "GDPR", "SB-976"), you MUST return "UNSURE" and explain that the relevant law is outside the reference context.

REFERENCE LEGAL CONTEXT:
{context_text}

FEATURE ARTIFACTS TO ANALYZE (terminology expanded inline):
{feature_text_normalized}

Return ONLY a single valid JSON object with these keys:
- "classification": "YES" | "NO" | "UNSURE"
- "reasoning": plain-English rationale focused on the implementation location and rule applicability
- "regulation": one allowed rule id from the context above OR "None"
Optional (include when helpful):
- "triggered_rules": array of {{ "rule_id": <allowed id>, "verdict": "violated"|"not_applicable"|"unclear", "explanation": str }}
- "recommendations": array of short, actionable suggestions
""".strip()


# ========================= JSON helpers ============================
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

def _extract_json(text: str) -> Optional[str]:
    m = _JSON_RE.search(text or "")
    return m.group(0) if m else None

def _try_json_load(s: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(s)
    except Exception:
        return None


# ====================== Rules fingerprint ==========================
def _rules_fingerprint(rules: List[Dict[str, Any]]) -> str:
    canon = [{
        "id": r.get("id", ""),
        "title": r.get("title", ""),
        "jurisdiction": r.get("jurisdiction", ""),
        "severity": r.get("severity", ""),
        "summary": r.get("summary", ""),
    } for r in sorted(rules, key=lambda x: x.get("id", ""))]
    return _sha256_text(json.dumps(canon, ensure_ascii=False, separators=(",", ":")))


# =========================== Public API ============================
def get_ai_analysis(feature_text: str,
                    feature_topic: Optional[str] = None,
                    feature_description: Optional[str] = None) -> str:
    """
    Calls Gemini with strict prompt + low temperature and returns the model's raw JSON text.
    No files are written. Minimal audit metadata is cached via get_last_audit_meta()
    so the caller can append it into database.json.
    """
    global _LAST_AUDIT_META
    _LAST_AUDIT_META = None

    audit_id = str(uuid.uuid4())
    normalized_text, _feature_meta = _prepare_feature_text(feature_text, feature_topic, feature_description)

        # Build rule context
    all_rules = _load_legal_context()
    selected_rules = _select_relevant_rules(normalized_text, all_rules, RULES_TOP_K)
    rules_ctx_ids = [r.get("id") for r in selected_rules]
    rules_ctx_fp  = _rules_fingerprint(selected_rules)
    legal_db_fp   = _file_sha256(LEGAL_DB_PATH)

    # Build prompt + (optional) snapshots
    context_snapshot_text = _context_block(selected_rules)  # used for optional audit snapshot
    prompt = _build_master_prompt(normalized_text, selected_rules)

    # Config
    generation_config = gen_types.GenerationConfig(
        temperature=GEN_TEMPERATURE,
        max_output_tokens=GEN_MAX_TOKENS,
        candidate_count=1,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
    )

    def _base_meta(status: str, raw_hash: Optional[str] = None) -> Dict[str, Any]:
        meta = {
            "audit_id": audit_id,
            "status": status,
            "model": GEMINI_MODEL,
            "legal_db_fingerprint": legal_db_fp,
            "rules_context_ids": rules_ctx_ids,
            "rules_context_fingerprint": rules_ctx_fp,
            "prompt_included": PROMPT_INCLUDED_IN_AUDIT,
            "context_text_included": CONTEXT_INCLUDED_IN_AUDIT,
        }
        if raw_hash is not None:
            meta["raw_output_hash"] = raw_hash
        # Snapshots only when flags are enabled
        if PROMPT_INCLUDED_IN_AUDIT:
            meta["prompt_snapshot"] = prompt
        if CONTEXT_INCLUDED_IN_AUDIT:
            meta["context_snapshot"] = context_snapshot_text
        return meta

    if not _MODEL:
        _LAST_AUDIT_META = _base_meta(status="error")
        return json.dumps({
            "classification": "UNSURE",
            "reasoning": "[MODEL_NOT_CONFIGURED] Missing GEMINI_API_KEY.",
            "regulation": "None",
            "triggered_rules": [],
            "recommendations": []
        })

    try:
        resp = _MODEL.generate_content(prompt, generation_config=generation_config)
        raw = getattr(resp, "text", "") or ""
        _LAST_AUDIT_META = _base_meta(status="ok", raw_hash=_sha256_text(raw))
    except Exception as e:
        _LAST_AUDIT_META = _base_meta(status="error")
        return json.dumps({
            "classification": "UNSURE",
            "reasoning": f"[LLM_CALL_FAILED] {e}",
            "regulation": "None",
            "triggered_rules": [],
            "recommendations": []
        })


    # Try to extract a JSON object if model included prose
    if not raw.strip().startswith("{"):
        candidate = _extract_json(raw)
        if candidate:
            raw = candidate

    if not raw:
        _LAST_AUDIT_META["status"] = "empty"
        return json.dumps({
            "classification": "UNSURE",
            "reasoning": "[EMPTY_RESPONSE] Model returned no content.",
            "regulation": "None",
            "triggered_rules": [],
            "recommendations": []
        })

    return raw


def get_last_audit_meta() -> Optional[Dict[str, Any]]:
    """Minimal audit metadata for storing in database.json (no files written)."""
    return _LAST_AUDIT_META


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """
    Parse & sanitize the LLM JSON.
    - No confidence field.
    - Validate 'regulation' and 'triggered_rules' against legal_db.
    - Reasoning: replace cited rule IDs with 'Title (`id`)', remove uncited IDs,
      and if external (unknown) law names/IDs appear, set classification to UNSURE.
    """
    if not response_text:
        return {
            "classification": "ERROR",
            "reasoning": "No response",
            "regulation": "None",
            "triggered_rules": [],
            "recommendations": [],
        }

    text = response_text.strip()
    # Strip code fences if the model returns ```json ... ```
    if "```json" in text:
        try:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        except Exception:
            pass
    elif text.startswith("```") and text.endswith("```"):
        text = text.strip("`")

    payload = _try_json_load(text) or _try_json_load(_extract_json(text) or "")
    if payload is None:
        return {
            "classification": "ERROR",
            "reasoning": "Invalid JSON",
            "regulation": "None",
            "triggered_rules": [],
            "recommendations": [],
        }

    # Load rules and build lookups
    rules = _load_legal_context()
    allowed_ids = {str(r.get("id", "")) for r in rules if r.get("id")}
    id_to_title = {str(r.get("id")): (r.get("title") or str(r.get("id"))) for r in rules if r.get("id")}
    allowed_titles = {(r.get("title") or "").lower() for r in rules}

    # Normalize classification
    cls = str(payload.get("classification", "UNSURE")).upper().strip()
    if cls not in {"YES", "NO", "UNSURE"}:
        cls = "UNSURE"

    # Validate 'regulation'
    regulation = payload.get("regulation", "None")
    extra_reason = ""
    if regulation not in allowed_ids and regulation != "None":
        regulation = "None"
        cls = "UNSURE"
        extra_reason = " Cited regulation is not in the reference context; set to UNSURE."

    # Validate & order 'triggered_rules'
    trig = payload.get("triggered_rules", []) or []
    def _rank(item: Dict[str, Any]) -> int:
        v = str(item.get("verdict", "")).lower()
        return {"violated": 0, "unclear": 1, "not_applicable": 2}.get(v, 3)
    valid_trig = [t for t in trig if str(t.get("rule_id", "")) in allowed_ids]
    valid_trig.sort(key=_rank)

    # Build set of actually cited IDs (for formatting)
    cited_ids = set()
    if regulation != "None":
        cited_ids.add(regulation)
    cited_ids.update({str(t.get("rule_id")) for t in valid_trig})

    # ----- Reasoning cleanup & external-law guard -----
    reasoning = (payload.get("reasoning", "") or "").strip()

    # 1) Replace cited IDs with 'Title (`id`)' so prose is human-friendly
    for rid in cited_ids:
        title = id_to_title.get(rid, rid)
        reasoning = re.sub(rf"\b{re.escape(rid)}\b", f"{title} (`{rid}`)", reasoning)

    # 2) Detect any external-law mentions (not in our legal_db)
    #    - common legal acronyms
    LEGAL_ACRONYMS = r"\b(GDPR|CCPA|CPRA|COPPA|HIPAA|PIPEDA|AADC|DMA|DSA|FERPA|LGPD|PDPA)\b"
    #    - bill patterns like SB-123, SB 123, HB 5678, AB 34
    BILL_PATTERN = r"\b(?:SB|HB|AB|LB)\s?-?\s?\d{2,5}\b"
    #    - generic 'Act|Regulation|Code|Directive' when paired with a proper noun before it
    GENERIC_LAW = r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,4})\s(?:Act|Regulation|Code|Directive)\b"

    external_hits = []
    for pat in (LEGAL_ACRONYMS, BILL_PATTERN, GENERIC_LAW):
        for m in re.finditer(pat, reasoning):
            hit = m.group(0)
            # ignore if this hit corresponds to one of our allowed titles/ids
            if hit.lower() in allowed_titles:
                continue
            if hit in allowed_ids:
                continue
            external_hits.append(hit)

    # 3) Remove any uncited allowed IDs mentioned accidentally
    for rid in (allowed_ids - cited_ids):
        reasoning = re.sub(rf"\b{re.escape(rid)}\b", "", reasoning)

    # 4) If external hits exist, we make the verdict UNSURE and note why
    if external_hits:
        cls = "UNSURE"
        for h in external_hits:
            reasoning = reasoning.replace(h, "").strip()
        ext_list = ", ".join(sorted(set(external_hits)))
        extra_reason = (extra_reason + " External law reference(s) removed: "
                        f"{ext_list}. Not in reference context; set to UNSURE.").strip()

    # 5) Normalize whitespace after removals
    reasoning = re.sub(r"\s{2,}", " ", reasoning).strip()

    if extra_reason:
        reasoning = (reasoning + " " + extra_reason).strip()

    return {
        "classification": cls,
        "reasoning": reasoning,
        "regulation": regulation,
        "triggered_rules": valid_trig,
        "recommendations": payload.get("recommendations", []),
    }


# ===================== Response schema (Gemini) =====================
RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["classification", "reasoning", "regulation"],
    "properties": {
        "classification": {"type": "string", "enum": ["YES", "NO", "UNSURE"]},
        "reasoning": {"type": "string"},
        "regulation": {"type": "string"},
        "triggered_rules": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["rule_id", "verdict", "explanation"],
                "properties": {
                    "rule_id": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["violated", "not_applicable", "unclear"]},
                    "explanation": {"type": "string"},
                },
            },
        },
        "recommendations": {"type": "array", "items": {"type": "string"}},
    },
}
