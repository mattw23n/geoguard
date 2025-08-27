# GeoGuard System Verification & Setup Guide

## ✅ Code Verification Against Project Outline

Your existing code implementation **matches** the ProjectOutline.md specifications:

### Architecture Components ✅

- **App Structure**: All required modules present (`main.py`, `decision_head.py`, `router.py`, `retrieval.py`, `normalization.py`, `calibration.py`, `schema.py`, `storage.py`, `utils.py`)
- **Data Files**: Terminology, phrasebooks, regulations, synthetic dataset all present
- **Pipeline Stages**: Normalization → Router → Retrieval → LLM Decision Head → Calibration → Audit
- **Output Schema**: Pydantic models match JSON specification exactly
- **Gemini Integration**: Configured in `utils.py` for LLM calls
- **Docker Setup**: Dockerfile and docker-compose.yml present

### Missing/Optional Components (for future enhancement):

- ❌ `ui/streamlit_app.py` (Human-in-the-loop UI - marked as optional)
- ❌ `scripts/build_indices.py` and `scripts/train_router.py` (advanced features)
- ⚠️ Some advanced retrieval features (BM25/vector hybrid - simplified for MVP)

---

## 🚀 System Setup Guide

### Prerequisites

- Python 3.11+
- Gemini API key from Google AI Studio
- Git (for version control)
- Docker (optional, for containerized deployment)

### Step 1: Environment Setup

```bash
# Navigate to the geoguard directory
cd c:\Users\ztewk\OneDrive\zk\Personal Projects\TechJam25\t4-gov\geoguard

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file in the geoguard root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
CONFIDENCE_THRESHOLD=0.65
SELF_CONSISTENCY_RUNS=3
```

**Note**: Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Step 3: Verify Installation

```bash
# Test basic imports and schema
python -c "from app.main import app; print('✅ FastAPI app loaded successfully')"
python -c "from app.schema import FeatureOutput; print('✅ Schema models loaded')"
pytest tests/test_schema.py -v
```

---

## 🧪 Testing Guide

### 1. Unit Tests

```bash
# Run all tests
pytest tests/ -v
# OR
pytest -m pytest tests/ -v

# Run specific test files
pytest tests/test_schema.py -v          # Schema validation tests
pytest tests/test_end_to_end.py -v     # End-to-end pipeline tests
```

### 2. API Testing

#### Start the Server

```bash
# Method 1: Direct uvicorn
uvicorn app.main:app --reload --port 8000

# Method 2: Using Makefile
make dev

# Method 3: Docker
docker-compose up --build
```

#### Test Health Endpoint

```bash
curl http://localhost:8000/healthz
# Expected: {"status": "ok", "pipeline_version": "0.1.0"}
```

#### Test Classification Endpoint

**Positive Case (should return YES):**

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "feature_id": "F-001",
    "feature_name": "Curfew login blocker with ASL",
    "feature_description": "To comply with the Utah Social Media Regulation Act, we implement a curfew-based login restriction for minors."
  }'
```

**Negative Case (should return NO):**

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "feature_id": "F-002", 
    "feature_name": "South Korea dark theme A/B experiment",
    "feature_description": "A/B test dark theme accessibility for users in South Korea. Rollout is limited via GH and monitored with FR flags."
  }'
```

**Ambiguous Case (should return REVIEW):**

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "feature_id": "F-003",
    "feature_name": "A video filter available globally except KR", 
    "feature_description": "Feature is available in all regions except Korea; no legal rationale stated."
  }'
```

### 3. Batch Processing Test

```bash
# Process the synthetic dataset
python scripts/export_csv.py

# Check output
type out\geoguard_results.csv  # Windows
# or
cat out/geoguard_results.csv   # Linux/Mac
```

### 4. Audit Trail Verification

```bash
# Check audit logs are created
type audit\audit.jsonl  # Windows
# or  
cat audit/audit.jsonl   # Linux/Mac
```

---

## 🔍 System Validation Checklist

### Core Functionality ✅

- [ ] **Router Logic**: Phrasebook-based weak supervision works
- [ ] **Normalization**: Glossary expansion and geo-entity tagging
- [ ] **Retrieval**: Feature clause splitting and regulation section loading
- [ ] **LLM Integration**: Gemini API calls with structured prompts
- [ ] **Self-Consistency**: 3-run majority voting for decisions
- [ ] **Calibration**: Confidence score averaging
- [ ] **Audit Persistence**: All decisions logged to JSONL

### Expected Outputs ✅

- [ ] **Decision**: One of "YES", "NO", "REVIEW"
- [ ] **Confidence**: Float between 0.0-1.0
- [ ] **Evidence**: Feature spans and regulation snippets
- [ ] **Regulations**: Subset of target regulations
- [ ] **Control Types**: Age gating, reporting, etc.
- [ ] **Metadata**: Retrieval IDs and runtime info

### Test Cases ✅

- [ ] **Positive**: "ASL", "minors", "Utah Social Media" → YES
- [ ] **Negative**: "A/B test", "market experiment" → NO
- [ ] **Ambiguous**: No clear legal rationale → REVIEW

---

## 🐛 Troubleshooting

### Common Issues

**1. ModuleNotFoundError**

```bash
# Ensure you're in the geoguard directory
cd geoguard
# Install dependencies
pip install -r requirements.txt
```

**2. Gemini API Errors**

- Verify API key is set in `.env`
- Check internet connection
- Ensure API key has proper permissions

**3. File Not Found Errors**

```bash
# Verify data files exist
dir data\regulations\*.md     # Windows
ls data/regulations/*.md      # Linux/Mac
```

**4. Import Errors**

```bash
# Check Python path
python -c "import sys; print(sys.path)"
# Run from geoguard root directory
```

### Performance Notes

- First run may be slower due to Gemini API cold start
- Router short-circuits reduce LLM calls for obvious business cases
- Self-consistency runs 3 Gemini calls per classification

---

## 📊 Expected Results

Based on the synthetic dataset, you should see:

- **F-001** (Curfew/ASL/Utah): `decision: "YES"`, `regulations: ["UT-SMRA"]`
- **F-002** (A/B test/Korea): `decision: "NO"` (router short-circuit)
- **F-003** (Global except KR): `decision: "REVIEW"` (ambiguous)

The system is production-ready for MVP testing and can be extended with advanced retrieval, UI, and automation features as outlined in your project specification.
