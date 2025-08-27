"""
GeoGuard Professional Web Interface

A comprehensive Streamlit UI for the GeoGuard compliance detection system.
Provides single feature classification, batch processing, audit trail viewing,
and system management capabilities.
"""

import streamlit as st
import pandas as pd
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Add parent directory to path for app imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

try:
    from app.decision_head import classify_feature, batch_classify
    from app.schema import FeatureInput
    from scripts.generate_results import main as generate_batch_results
except ImportError as e:
    st.error(f"❌ Import error: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="GeoGuard - Compliance Detection System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79 0%, #2d5aa0 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f4e79;
        margin: 0.5rem 0;
    }
    .decision-yes {
        background-color: #d4edda;
        color: #155724;
        padding: 0.5rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    .decision-no {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
    .decision-review {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.5rem;
        border-radius: 5px;
        border: 1px solid #ffeaa7;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
</style>
""", unsafe_allow_html=True)

def load_audit_logs():
    """Load audit logs from jsonl file"""
    audit_path = parent_dir / "audit" / "audit.jsonl"
    if not audit_path.exists():
        return []
    
    logs = []
    try:
        with open(audit_path, 'r') as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
    except Exception as e:
        st.error(f"Error loading audit logs: {e}")
    return logs

def format_decision(decision):
    """Format decision with appropriate styling"""
    if decision == "YES":
        return '<div class="decision-yes">✅ YES - Legal Compliance Required</div>'
    elif decision == "NO":
        return '<div class="decision-no">❌ NO - Business Geofence</div>'
    elif decision == "REVIEW":
        return '<div class="decision-review">⚠️ REVIEW - Human Evaluation Needed</div>'
    else:
        return f'<div class="decision-review">❓ {decision}</div>'

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🛡️ GeoGuard</h1>
        <h3>Automated Geo-Regulation Compliance Detection</h3>
        <p>From Guesswork to Governance with LLM-powered Analysis</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar navigation
    st.sidebar.title("🚀 Navigation")
    page = st.sidebar.selectbox(
        "Select Feature",
        ["🔍 Single Classification", "📊 Batch Processing", "📋 Audit Trail", "⚙️ System Status", "📚 Documentation"]
    )

    if page == "🔍 Single Classification":
        single_classification_page()
    elif page == "📊 Batch Processing":
        batch_processing_page()
    elif page == "📋 Audit Trail":
        audit_trail_page()
    elif page == "⚙️ System Status":
        system_status_page()
    elif page == "📚 Documentation":
        documentation_page()

def single_classification_page():
    """Single feature classification interface"""
    st.header("🔍 Single Feature Classification")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Feature Input")
        
        # Input form
        with st.form("feature_form"):
            feature_id = st.text_input("Feature ID", value="F-DEMO", help="Unique identifier for the feature")
            feature_name = st.text_input("Feature Name", value="", help="Human-readable name of the feature")
            feature_description = st.text_area(
                "Feature Description", 
                value="",
                height=150,
                help="Detailed description of the feature functionality"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                prd = st.text_area("PRD Excerpt (Optional)", height=100)
            with col_b:
                trd = st.text_area("TRD Excerpt (Optional)", height=100)
            
            submitted = st.form_submit_button("🚀 Classify Feature", type="primary")
        
        # Quick examples
        st.subheader("💡 Quick Examples")
        
        examples = {
            "Legal Compliance (Utah)": {
                "id": "F-001",
                "name": "Curfew login blocker with ASL",
                "desc": "To comply with the Utah Social Media Regulation Act, we implement a curfew-based login restriction for minors."
            },
            "Business Geofence": {
                "id": "F-002", 
                "name": "South Korea dark theme A/B experiment",
                "desc": "A/B test dark theme accessibility for users in South Korea. Rollout is limited via GH and monitored with FR flags."
            },
            "Ambiguous Case": {
                "id": "F-003",
                "name": "Video filter - Global except KR",
                "desc": "Feature is available in all regions except Korea; no legal rationale stated."
            }
        }
        
        example_choice = st.selectbox("Load Example:", ["Select an example..."] + list(examples.keys()))
        
        if example_choice != "Select an example...":
            example = examples[example_choice]
            st.session_state.example_id = example["id"]
            st.session_state.example_name = example["name"]
            st.session_state.example_desc = example["desc"]
            st.rerun()
        
        # Use session state for examples
        if 'example_id' in st.session_state:
            feature_id = st.session_state.example_id
            feature_name = st.session_state.example_name
            feature_description = st.session_state.example_desc
            # Clear after use
            del st.session_state.example_id
            del st.session_state.example_name
            del st.session_state.example_desc
    
    with col2:
        st.subheader("🎯 Classification Rules")
        st.info("""
        **YES - Legal Compliance:**
        - Age gating requirements
        - Data retention policies
        - CSAM reporting obligations
        - Geographic content restrictions
        
        **NO - Business Geofence:**
        - A/B testing
        - Market experiments
        - Performance optimization
        - User experience trials
        
        **REVIEW - Unclear:**
        - Ambiguous legal rationale
        - Mixed business/legal signals
        - Insufficient information
        """)
    
    # Process classification
    if submitted and feature_description:
        with st.spinner("🔄 Analyzing feature for compliance requirements..."):
            try:
                payload = {
                    "feature_id": feature_id,
                    "feature_name": feature_name,
                    "feature_description": feature_description,
                    "prd": prd,
                    "trd": trd
                }
                
                result = classify_feature(payload)
                
                # Display results
                st.success("✅ Classification Complete!")
                
                # Decision banner
                st.markdown(format_decision(result["decision"]), unsafe_allow_html=True)
                
                # Metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Confidence Score", f"{result['confidence']:.2%}")
                with col2:
                    st.metric("Regulations Found", len(result.get('regulations', [])))
                with col3:
                    st.metric("Control Types", len(result.get('control_type', [])))
                
                # Detailed results
                st.subheader("📋 Detailed Analysis")
                
                tab1, tab2, tab3, tab4 = st.tabs(["Reasoning", "Evidence", "Regulations", "Metadata"])
                
                with tab1:
                    st.write("**Reasoning Summary:**")
                    st.write(result.get("reasoning_summary", "No reasoning provided"))
                
                with tab2:
                    st.write("**Feature Evidence:**")
                    evidence = result.get("evidence", {})
                    for span in evidence.get("feature_spans", []):
                        st.code(span)
                    
                    st.write("**Regulation Snippets:**")
                    for snippet in evidence.get("reg_snippets", []):
                        st.code(snippet)
                
                with tab3:
                    if result.get("regulations"):
                        st.write("**Applicable Regulations:**")
                        for reg in result["regulations"]:
                            st.write(f"• {reg}")
                    
                    if result.get("control_type"):
                        st.write("**Control Types:**")
                        for control in result["control_type"]:
                            st.write(f"• {control}")
                
                with tab4:
                    st.json(result.get("metadata", {}))
                
            except Exception as e:
                st.error(f"❌ Classification failed: {str(e)}")
    
    elif submitted and not feature_description:
        st.warning("⚠️ Please provide a feature description to classify.")

def batch_processing_page():
    """Batch processing interface"""
    st.header("📊 Batch Processing")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📁 Dataset Management")
        
        # Current dataset info
        synthetic_path = parent_dir / "data" / "synthetic.csv"
        if synthetic_path.exists():
            df = pd.read_csv(synthetic_path)
            st.success(f"✅ Loaded synthetic dataset: {len(df)} features")
            
            with st.expander("📋 View Dataset"):
                st.dataframe(df, use_container_width=True)
        else:
            st.error("❌ Synthetic dataset not found!")
            return
        
        # Batch processing controls
        st.subheader("🚀 Batch Operations")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("▶️ Run Batch Classification", type="primary"):
                with st.spinner("🔄 Processing all features..."):
                    try:
                        generate_batch_results()
                        st.success("✅ Batch processing complete!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ Batch processing failed: {e}")
        
        with col_b:
            results_path = parent_dir / "out" / "geoguard_results.csv"
            if results_path.exists():
                with open(results_path, 'rb') as f:
                    st.download_button(
                        "⬇️ Download Results CSV",
                        f.read(),
                        file_name="geoguard_results.csv",
                        mime="text/csv"
                    )
    
    with col2:
        st.subheader("📈 Processing Status")
        
        # Check for existing results
        results_path = parent_dir / "out" / "geoguard_results.csv"
        if results_path.exists():
            results_df = pd.read_csv(results_path)
            
            st.metric("Total Processed", len(results_df))
            
            # Decision distribution
            decision_counts = results_df['decision'].value_counts()
            
            fig = px.pie(
                values=decision_counts.values,
                names=decision_counts.index,
                title="Decision Distribution",
                color_discrete_map={
                    'YES': '#28a745',
                    'NO': '#dc3545', 
                    'REVIEW': '#ffc107',
                    'ERROR': '#6c757d'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Confidence distribution
            fig2 = px.histogram(
                results_df,
                x='confidence',
                title="Confidence Score Distribution",
                nbins=10
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("📋 No results available. Run batch processing to generate results.")
    
    # Results viewer
    if results_path.exists():
        st.subheader("📊 Results Viewer")
        
        results_df = pd.read_csv(results_path)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            decision_filter = st.selectbox("Filter by Decision:", ["All"] + list(results_df['decision'].unique()))
        with col2:
            min_confidence = st.slider("Min Confidence:", 0.0, 1.0, 0.0)
        with col3:
            max_confidence = st.slider("Max Confidence:", 0.0, 1.0, 1.0)
        
        # Apply filters
        filtered_df = results_df.copy()
        if decision_filter != "All":
            filtered_df = filtered_df[filtered_df['decision'] == decision_filter]
        filtered_df = filtered_df[
            (filtered_df['confidence'] >= min_confidence) & 
            (filtered_df['confidence'] <= max_confidence)
        ]
        
        st.dataframe(filtered_df, use_container_width=True)

def audit_trail_page():
    """Audit trail viewer"""
    st.header("📋 Audit Trail")
    
    logs = load_audit_logs()
    
    if not logs:
        st.info("📝 No audit logs available. Process some features to generate audit trail.")
        return
    
    st.success(f"📊 Loaded {len(logs)} audit entries")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    decisions = [log.get('decision') for log in logs]
    with col1:
        st.metric("Total Classifications", len(logs))
    with col2:
        st.metric("YES Decisions", decisions.count('YES'))
    with col3:
        st.metric("NO Decisions", decisions.count('NO'))
    with col4:
        st.metric("REVIEW Decisions", decisions.count('REVIEW'))
    
    # Timeline chart
    if logs:
        timestamps = []
        decisions = []
        for log in logs:
            runtime = log.get('metadata', {}).get('runtime', {})
            timestamp = runtime.get('timestamp_utc')
            if timestamp:
                timestamps.append(timestamp)
                decisions.append(log.get('decision', 'UNKNOWN'))
        
        if timestamps:
            df_timeline = pd.DataFrame({
                'timestamp': pd.to_datetime(timestamps),
                'decision': decisions
            })
            
            fig = px.scatter(
                df_timeline,
                x='timestamp',
                y='decision',
                color='decision',
                title="Classification Timeline",
                color_discrete_map={
                    'YES': '#28a745',
                    'NO': '#dc3545',
                    'REVIEW': '#ffc107'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Detailed logs
    st.subheader("🔍 Detailed Audit Logs")
    
    for i, log in enumerate(reversed(logs[-50:]), 1):  # Show last 50 entries
        with st.expander(f"Entry {i}: {log.get('feature_id', 'Unknown')} - {log.get('decision', 'Unknown')}"):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.write("**Basic Info:**")
                st.write(f"Feature ID: {log.get('feature_id', 'N/A')}")
                st.write(f"Decision: {log.get('decision', 'N/A')}")
                st.write(f"Confidence: {log.get('confidence', 0):.2%}")
                st.write(f"Reasoning: {log.get('reasoning_summary', 'N/A')}")
            
            with col2:
                st.write("**Metadata:**")
                st.json(log.get('metadata', {}))

def system_status_page():
    """System status and health check"""
    st.header("⚙️ System Status")
    
    # Health checks
    st.subheader("🔍 System Health Checks")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Core Components:**")
        
        # Check imports
        try:
            from app.decision_head import classify_feature
            st.success("✅ Decision Head Module")
        except:
            st.error("❌ Decision Head Module")
        
        try:
            from app.router import router_decision
            st.success("✅ Router Module")
        except:
            st.error("❌ Router Module")
        
        try:
            from app.retrieval import retrieve_feature_clauses
            st.success("✅ Retrieval Module")
        except:
            st.error("❌ Retrieval Module")
    
    with col2:
        st.write("**Data Files:**")
        
        # Check data files
        data_files = [
            ("Terminology", "data/terminology.yaml"),
            ("Positive Phrasebook", "data/phrasebook/positive.txt"),
            ("Negative Phrasebook", "data/phrasebook/negative.txt"),
            ("Synthetic Dataset", "data/synthetic.csv")
        ]
        
        for name, path in data_files:
            if (parent_dir / path).exists():
                st.success(f"✅ {name}")
            else:
                st.error(f"❌ {name}")
    
    # Environment info
    st.subheader("🌐 Environment Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    with col2:
        st.metric("Streamlit Version", st.__version__)
    
    with col3:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            st.success("🔑 Gemini API Key Set")
        else:
            st.warning("⚠️ Gemini API Key Missing")
    
    # Performance stats
    st.subheader("📊 Performance Statistics")
    
    logs = load_audit_logs()
    if logs:
        # Calculate average confidence by decision type
        decision_confidence = {}
        for log in logs:
            decision = log.get('decision')
            confidence = log.get('confidence', 0)
            if decision not in decision_confidence:
                decision_confidence[decision] = []
            decision_confidence[decision].append(confidence)
        
        for decision, confidences in decision_confidence.items():
            avg_confidence = sum(confidences) / len(confidences)
            st.metric(f"Avg Confidence ({decision})", f"{avg_confidence:.2%}")

def documentation_page():
    """Documentation and help"""
    st.header("📚 Documentation")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Overview", "🔧 Usage Guide", "📋 API Reference", "🚀 Quick Start"])
    
    with tab1:
        st.markdown("""
        ## 🛡️ GeoGuard Overview
        
        **GeoGuard** is an automated compliance detection system that uses LLM capabilities to flag features 
        requiring geo-specific legal compliance logic.
        
        ### Key Features:
        - **Automated Classification**: YES/NO/REVIEW decisions for feature compliance
        - **Evidence-Based Reasoning**: Cites specific text spans and regulation snippets
        - **Audit Trail**: Complete traceability of all decisions
        - **Batch Processing**: Handle multiple features simultaneously
        - **Professional UI**: User-friendly interface for all operations
        
        ### Target Regulations:
        - EU Digital Services Act (DSA)
        - California SB-976 (Kids Social Media Protection)
        - Florida Online Protections for Minors
        - Utah Social Media Regulation Act
        - US NCMEC Reporting Requirements
        """)
    
    with tab2:
        st.markdown("""
        ## 🔧 Usage Guide
        
        ### Single Feature Classification:
        1. Navigate to "🔍 Single Classification"
        2. Enter feature details (ID, name, description)
        3. Click "🚀 Classify Feature"
        4. Review the decision, reasoning, and evidence
        
        ### Batch Processing:
        1. Go to "📊 Batch Processing"
        2. Verify your dataset is loaded
        3. Click "▶️ Run Batch Classification"
        4. Download results as CSV
        
        ### Audit Trail:
        1. Visit "📋 Audit Trail"
        2. View classification history and metrics
        3. Analyze decision patterns over time
        
        ### Examples:
        - **Legal**: "Implement age gates for Utah Social Media Regulation Act compliance"
        - **Business**: "A/B test new UI theme in select markets"
        - **Ambiguous**: "Feature unavailable in Korea (no reason specified)"
        """)
    
    with tab3:
        st.markdown("""
        ## 📋 API Reference
        
        ### Input Schema:
        ```json
        {
            "feature_id": "string",
            "feature_name": "string", 
            "feature_description": "string",
            "prd": "string (optional)",
            "trd": "string (optional)"
        }
        ```
        
        ### Output Schema:
        ```json
        {
            "feature_id": "string",
            "decision": "YES|NO|REVIEW",
            "confidence": 0.0-1.0,
            "reasoning_summary": "string",
            "evidence": {
                "feature_spans": ["string"],
                "reg_snippets": ["string"]
            },
            "regulations": ["DSA", "CA-SB976", ...],
            "control_type": ["age_gating", "reporting", ...],
            "metadata": {...}
        }
        ```
        
        ### REST API Endpoints:
        - `GET /healthz` - System health check
        - `POST /classify` - Single feature classification
        - `POST /batch` - Batch processing
        """)
    
    with tab4:
        st.markdown("""
        ## 🚀 Quick Start
        
        ### Setup:
        1. Install dependencies: `pip install -r requirements.txt`
        2. Set Gemini API key: Create `.env` with `GEMINI_API_KEY=your_key`
        3. Run UI: `streamlit run ui/streamlit_app.py`
        4. Run API: `uvicorn app.main:app --reload --port 8000`
        
        ### Testing:
        1. Run tests: `python -m pytest tests/`
        2. Test single classification with the examples provided
        3. Run batch processing on the synthetic dataset
        
        ### Development:
        - All source code in `/app` directory
        - Data files in `/data` directory
        - Scripts in `/scripts` directory
        - Tests in `/tests` directory
        
        ### Support:
        - Check System Status for health information
        - Review Audit Trail for historical decisions
        - Use examples in Single Classification for testing
        """)

if __name__ == "__main__":
    main()
