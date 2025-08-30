import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timezone
from src.ai_core import get_ai_analysis, parse_llm_response, get_last_audit_meta
from src.db_utils import (
    get_all_features,
    get_feature_by_id,
    add_or_update_feature,
    add_scan,
    get_scans_for_feature,
    delete_features
)

LEGAL_DB_PATH = os.getenv("LEGAL_DB_PATH", os.path.join("data", "legal_db.json"))

@st.cache_data(show_spinner=False)
def load_legal_index(path: str = LEGAL_DB_PATH) -> dict:
    """Load legal_db.json and index it by rule id. Handles dict or list shapes."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    idx = {}
    if isinstance(data, list):
        for entry in data:
            if not isinstance(entry, dict):
                continue
            rid = str(entry.get("id") or entry.get("rule_id") or "").strip()
            if rid:
                e = dict(entry)
                e.setdefault("id", rid)
                idx[rid] = e
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                rid = str(v.get("id") or k).strip()
                e = dict(v)
                e.setdefault("id", rid)
                e.setdefault("title", str(k).replace("_", " ").title())
                idx[rid] = e
            else:
                # primitive value → treat as summary
                rid = str(k).strip()
                idx[rid] = {"id": rid, "title": str(k), "jurisdiction": "unspecified",
                            "severity": "medium", "summary": str(v)}
    return idx

LEGAL_INDEX = load_legal_index()

# --- Page Configuration ---
st.set_page_config(
    page_title="GeoGuard AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)
# Custom css
st.markdown("""
<style>
/* --- Regulation cards & chips --- */
.rule-card { background:#0f1116; border:1px solid #2a2f3a; border-radius:10px; padding:14px; margin:8px 0; }
.rule-title { font-weight:600; font-size:1.05rem; margin:0 0 6px 0; }
.rule-summary { margin-top:8px; line-height:1.4; color:#e7e7e7; }

.chips { margin:2px 0 0 0; }
.chip {
  display:inline-block; padding:3px 10px; border-radius:9999px;
  font-size:.75rem; margin-right:6px; margin-top:6px;
  border:1px solid #333; background:#1a1f2b; color:#c7d2fe;
}
.chip-id { background:#0d1f16; color:#b6f0c7; border-color:#1f5d3c; }
.chip-jur { background:#131b2c; color:#b9c9ff; border-color:#2c4c7a; }

/* severity colors */
.chip-sev { color:#fff; }
.chip-sev-low { background:#1f3d2a; border-color:#2b7a47; }
.chip-sev-medium { background:#3a3321; border-color:#a67c3d; }
.chip-sev-high { background:#3b2224; border-color:#a63d4a; }
.chip-sev-critical { background:#4a1f1f; border-color:#c0392b; }

/* verdict badge on triggered rules */
.badge { display:inline-block; padding:3px 8px; border-radius:6px; font-size:.75rem; font-weight:600; }
.badge-violated { background:#3b1a1e; color:#ffb3bd; border:1px solid #a23b49; }
.badge-na { background:#1f3a28; color:#b9f6ca; border:1px solid #2f7a4a; }
.badge-unclear { background:#3b331a; color:#ffe3a1; border:1px solid #a67c3d; }
</style>
""", unsafe_allow_html=True)

# --- Initialize Session State for Page Navigation ---
if "view" not in st.session_state:
    st.session_state.view = "list"  # 'list', 'detail', or 'batch_upload'
if "selected_feature_id" not in st.session_state:
    st.session_state.selected_feature_id = None
if "selected_feature_ids" not in st.session_state:
    st.session_state.selected_feature_ids = set()
if "select_all" not in st.session_state:
    st.session_state.select_all = False
    
def _sev_class(sev: str) -> str:
    s = (sev or "").lower()
    if s in ("critical", "crit"): return "chip-sev-critical"
    if s in ("high",): return "chip-sev-high"
    if s in ("medium", "med"): return "chip-sev-medium"
    return "chip-sev-low"

def render_regulation_card(rule_id: str, legal_index: dict):
    """Pretty card for a single regulation id using LEGAL_INDEX."""
    r = legal_index.get(rule_id)
    if not r:
        st.info(f"`{rule_id}` (not found in legal_db)")
        return
    title = r.get("title", rule_id)
    jur = r.get("jurisdiction", "unspecified")
    sev = r.get("severity", "medium")
    sev_cls = _sev_class(sev)
    summary = r.get("summary") or r.get("description") or ""

    with st.container():
        st.markdown(
            f"""
<div class="rule-card">
  <div class="rule-title">{title}</div>
  <div class="chips">
    <span class="chip chip-id">{rule_id}</span>
    <span class="chip chip-jur">Jurisdiction: {jur}</span>
    <span class="chip chip-sev {sev_cls}">Severity: {sev.title()}</span>
  </div>
  {'<div class="rule-summary">'+summary+'</div>' if summary else ''}
</div>
""",
            unsafe_allow_html=True,
        )

def render_triggered_rule_card(rule: dict, legal_index: dict):
    """Nicer layout for triggered_rules items with a verdict badge."""
    rule_id = rule.get("rule_id", "Unknown")
    verdict = (rule.get("verdict") or "unclear").lower()
    explanation = rule.get("explanation", "")

    meta = legal_index.get(rule_id, {})
    title = meta.get("title", rule_id)
    jur = meta.get("jurisdiction", "")
    sev = meta.get("severity", "")
    summary = meta.get("summary", "")

    if verdict == "violated":
        badge = '<span class="badge badge-violated">🚨 Violated</span>'
    elif verdict == "not_applicable":
        badge = '<span class="badge badge-na">✅ Not Applicable</span>'
    else:
        badge = f'<span class="badge badge-unclear">⚠️ {verdict.title()}</span>'

    with st.container():
        st.markdown(
            f"""
<div class="rule-card">
  <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;">
    <div class="rule-title">{title}</div>
    <div>{badge}</div>
  </div>
  <div class="chips">
    <span class="chip chip-id">{rule_id}</span>
    {'<span class="chip chip-jur">Jurisdiction: '+jur+'</span>' if jur else ''}
    {'<span class="chip chip-sev '+_sev_class(sev)+'">Severity: '+sev.title()+'</span>' if sev else ''}
  </div>
  {'<div class="rule-summary">'+summary+'</div>' if summary else ''}
  {'<div style="margin-top:8px;"><b>Model Explanation:</b> '+explanation+'</div>' if explanation else ''}
</div>
""",
            unsafe_allow_html=True,
        )


def _parse_scan_ts(scan):
    """Back-compat helper: parse timestamp_utc (preferred) or timestamp."""
    ts_str = scan.get("timestamp_utc") or scan.get("timestamp")
    if not ts_str:
        return None
    ts_str = ts_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def extract_text_from_file(uploaded_file):
    """Extract text content from various file formats"""
    try:
        file_type = uploaded_file.type
        file_name = uploaded_file.name.lower()

        if file_type == "text/plain" or file_name.endswith('.txt'):
            return uploaded_file.getvalue().decode('utf-8')

        elif file_type == "application/pdf" or file_name.endswith('.pdf'):
            st.warning("PDF support requires additional libraries. Please copy-paste the content or use a text file for now.")
            return None

        elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                          "application/msword"] or file_name.endswith(('.docx', '.doc')):
            st.warning("Word document support requires additional libraries. Please copy-paste the content or use a text file for now.")
            return None

        elif file_type == "application/json" or file_name.endswith('.json'):
            content = json.loads(uploaded_file.getvalue().decode('utf-8'))
            return json.dumps(content, indent=2)

        else:
            st.error(f"Unsupported file type: {file_type}")
            return None

    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None


def process_batch_csv(uploaded_file):
    """Process CSV file for batch feature upload"""
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()

        required_columns = ['title', 'description']
        optional_columns = ['prd', 'trd']

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns: {missing_columns}")
            st.info("Required columns: title, description")
            st.info("Optional columns: prd, trd")
            return None

        for col in optional_columns:
            if col not in df.columns:
                df[col] = ""

        df = df.fillna("")
        df = df[df['title'].str.strip() != ""]

        return df[['title', 'description', 'prd', 'trd']]

    except Exception as e:
        st.error(f"Error processing CSV file: {str(e)}")
        return None


def render_classification_badge(classification):
    """Renders a styled classification badge"""
    if classification == "YES":
        st.error(f"🚨 {classification}, requires legal compliance")
    elif classification == "NO":
        st.success(f"✅ {classification}, does not require legal compliance")
    elif classification == "UNSURE":
        st.warning(f"⚠️ {classification}, Human review required")
    else:
        st.info(f"❓ **Unknown:** {classification}")


def render_analysis_section(analysis):
    """Renders the AI analysis in a human-readable format with all available fields"""
    classification = analysis.get('classification', 'N/A')

    # Classification with appropriate styling
    st.subheader("📊 Assessment")
    render_classification_badge(classification)

    # (Removed confidence—LLM no longer returns it)

    # Reasoning section
    reasoning = analysis.get("reasoning", "No reasoning provided.")
    if reasoning and reasoning.strip():
        st.subheader("🧠 AI Reasoning")
        st.info(reasoning)

    regulation = (analysis.get("regulation") or "").strip()
    st.subheader("📋 Relevant Regulations")

    if regulation and regulation != "None":
        rule = LEGAL_INDEX.get(regulation)
        if rule:
            title = rule.get("title", regulation)
            jur = rule.get("jurisdiction", "unspecified")
            sev = rule.get("severity", "medium")
            sev_cls = _sev_class(sev)
            summary = rule.get("summary") or rule.get("description") or ""

            with st.container(border=True):
                st.markdown(
                    f"""
    <div class="rule-card">
    <div class="rule-title">{title}</div>
    <div class="chips">
        <span class="chip chip-id">{regulation}</span>
        <span class="chip chip-jur">Jurisdiction: {jur}</span>
        <span class="chip chip-sev {sev_cls}">Severity: {sev.title()}</span>
    </div>
    {'<div class="rule-summary">'+summary+'</div>' if summary else ''}
    </div>
    """,
                    unsafe_allow_html=True,
                )
        else:
            # Fallback if rule id not found in the local DB
            with st.container(border=True):
                st.info(regulation)
    else:
        st.caption("No specific regulation identified.")

    # --- Triggered rules ---
    triggered_rules = analysis.get("triggered_rules", [])
    if triggered_rules:
        st.subheader("⚖️ Triggered Compliance Rules")
        for rule in triggered_rules:
            with st.container(border=True):
                if isinstance(rule, dict):
                    rule_id = rule.get('rule_id', 'Unknown Rule')
                    verdict = (rule.get('verdict', 'unclear') or 'unclear').lower()
                    explanation = rule.get('explanation', 'No explanation provided')

                    meta = LEGAL_INDEX.get(rule_id, {})
                    title = meta.get("title", rule_id)
                    summary = meta.get("summary", "")
                    jur = meta.get("jurisdiction", "")
                    sev = meta.get("severity", "")
                    sev_cls = _sev_class(sev)

                    if verdict == "violated":
                        badge = '<span class="badge badge-violated">🚨 Violated</span>'
                    elif verdict == "not_applicable":
                        badge = '<span class="badge badge-na">✅ Not Applicable</span>'
                    else:
                        badge = f'<span class="badge badge-unclear">⚠️ {verdict.title()}</span>'

                    st.markdown(
                        f"""
<div class="rule-card">
<div style="display:flex;justify-content:space-between;gap:10px;align-items:center;">
    <div class="rule-title">{title}</div>
    <div>{badge}</div>
</div>
<div class="chips">
    <span class="chip chip-id">{rule_id}</span>
    {'<span class="chip chip-jur">Jurisdiction: '+jur+'</span>' if jur else ''}
    {'<span class="chip chip-sev '+sev_cls+'">Severity: '+sev.title()+'</span>' if sev else ''}
</div>
{'<div class="rule-summary">'+summary+'</div>' if summary else ''}
{'<div style="margin-top:8px;"><b>Model Explanation:</b> '+explanation+'</div>' if explanation else ''}
</div>
""",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f"• {rule}")

    # Recommendations
    recommendations = analysis.get("recommendations", [])
    if recommendations:
        st.subheader("💡 Recommendations")
        for rec in recommendations:
            st.markdown(f"• {rec}")

    # Raw analysis data (collapsible for debugging)
    with st.expander("🔍 Raw Analysis Data (Debug)", expanded=False):
        st.json(analysis)


def render_feature_snapshot(snapshot, key_prefix: str = "snapshot"):
    """Renders the feature snapshot in a readable format with unique widget keys."""
    st.subheader("📸 Feature State at Scan Time")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Title:**")
        st.code(snapshot.get("title", "N/A"))

        st.markdown("**Description:**")
        description = snapshot.get("description", "N/A")
        if len(description) > 100:
            # UNIQUE KEY per scan/instance
            st.text_area(
                "",
                value=description,
                height=100,
                disabled=True,
                key=f"{key_prefix}_desc"
            )
        else:
            st.code(description)

    with col2:
        st.markdown("**PRD Content:**")
        prd = snapshot.get("prd", "N/A")
        if len(prd) > 50:
            st.text_area(
                "",
                value=prd,
                height=80,
                disabled=True,
                key=f"{key_prefix}_prd"
            )
        else:
            st.code(prd if prd else "None")

        st.markdown("**TRD Content:**")
        trd = snapshot.get("trd", "N/A")
        if len(trd) > 50:
            st.text_area(
                "",
                value=trd,
                height=80,
                disabled=True,
                key=f"{key_prefix}_trd"
            )
        else:
            st.code(trd if trd else "None")


# ==============================================================================
#                           RENDER BATCH UPLOAD VIEW
# ==============================================================================
def render_batch_upload_view():
    """Renders the batch upload interface"""

    # Header with navigation
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back to Dashboard", type="secondary"):
            st.session_state.view = "list"
            st.rerun()

    with col2:
        st.title("📤 Batch Feature Upload")

    st.markdown("""
    Upload multiple features at once using a CSV file. This is perfect for importing
    existing feature lists or creating multiple features efficiently.
    """)

    # CSV Template Download
    st.markdown("### 📋 CSV Template")
    st.markdown("Your CSV file should have the following columns:")

    template_df = pd.DataFrame({
        'title': ['User Authentication System', 'Payment Processing Gateway'],
        'description': ['Secure login and user management functionality', 'Handle credit card payments and transactions'],
        'prd': ['Link to PRD document or content here', 'Payment PRD content'],
        'trd': ['Technical requirements for auth system', 'Payment technical specifications']
    })

    st.dataframe(template_df, use_container_width=True)

    csv_template = template_df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV Template",
        data=csv_template,
        file_name="geoguard_features_template.csv",
        mime="text/csv"
    )

    st.divider()

    st.markdown("### 📤 Upload Your Features")
    uploaded_csv = st.file_uploader(
        "Choose CSV file",
        type=['csv'],
        help="Upload a CSV file with your features. Required columns: title, description. Optional: prd, trd"
    )

    if uploaded_csv is not None:
        st.markdown("#### 👀 Preview")
        df = process_batch_csv(uploaded_csv)

        if df is not None:
            st.dataframe(df, use_container_width=True)
            st.success(f"✅ Found {len(df)} valid features in your CSV file")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Import All Features", type="primary", use_container_width=True):
                    imported_count = 0

                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    for index, row in df.iterrows():
                        status_text.text(f"Importing: {row['title']}")
                        feature_details = {
                            "id": None,
                            "title": row['title'],
                            "description": row['description'],
                            "prd": row['prd'],
                            "trd": row['trd'],
                        }
                        add_or_update_feature(feature_details)
                        imported_count += 1
                        progress_bar.progress((index + 1) / len(df))

                    status_text.empty()
                    progress_bar.empty()
                    st.success(f"🎉 Successfully imported {imported_count} features!")
                    st.session_state.import_completed = True
                    st.rerun()

                if getattr(st.session_state, 'import_completed', False):
                    if st.button("📊 View Dashboard", type="secondary", use_container_width=True):
                        st.session_state.view = "list"
                        st.session_state.import_completed = False
                        st.rerun()

            with col2:
                st.markdown("**Import Summary:**")
                st.info(f"• {len(df)} features ready to import\n• Duplicates will be skipped\n• All features will be saved to database")


# ==============================================================================
#                             RENDER DETAIL VIEW
# ==============================================================================
def render_detail_view():
    """Renders the page for viewing/editing/scanning a single feature."""

    # Header with navigation
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back to Dashboard", type="secondary"):
            st.session_state.view = "list"
            st.session_state.selected_feature_id = None
            st.rerun()

    with col2:
        st.title("⚖️ Feature Analysis & Management")

    current_feature = None
    if st.session_state.selected_feature_id:
        current_feature = get_feature_by_id(st.session_state.selected_feature_id)

    # --- Feature Details Form ---
    st.markdown("### 📝 Feature Information")

    title = st.text_input(
        "Feature Title",
        value=current_feature["title"] if current_feature else "",
        placeholder="Enter a descriptive title for your feature"
    )

    description = st.text_area(
        "Feature Description",
        value=current_feature["description"] if current_feature else "",
        height=120,
        placeholder="Describe what this feature does, its purpose, and key functionality"
    )

    st.markdown("### 📋 Related Documents")

    doc_col1, doc_col2 = st.columns(2)

    # PRD
    with doc_col1:
        st.markdown("#### Product Requirements Document (PRD)")
        prd_input_method = st.radio("PRD Input Method", ["Text Input", "File Upload"], key="prd_method", horizontal=True)
        prd_content = ""
        if prd_input_method == "Text Input":
            prd_content = st.text_area(
                "PRD Content/Link",
                value=current_feature["prd"] if current_feature else "",
                height=120,
                placeholder="Paste PRD content or provide a link to the document",
                key="prd_text"
            )
        else:
            prd_file = st.file_uploader("Upload PRD File", type=['txt', 'json', 'md'], key="prd_file",
                                        help="Supported formats: TXT, JSON, Markdown")
            if prd_file is not None:
                extracted_content = extract_text_from_file(prd_file)
                if extracted_content:
                    prd_content = extracted_content
                    st.success(f"✅ Loaded content from {prd_file.name}")
                    with st.expander("📄 Preview PRD Content"):
                        st.text_area("", value=prd_content[:500] + "..." if len(prd_content) > 500 else prd_content,
                                     height=100, disabled=True)
            else:
                prd_content = current_feature["prd"] if current_feature else ""

    # TRD
    with doc_col2:
        st.markdown("#### Technical Requirements Document (TRD)")
        trd_input_method = st.radio("TRD Input Method", ["Text Input", "File Upload"], key="trd_method", horizontal=True)
        trd_content = ""
        if trd_input_method == "Text Input":
            trd_content = st.text_area(
                "TRD Content/Link",
                value=current_feature["trd"] if current_feature else "",
                height=120,
                placeholder="Paste TRD content or provide a link to the document",
                key="trd_text"
            )
        else:
            trd_file = st.file_uploader("Upload TRD File", type=['txt', 'json', 'md'], key="trd_file",
                                        help="Supported formats: TXT, JSON, Markdown")
            if trd_file is not None:
                extracted_content = extract_text_from_file(trd_file)
                if extracted_content:
                    trd_content = extracted_content
                    st.success(f"✅ Loaded content from {trd_file.name}")
                    with st.expander("📄 Preview TRD Content"):
                        st.text_area("", value=trd_content[:500] + "..." if len(trd_content) > 500 else trd_content,
                                     height=100, disabled=True)
            else:
                trd_content = current_feature["trd"] if current_feature else ""

    st.divider()

    # --- Actions: Save and Scan ---
    action_col1, action_col2, action_col3 = st.columns([2, 2, 1])

    with action_col1:
        if st.button("💾 Save Feature", type="primary", use_container_width=True):
            if not title.strip():
                st.error("Please enter a feature title before saving.")
            else:
                feature_details = {
                    "id": st.session_state.selected_feature_id,
                    "title": title,
                    "description": description,
                    "prd": prd_content,
                    "trd": trd_content,
                }
                new_id = add_or_update_feature(feature_details)
                st.session_state.selected_feature_id = new_id
                st.success(f"✅ Feature '{title}' saved successfully!")
                st.rerun()

    with action_col2:
        scan_disabled = not st.session_state.selected_feature_id or not title.strip()
        if st.button("🔍 Run AI Compliance Scan", type="secondary", disabled=scan_disabled, use_container_width=True):
            with st.spinner("🤔 AI is analyzing your feature for compliance issues..."):
                feature_snapshot = {"title": title, "description": description, "prd": prd_content, "trd": trd_content}

                # Use latest ai_core semantics: terminology expansion looks at topic/description
                raw_response = get_ai_analysis("", feature_topic=title, feature_description=description)
                analysis = parse_llm_response(raw_response)

                # Minimal audit block from ai_core (no feature hashes/terminology paths)
                audit_meta = get_last_audit_meta() or {}

                add_scan(st.session_state.selected_feature_id, feature_snapshot, analysis, audit_meta=audit_meta)
                
                st.success("✅ Compliance scan completed and saved!")
                st.rerun()

    if scan_disabled and not st.session_state.selected_feature_id:
        st.caption("💡 Save the feature first to enable scanning")

    st.divider()

    # --- Display Scan History for Selected Feature ---
    st.markdown("### 📈 Compliance Scan History")

    if st.session_state.selected_feature_id:
        feature_scans = get_scans_for_feature(st.session_state.selected_feature_id)


        if not feature_scans:
            st.info("🔍 No compliance scans have been performed for this feature yet. Run your first scan above!")
        else:
            total_scans = len(feature_scans)
            high_risk_scans = sum(1 for scan in feature_scans if scan['analysis'].get('classification') == 'YES')
            latest_scan = feature_scans[0] if feature_scans else None

            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("Total Scans", total_scans)
            with metric_col2:
                st.metric("Compliance Needed for", high_risk_scans, delta=f"{high_risk_scans}/{total_scans}")
            with metric_col3:
                if latest_scan:
                    classification = latest_scan['analysis'].get('classification', 'N/A')

                    if classification == "YES":
                        status_text = "YES, Needs Compliance"
                    elif classification == "NO":
                        status_text = "NO, Compliant"
                    elif classification == "UNSURE":
                        status_text = "UNSURE, Review Required"
                    else:
                        status_text = "Unknown"
                    st.metric("Latest Status", status_text)

            st.divider()

            for i, scan in enumerate(feature_scans):
                scan_number = len(feature_scans) - i
                dt = _parse_scan_ts(scan)
                formatted_time = dt.strftime("%B %d, %Y at %I:%M %p") if dt else "N/A"
                classification = scan['analysis'].get('classification', 'N/A')

                if classification == "YES":
                    status_emoji = "🚨"; status_text = "Needs Compliance"
                elif classification == "NO":
                    status_emoji = "✅"; status_text = "Compliant"
                elif classification == "UNSURE":
                    status_emoji = "⚠️"; status_text = "Review Required"
                else:
                    status_emoji = "❓"; status_text = "Unknown"

                with st.expander(f"{status_emoji} Scan #{scan_number} - {status_text} ({formatted_time})",
                                 expanded=(i == 0)):
                    analysis_tab, snapshot_tab = st.tabs(["🔍 Analysis Results", "📸 Feature Snapshot"])

                    with analysis_tab:
                        render_analysis_section(scan["analysis"])

                        # --- AUDIT DETAILS DROPDOWN (all audit-related data lives here) ---
                        audit = scan.get("audit") or {}
                        with st.expander("📑 Audit Details", expanded=False):
                            if not audit:
                                st.caption("No audit metadata recorded for this scan.")
                            else:
                                left, right = st.columns(2)
                                with left:
                                    st.markdown(f"**Audit ID:** `{audit.get('audit_id', 'N/A')}`")
                                    st.markdown(f"**Status:** `{audit.get('status', 'N/A')}`")
                                    st.markdown(f"**Model:** `{audit.get('model', 'N/A')}`")
                                    st.markdown(f"**Prompt Included:** `{audit.get('prompt_included', False)}`")
                                with right:
                                    st.markdown(f"**Raw Output Hash:** `{audit.get('raw_output_hash', 'N/A')}`")
                                    st.markdown(f"**Legal DB Fingerprint:** `{audit.get('legal_db_fingerprint', 'N/A')}`")
                                    st.markdown(f"**Rules Context Fingerprint:** `{audit.get('rules_context_fingerprint', 'N/A')}`")

                                rules_ids = audit.get("rules_context_ids") or []
                                if rules_ids:
                                    st.markdown("**Rules Context IDs:**")
                                    st.code(", ".join(rules_ids), language="text")

                    with snapshot_tab:
                        render_feature_snapshot(
                            scan["feature_snapshot"],
                            key_prefix=f"scan_{scan.get('scan_id', i)}"
                        )
    else:
        st.info("💡 Save this feature to enable compliance scanning and view scan history.")


# ==============================================================================
#                               RENDER LIST VIEW
# ==============================================================================
def render_list_view():
    """Renders the home screen with a list of all created features."""

    # Styled header
    st.markdown("""
    <div class="main-header">
        <h1>⚖️ GeoGuard AI Feature Dashboard</h1>
        <p>Automated compliance scanning and risk assessment for product features</p>
    </div>
    """, unsafe_allow_html=True)

    # Quick action buttons
    button_col1, button_col2, button_col3 = st.columns([1, 1, 1])
    with button_col1:
        if st.button("➕ Create New Feature", type="primary", use_container_width=True):
            st.session_state.selected_feature_id = None
            st.session_state.view = "detail"
            st.rerun()
    with button_col2:
        if st.button("📤 Batch Upload Features", type="secondary", use_container_width=True):
            st.session_state.view = "batch_upload"
            st.rerun()
    with button_col3:
        st.markdown("")

    st.divider()

    features = get_all_features()

    if not features:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; color: #666;">
            <h3>🌟 Welcome to GeoGuard AI!</h3>
            <p>No features found yet. Create your first feature or upload multiple features using CSV.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        total_features = len(features)

        total_scans = 0
        high_risk_features = 0
        for feature in features:
            feature_scans = get_scans_for_feature(feature["id"])
            total_scans += len(feature_scans)
            if feature_scans and feature_scans[0]['analysis'].get('classification') == 'YES':
                high_risk_features += 1

        st.markdown("### 📊 Dashboard Overview")
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        with metric_col1:
            st.metric("Total Features", total_features)
        with metric_col2:
            st.metric("Total Scans", total_scans)
        with metric_col3:
            st.metric("Compliance Needed for", high_risk_features)
        with metric_col4:
            compliance_rate = round((total_features - high_risk_features) / total_features * 100, 1) if total_features > 0 else 0
            st.metric("Compliance Rate", f"{compliance_rate}%")

        st.divider()

        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_term = st.text_input("🔍 Search features", placeholder="Search by title or description...")
        with search_col2:
            status_filter = st.selectbox("Filter by Status", ["All", "Needs Compliance", "Compliant", "Not Scanned", "Review Required"])

        filtered_features = features
        if search_term:
            filtered_features = [
                f for f in filtered_features
                if search_term.lower() in f['title'].lower() or search_term.lower() in f.get('description', '').lower()
            ]

        if status_filter != "All":
            filtered_by_status = []
            for feature in filtered_features:
                feature_scans = get_scans_for_feature(feature["id"])
                if not feature_scans:
                    if status_filter == "Not Scanned":
                        filtered_by_status.append(feature)
                else:
                    latest_classification = feature_scans[0]['analysis'].get('classification', 'N/A')
                    if (status_filter == "Needs Compliance" and latest_classification == "YES") or \
                       (status_filter == "Compliant" and latest_classification == "NO") or \
                       (status_filter == "Review Required" and latest_classification == "UNSURE"):
                        filtered_by_status.append(feature)
            filtered_features = filtered_by_status

        # Selection and Delete Controls
        if filtered_features:
            st.markdown("### 🗂️ Feature Management")

            select_col1, select_col2, select_col3, select_col4 = st.columns([1, 1, 1, 1])

            with select_col1:
                select_all = st.checkbox("Select All", value=st.session_state.select_all, key="select_all_checkbox")
                if select_all != st.session_state.select_all:
                    st.session_state.select_all = select_all
                    if select_all:
                        st.session_state.selected_feature_ids = {f["id"] for f in filtered_features}
                    else:
                        st.session_state.selected_feature_ids = set()
                    st.rerun()

            selected_count = len(st.session_state.selected_feature_ids)

            with select_col3:
                if st.button("🗑️ Clear Selection", disabled=selected_count == 0):
                    st.session_state.selected_feature_ids = set()
                    st.session_state.select_all = False
                    st.rerun()

            with select_col4:
                if st.button(f"🗑️ Delete Selected ({selected_count})", type="secondary", disabled=selected_count == 0, use_container_width=True):
                    st.session_state.show_delete_confirmation = True
                    st.rerun()

            if getattr(st.session_state, 'show_delete_confirmation', False):
                with st.container(border=True):
                    st.error("⚠️ **Confirm Deletion**")
                    st.markdown(f"Are you sure you want to delete {selected_count} selected feature(s)? This action cannot be undone and will also delete all associated compliance scans.")

                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("✅ Yes, Delete", type="primary", use_container_width=True):
                            deleted_features, deleted_scans = delete_features(list(st.session_state.selected_feature_ids))
                            st.session_state.selected_feature_ids = set()
                            st.session_state.select_all = False
                            st.session_state.show_delete_confirmation = False
                            st.success(f"🗑️ Deleted {deleted_features} features and {deleted_scans} associated scans")
                            st.rerun()
                    with confirm_col2:
                        if st.button("❌ Cancel", use_container_width=True):
                            st.session_state.show_delete_confirmation = False
                            st.rerun()

            st.divider()

        st.markdown(f"### 📋 Features ({len(filtered_features)} of {len(features)})")

        for feature in filtered_features:
            feature_scans = get_scans_for_feature(feature["id"])
            latest_classification = "Not Scanned"
            last_scan_date = "Never"

            if feature_scans:
                dt = _parse_scan_ts(feature_scans[0])
                last_scan_date = dt.strftime("%m/%d/%Y") if dt else "N/A"
                latest_classification = feature_scans[0]['analysis'].get('classification', 'N/A')

            if latest_classification == "YES":
                status_emoji = "🚨"; status_text = "Needs Compliance"
            elif latest_classification == "NO":
                status_emoji = "✅"; status_text = "Compliant"
            elif latest_classification == "UNSURE":
                status_emoji = "⚠️"; status_text = "Review Required"
            else:
                status_emoji = "❓"; status_text = "Not Scanned"

            with st.container(border=True):
                row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([0.5, 2.5, 2, 2, 1])

                with row_col1:
                    is_selected = feature["id"] in st.session_state.selected_feature_ids
                    checkbox_changed = st.checkbox("", value=is_selected, key=f"select_{feature['id']}")
                    if checkbox_changed != is_selected:
                        if checkbox_changed:
                            st.session_state.selected_feature_ids.add(feature["id"])
                        else:
                            st.session_state.selected_feature_ids.discard(feature["id"])
                        st.session_state.select_all = len(st.session_state.selected_feature_ids) == len(filtered_features)
                        st.rerun()

                with row_col2:
                    st.markdown(f"**{feature['title']}**")
                    description_preview = feature.get('description', '')
                    if len(description_preview) > 100:
                        description_preview = description_preview[:100] + "..."
                    st.caption(description_preview if description_preview else "No description")

                with row_col3:
                    st.markdown(f"{status_emoji} **{status_text}**")
                    st.caption(f"ID: {feature['id']}")

                with row_col4:
                    st.markdown("**Last Scan:**")
                    st.caption(last_scan_date)
                    if feature_scans:
                        st.caption(f"({len(feature_scans)} total scans)")

                with row_col5:
                    if st.button("View →", key=f"view_{feature['id']}", use_container_width=True):
                        st.session_state.selected_feature_id = feature["id"]
                        st.session_state.view = "detail"
                        st.rerun()


# ==============================================================================
#                                 MAIN ROUTER
# ==============================================================================
with st.sidebar:
    st.markdown("### ℹ️ About GeoGuard AI")
    st.markdown("""
    This tool helps you:
    - 📝 Document product features
    - 📤 Batch upload via CSV
    - 📁 Upload PRD/TRD files
    - 🔍 Run AI compliance scans
    - 📊 Track assessments
    - 📈 Monitor compliance over time
    """)

    if st.session_state.view == "detail":
        st.divider()
        st.markdown("### 💡 Quick Tips")
        st.markdown("""
        - Save your feature before scanning
        - Upload files for larger documents
        - Include detailed descriptions for better AI analysis
        - Review scan history to track changes
        """)

    elif st.session_state.view == "batch_upload":
        st.divider()
        st.markdown("### 📤 CSV Format")
        st.markdown("""
        **Required columns:**
        - `title`: Feature name
        - `description`: What it does

        **Optional columns:**
        - `prd`: PRD content/link
        - `trd`: TRD content/link
        """)

# Main content routing
if st.session_state.view == "list":
    render_list_view()
elif st.session_state.view == "detail":
    render_detail_view()
elif st.session_state.view == "batch_upload":
    render_batch_upload_view()
