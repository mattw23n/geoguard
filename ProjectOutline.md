
# GeoGuard – From Guesswork to Governance

**Automating Geo‑Regulation detection with an LLM**

*(Hackathon spec – agent‑readable and implementation‑ready)*

---

## 0) Overview

**Goal:** Build an auditable service that reads feature artifacts (title, description, PRD/TRD excerpts) and flags whether the feature  **requires geo‑specific legal compliance logic** , explains  *why* , and cites evidence from both the feature text and a small regulation corpus.

**Primary outputs:** A structured JSON (and CSV for batch) containing:

* `decision` ∈ {`YES`, `NO`, `REVIEW`}
* short `reasoning_summary` (1–3 sentences, evidence‑anchored,  *no free‑form chain‑of‑thought* )
* `confidence` ∈ [0,1]
* `evidence` → quoted spans from feature + regulation passages
* `regulations` → subset of {`DSA`, `CA-SB976`, `FL-Minors`, `UT-SMRA`, `US-NCMEC`}
* `control_type` → subset of predefined controls (e.g., `age_gating`, `reporting`, `data_retention`, …)

**Non‑goals for MVP:** Full legal interpretation, real production data, or global regulation coverage beyond the five listed below.

---

## 1) Regulation Scope (MVP)

Use a small local corpus (plain text/markdown) of the following references (section‑ID indexed):

1. **EU Digital Services Act (DSA)**
2. **California SB‑976** – Protecting Our Kids from Social Media Addiction Act
3. **Florida – Online Protections for Minors** *(as provided via the brief’s reference)*
4. **Utah – Social Media Regulation Act (UT‑SMRA)**
5. **US – NCMEC reporting requirements** (providers must report CSAM)

> Store preprocessed text under `data/regulations/*.md` with hierarchical headings to enable section‑level retrieval.

---

## 2) Inputs

### 2.1 Feature Artifacts

* Fields: `feature_id`, `feature_name`, `feature_description` (+ optional PRD/TRD snippets)
* Source: **Synthetic dataset** provided in the hackathon materials.

### 2.2 Terminology Table (Glossary)

Create a **controlled vocabulary** to normalize internal jargon and codenames before inference.

Place in `data/terminology.yaml`:


# data/terminology.yaml

```yaml
# data/terminology.yaml
NR: "Not recommended (content/user status)"
PF: "Personalized feed"
GH: "Geo-handler; module for routing features by user region"
CDS: "Compliance Detection System"
DRT: "Data retention threshold; duration for which logs can be stored"
LCP: "Local compliance policy"
Redline: "Flag for legal review"
Softblock: "User-level limitation applied silently without notifications"
Spanner: "Synthetic name for a rule engine"
ShadowMode: "Deploy feature in non-user-impact way to collect analytics only"
T5: "Tier 5 sensitivity data; highly sensitive per internal taxonomy"
ASL: "Age-sensitive logic"
Glow: "Compliance flagging status used for geo-based alerts"
NSP: "Non-shareable policy (content should not be shared externally)"
Jellybean: "Internal parental control system"
EchoTrace: "Log tracing mode for compliance verification"
BB: "Baseline behavior used for anomaly detection"
Snowcap: "Child-safety policy framework"
FR: "Feature rollout status"
IMT: "Internal monitoring trigger"

```

---

## 3) Output Schema (authoritative)

Use **strict JSON** with enums. Validate with Pydantic/JSON Schema.

```json
{
  "feature_id": "string",
  "decision": "YES | NO | REVIEW",
  "confidence": 0.0,
  "reasoning_summary": "1-3 short sentences that reference evidence (no chain-of-thought).",
  "evidence": {
    "feature_spans": ["exact quote(s) from the feature text"],
    "reg_snippets": ["exact quote(s) from regulation text with section IDs, e.g., 'DSA §XYZ...'"]
  },
  "regulations": ["DSA", "CA-SB976", "FL-Minors", "UT-SMRA", "US-NCMEC"],
  "control_type": [
    "age_gating",
    "parental_consent",
    "reporting",
    "content_restriction",
    "data_localization",
    "data_retention",
    "notice_and_action",
    "delivery_constraints"
  ],
  "metadata": {
    "retrieval": {
      "feature_clause_ids": ["f:12", "f:21"],
      "reg_section_ids": ["dsa:IV.2.3", "ncmec:§2258A(b)"]
    },
    "runtime": {
      "pipeline_version": "semver",
      "prompt_version": "semver",
      "timestamp_utc": "ISO-8601"
    }
  }
}

```

**CSV export** (batch):

`feature_id,decision,confidence,reasoning_summary,regulations,control_type,evidence_feature_spans,evidence_reg_snippets`

---

## 4) System Architecture

### 4.1 Pipeline Stages

1. **Normalize**
   * Clean text, sentence split, and **expand jargon** using `terminology.yaml`.
   * Tag geographic entities (countries/regions) using spaCy + curated list.
2. **Dual Retrieval (Hybrid)**
   * **Clause‑level retrieval** from feature text (BM25 + vector).
   * **Regulation retrieval** (BM25 + vector) → top 3–5 sections with IDs.
   * Keep full text of chosen clauses/sections for citation.
3. **Decision Head (Multi‑Stage LLM)**
   * **Stage A – Detector:** distinguish **legal compliance** vs  **business geofence** . Output preliminary YES/NO + reason.
   * **Stage B – Policy Mapper:** if legal → map to `control_type` and candidate `regulations` using retrieved regs; cite passages.
   * **Stage C – Arbiter:** reconcile A/B; return final JSON with `confidence` and evidence spans.
4. **Calibration & Triage**
   * Temperature‑scaled or Platt‑scaled confidence.
   * If `confidence < THRESHOLD` or conflicts detected → `decision = REVIEW`.
5. **Persistence**
   * Store inputs, retrieval IDs, prompts, outputs, and hashes for audit.
6. **Human‑in‑the‑Loop UI (lite)**
   * Review queue for `REVIEW` and low‑confidence `YES`.
   * Review actions update phrasebooks and labeled data.
7. **Exporter**
   * Batch process CSV and save to `/out/geoguard_results.csv`.

---

## 5) Precision Boosters (must implement)

### 5.1 Phrasebooks

**Positive cues** (→ legal likelihood ↑):

* `age gate`, `underage`, `minors`, `parental consent`, `Jellybean`, `Snowcap`, `ASL`
* `report to NCMEC`, `CSAM`, `child sexual abuse`
* `data retention`, `retention threshold`, `DRT`
* `copyright blocking`, `notice and action`, `takedown`
* `local compliance policy (LCP)`, `geo‑handler (GH) enforcement`, `delivery constraint`

**Negative cues** (→ business geofence, not legal):

* `A/B test`, `variant test`, `market experiment`, `trial run`, `layout test`, `theme test`
* `creator fund payout`, `leaderboard`, `mood-based PF`, `rewards`, other engagement features without legal terms

Store as text lists:

```bash
data/phrasebook/positive.txt
data/phrasebook/negative.txt
```

### 5.2 Weak Supervision Router (cost + precision)

* Implement Snorkel‑style **labeling functions** (LFs) using phrasebooks + regex.
* Train a small classifier (e.g., `roberta-base`) on weak labels:
  * If **router** predicts “business geofence” with high confidence → short‑circuit to `NO`.
  * Else → route to LLM Decision Head.

### 5.3 Retrieval Grounding

* Use **Haystack** or **LlamaIndex** with FAISS/Qdrant + BM25.
* Restrict prompts to retrieved passages (feature + regulation). Refuse to cite unseen text.

### 5.4 Structured Prompting & Guardrails

* Require **JSON‑only** outputs (strict schema).
* Validate with Pydantic; on failure, **auto‑retry** with error‑aware prompt.

### 5.5 Self‑Consistency (n=3) & Majority Vote

* Run Arbiter `n=3` at low temperature.
* Majority vote for `decision`; average `confidence`.

### 5.6 Evidence‑First Justification

* Extract and return **exact quotes** for both:
  * `evidence.feature_spans`
  * `evidence.reg_snippets` (with section IDs)
* `reasoning_summary` must reference those quotes and avoid hidden reasoning.

### 5.7 Edge‑Case Rules

* If text contains both **positive** and **negative** cues without explicit legal phrasing, require strong regulation match; otherwise `REVIEW`.
* Do not output `YES` if **no geographic entity** is present *and* no regulation snippet matches.

---

## 6) API & CLI

### 6.1 REST (FastAPI)

**POST `/classify`**

* **Body:**
  ```json
  { "feature_id": "F-001", "feature_name": "...", "feature_description": "...", "prd": "", "trd": "" }
  ```
* **Response:** JSON object per schema above.

**POST `/batch`**

* **Body:** `{ "rows": [ {<same as /classify>}, ... ] }`
* **Response:** `{ "results": [ ... ], "csv_path": "/out/geoguard_results.csv" }`

**GET `/healthz`** → `{ "status": "ok", "pipeline_version": "..." }`

### 6.2 CLI

```bash
python scripts/build_indices.py --regs data/regulations --out .cache/indices
python scripts/train_router.py --in data/synthetic.csv --out models/router
python scripts/export_csv.py --in data/synthetic.csv --out out/geoguard_results.csv
```

---

## 7) Prompts (templates)

> Keep prompts short, cite **only** retrieved spans, and return  **schema‑valid JSON** . No chain‑of‑thought.

**Stage A – Detector**


```csharp
SYSTEM: You determine if a feature implies geo-specific LEGAL compliance logic (not business geofencing).
Use the glossary and retrieved feature clauses. Output YES or NO with a short evidence-based reason.
USER:
Glossary:
{{terminology_yaml}}Feature clauses (top-k):
{{feature_clauses}}Return JSON:
{"detector_decision":"YES|NO","reason":"1-2 sentences (cite a short feature quote)","feature_spans":["..."] }
```


**Stage B – Policy Mapper**


```css
SYSTEM: Map the feature to compliance control types and likely regulations.
Use ONLY the retrieved regulation sections. Quote exact snippets.USER:
Feature evidence:
{{feature_spans}}Regulation sections (top-k):
{{reg_sections_with_ids}}Return JSON:
{"control_type":["..."],"regulations":["..."],"reg_snippets":["exact quotes with section ids"],"reason":"1-2 sentences"}
```


**Stage C – Arbiter**


```makefile
SYSTEM: Produce the final decision with confidence.
Consider Detector + Policy Mapper outputs. If evidence is weak or conflicting, set decision=REVIEW.USER:
Detector: {{detector_json}}
PolicyMapper: {{policymapper_json}}Return JSON:
{
 "feature_id": "{{feature_id}}",
 "decision": "YES|NO|REVIEW",
 "confidence": 0.0-1.0,
 "reasoning_summary": "1-3 sentences; reference quoted evidence",
 "evidence": { "feature_spans": [...], "reg_snippets": [...] },
 "regulations": [...],
 "control_type": [...],
 "metadata": { "retrieval": {{retrieval_ids}}, "runtime": {{runtime_info}} }
}
```


---

## 8) Data Processing

1. **Text cleaning:** strip HTML, normalize unicode, sentence split (spaCy).
2. **Glossary expansion:** replace abbreviations with long forms; keep originals in parentheses.
3. **NER for geography:** custom dictionary (EU, EEA, France, CA, FL, UT, KR, etc.).
4. **Clause IDing:** index sentences/clauses as `f:<row_id>:<clause_idx>`.
5. **Regulation indexing:** parse headings to IDs (e.g., `dsa:IV.2.3`), store plain text for retrieval + citation.

---

## 9) Evaluation

* **Primary:** Cost‑sensitive F1, **FN penalty 3× FP**
* **Secondary:** AUPRC (positive = `YES`), ECE (calibration), % `REVIEW`, % outputs with non‑empty evidence.
* **Ablations:**
  * No retrieval vs retrieval
  * No phrasebooks vs phrasebooks
  * No calibration vs calibration
  * Router off vs on

**Acceptance criteria (MVP, synthetic set):**

* FN rate ≤ 10% (with FN penalty applied)
* ≥ 95% of `YES` outputs contain at least one valid regulation quote
* JSON validity = 100% (post‑retry)
* Batch run produces `out/geoguard_results.csv`

---

## 10) Repo Layout (create exactly)

```bash
/geoguard
  /app
    main.py                 # FastAPI app (endpoints)
    router.py               # weak supervision + roberta classifier
    decision_head.py        # Detector, PolicyMapper, Arbiter orchestration
    retrieval.py            # hybrid search (BM25 + vector)
    normalization.py        # glossary expansion, NER, clause splitting
    calibration.py          # temperature/Platt scaling; self-consistency vote
    schema.py               # Pydantic models & JSON schema
    storage.py              # audit trail persistence (jsonl)
    utils.py
  /ui
    streamlit_app.py        # review queue & inspection
  /data
    synthetic.csv           # provided dataset (placeholder)
    terminology.yaml        # glossary (authoritative)
    /phrasebook
      positive.txt
      negative.txt
    /regulations
      dsa.md
      ca_sb976.md
      fl_minors.md
      ut_smra.md
      us_ncmec.md
  /models
    /router                 # saved small classifier + tokenizer
  /scripts
    build_indices.py        # build hybrid indices
    train_router.py         # weak supervision + fine-tuning
    export_csv.py           # batch inference + CSV writer
    eval_notebook.ipynb     # optional for analysis
  /tests
    test_schema.py
    test_end_to_end.py
  Dockerfile
  docker-compose.yml
  Makefile
  README.md                 # this file
```

---

## 11) Makefile Targets


```makefile
setup:          ## install deps
	pip install -U pip
	pip install -r requirements.txt
dev:            ## run FastAPI + UI (local)
	uvicorn app.main:app --reload --port 8000
ui:
	streamlit run ui/streamlit_app.py
indices:
	python scripts/build_indices.py --regs data/regulations --out .cache/indices
train-router:
	python scripts/train_router.py --in data/synthetic.csv --out models/router
batch:
	python scripts/export_csv.py --in data/synthetic.csv --out out/geoguard_results.csv
```


---

## 12) Docker

**Dockerfile**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**

```yaml
version: "3.8"
services:
  geoguard:
    build: .
    volumes: [".:/app"]
    ports: ["8000:8000"]
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - EMBEDDING_MODEL=bge-small-en
      - VECTOR_STORE=faiss
```

---

## 13) Environment Variables

* `LLM_API_KEY` – provider key
* `EMBEDDING_MODEL` – default `bge-small-en`
* `VECTOR_STORE` – `faiss` (local) or `qdrant`
* `CONFIDENCE_THRESHOLD` – default `0.65`
* `SELF_CONSISTENCY_RUNS` – default `3`

---

## 14) Libraries & Tools

* **Serving/UI:** FastAPI, Uvicorn, Streamlit
* **Retrieval:** Haystack *or* LlamaIndex, FAISS/Qdrant, rank‑BM25
* **NLP:** spaCy, sentence‑transformers
* **Weak supervision:** Snorkel (optional), scikit‑learn, Hugging Face Transformers
* **Validation:** Pydantic
* **Calib/Eval:** scikit‑learn, (optional) Evidently
* **Dev:** Docker, pytest, Ruff/Black, pre‑commit

---

## 15) Human‑in‑the‑Loop UI (spec)

* **Inputs:** paste feature text or select row from dataset.
* **Display:**
  * Decision + confidence
  * Evidence (feature quotes + regulation snippets with section IDs)
  * Controls + regulations
  * Retrieval IDs, prompt versions
* **Actions:** “Confirm”, “Correct decision”, “Add note”, “Add phrase (pos/neg)”
* **Effect:** writes to `data/feedback/labels.jsonl` and updates phrasebooks.

---

## 16) Tests (minimum)

* **Schema validation** for all endpoints.
* **Deterministic regression** on a small fixture set:
  * **Positive:**
    * “Feature reads user location to enforce France’s copyright rules (download blocking)” → `YES`, includes `DSA`, control `content_restriction`.
    * “Requires age gates specific to Indonesia’s Child Protection Law” (treated as `age_gating`; since IND law not in corpus, expect `REVIEW` due to no supporting reg snippet).
  * **Negative:**
    * “Geofences feature rollout in US for market testing” → `NO`.
  * **Ambiguous:**
    * “A video filter feature is available globally except KR” → `REVIEW`.

---

## 17) Automation & Governance Loop

* Every reviewed case updates:
  * Phrasebooks (append terms),
  * Weak labels (Snorkel LFs),
  * Router fine‑tuning dataset,
  * Few‑shot examples for Detector/Mapper.
* Nightly script retrains router + rebuilds indices.

---

## 18) Security & Privacy

* Only synthetic data in repo.
* Do not log raw keys; redact in audit logs.
* Persist audit artifacts locally under `/audit/*.jsonl` with SHA‑256 of inputs.

---

## 19) Deliverables (per hackathon brief)

1. **Working solution** (dockerized; local run).
2. **Text description** (this README) including:
   * Development tools, APIs, assets, libraries, problem statement, datasets.
3. **Public GitHub repo** with `README.md`, quick‑start, and sample data.
4. **Demo video (<3 min)** – show UI, API call, CSV export, and audit trail.
   * Add link in README once uploaded:

     `Demo video: https://youtu.be/REPLACE_ME`
5. **CSV output** on test dataset: `out/geoguard_results.csv`.

---

## 20) Milestones (48‑hour plan)

**Day 1**

* Ingest synthetic dataset + glossary.
* Build regulation indices (BM25 + vector).
* Implement Detector → Policy Mapper → Arbiter with schema guardrails.
* Wire `/classify` and `/batch`. Export CSV.

**Day 2**

* Phrasebooks + weak‑supervision router.
* Confidence calibration + self‑consistency voting.
* Streamlit review UI + audit storage.
* Evaluation report + ablations; record demo video.

---

## 21) Problem Statement (for README completeness)

> As TikTok operates globally, every product feature must satisfy geographic regulations (e.g., GDPR, state laws). We need automated visibility into whether a feature **requires geo‑specific compliance logic** and why, to reduce governance costs, mitigate regulatory exposure, and enable audit‑ready transparency.

---

## 22) Example Records (for quick testing)

**Positive (legal):**

```vbnet
Feature: "Curfew login blocker with ASL"
Description: "To comply with the Utah Social Media Regulation Act, we implement a curfew-based login restriction for minors."
Expect: YES | control_type: ["age_gating"] | regulations: ["UT-SMRA"]
```

**Negative (business):**

```vbnet
Feature: "South Korea dark theme A/B experiment"
Description: "A/B test dark theme accessibility for users in South Korea. Rollout is limited via GH and monitored with FR flags."
Expect: NO
```

**Ambiguous:**

```vbnet
Feature: "A video filter available globally except KR"
Description: "Feature is available in all regions except Korea; no legal rationale stated."
Expect: REVIEW
```

---

## 23) Notes for Agentic Builders

* Prefer *deterministic preprocessing* (glossary expansion) before any LLM calls.
* Do not emit ungrounded reasoning. **Always cite quotes** from the feature and regulation text.
* If regulation retrieval returns nothing relevant, set `decision=REVIEW`.
* Keep prompts and outputs small; retry on schema violations automatically.

---

## 24) Placeholders to Update

* **Repository URL:** `https://github.com/<org>/geoguard`
* **Demo video URL:** `https://youtu.be/REPLACE_ME`
* **LLM provider/model:** set in `.env` or compose file.

---

### Quick Start

```bash
git clone https://github.com/<org>/geoguard
cd geoguard
cp .env.example .env   # add LLM_API_KEY
docker compose up --build
# then:
make indices
make train-router
make batch
# Visit: http://localhost:8000/healthz and run Streamlit UI

```

---

**End of README**
