import streamlit as st
import pandas as pd
import json
from datetime import datetime
from src.ai_core import get_ai_analysis, parse_llm_response
from src.db_utils import (
    load_database,
    save_database,
    add_or_update_feature,
    add_scan,
    get_scans_for_feature,
)

# --- Page Configuration ---
st.set_page_config(
    page_title="GeoGuard AI", 
    page_icon="⚖️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 1rem 1rem;
    }
    
    .feature-card {
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin: 1rem 0;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .scan-card {
        background: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #007bff;
    }
    
    .classification-yes {
        background: #f8d7da;
        border-left-color: #dc3545;
    }
    
    .classification-no {
        background: #d4edda;
        border-left-color: #28a745;
    }
    
    .classification-unsure {
        background: #fff3cd;
        border-left-color: #ffc107;
    }
    
    .upload-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px dashed #dee2e6;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Session State for Page Navigation ---
if "view" not in st.session_state:
    st.session_state.view = "list"  # 'list', 'detail', or 'batch_upload'
if "selected_feature_id" not in st.session_state:
    st.session_state.selected_feature_id = None


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
        
        # Clean column names (remove whitespace)
        df.columns = df.columns.str.strip()
        
        # Expected columns
        required_columns = ['title', 'description']
        optional_columns = ['prd', 'trd']
        
        # Check for required columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns: {missing_columns}")
            st.info("Required columns: title, description")
            st.info("Optional columns: prd, trd")
            return None
        
        # Fill missing optional columns
        for col in optional_columns:
            if col not in df.columns:
                df[col] = ""
        
        # Clean data
        df = df.fillna("")
        df = df[df['title'].str.strip() != ""]  # Remove rows with empty titles
        
        return df[['title', 'description', 'prd', 'trd']]
        
    except Exception as e:
        st.error(f"Error processing CSV file: {str(e)}")
        return None


def render_classification_badge(classification):
    """Renders a styled classification badge"""
    if classification == "YES":
        st.error(f"🚨 **High Risk:** {classification}")
    elif classification == "NO":
        st.success(f"✅ **Low Risk:** {classification}")
    elif classification == "UNSURE":
        st.warning(f"⚠️ **Uncertain:** {classification}")
    else:
        st.info(f"❓ **Unknown:** {classification}")


def render_analysis_section(analysis):
    """Renders the AI analysis in a human-readable format"""
    classification = analysis.get('classification', 'N/A')
    
    # Classification with appropriate styling
    st.subheader("📊 Risk Assessment")
    render_classification_badge(classification)
    
    # Reasoning section
    reasoning = analysis.get("reasoning", "No reasoning provided.")
    if reasoning and reasoning.strip():
        st.subheader("🧠 AI Reasoning")
        st.info(reasoning)
    
    # Relevant regulation
    regulation = analysis.get("regulation", "")
    if regulation and regulation.strip():
        st.subheader("📋 Relevant Regulations")
        st.info(regulation)
    
    # Risk factors if available
    risk_factors = analysis.get("risk_factors", [])
    if risk_factors:
        st.subheader("⚠️ Risk Factors")
        for factor in risk_factors:
            st.markdown(f"• {factor}")
    
    # Recommendations if available
    recommendations = analysis.get("recommendations", [])
    if recommendations:
        st.subheader("💡 Recommendations")
        for rec in recommendations:
            st.markdown(f"• {rec}")


def render_feature_snapshot(snapshot):
    """Renders the feature snapshot in a readable format"""
    st.subheader("📸 Feature State at Scan Time")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Title:**")
        st.code(snapshot.get("title", "N/A"))
        
        st.markdown("**Description:**")
        description = snapshot.get("description", "N/A")
        if len(description) > 100:
            st.text_area("", value=description, height=100, disabled=True, key=f"desc_{hash(description)}")
        else:
            st.code(description)
    
    with col2:
        st.markdown("**PRD Content:**")
        prd = snapshot.get("prd", "N/A")
        if len(prd) > 50:
            st.text_area("", value=prd, height=80, disabled=True, key=f"prd_{hash(prd)}")
        else:
            st.code(prd if prd else "None")
        
        st.markdown("**TRD Content:**")
        trd = snapshot.get("trd", "N/A")
        if len(trd) > 50:
            st.text_area("", value=trd, height=80, disabled=True, key=f"trd_{hash(trd)}")
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
    
    # Download template
    csv_template = template_df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV Template",
        data=csv_template,
        file_name="geoguard_features_template.csv",
        mime="text/csv"
    )

    st.divider()

    # File Upload Section
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
                    db = load_database()
                    imported_count = 0
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for index, row in df.iterrows():
                        status_text.text(f"Importing: {row['title']}")
                        
                        feature_details = {
                            "id": None,  # Will generate new ID
                            "title": row['title'],
                            "description": row['description'], 
                            "prd": row['prd'],
                            "trd": row['trd'],
                        }
                        
                        add_or_update_feature(db, feature_details)
                        imported_count += 1
                        progress_bar.progress((index + 1) / len(df))
                    
                    save_database(db)
                    status_text.empty()
                    progress_bar.empty()
                    st.success(f"🎉 Successfully imported {imported_count} features!")
                    
                    if st.button("View Dashboard"):
                        st.session_state.view = "list"
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

    db = load_database()
    current_feature = None
    if st.session_state.selected_feature_id:
        for f in db["features"]:
            if f["id"] == st.session_state.selected_feature_id:
                current_feature = f
                break

    # --- Feature Details Form ---
    st.markdown("### 📝 Feature Information")
    
    # Title (full width)
    title = st.text_input(
        "Feature Title", 
        value=current_feature["title"] if current_feature else "",
        placeholder="Enter a descriptive title for your feature"
    )
    
    # Description (full width)
    description = st.text_area(
        "Feature Description", 
        value=current_feature["description"] if current_feature else "", 
        height=120,
        placeholder="Describe what this feature does, its purpose, and key functionality"
    )
    
    # Related Documents with File Upload Support
    st.markdown("### 📋 Related Documents")
    
    doc_col1, doc_col2 = st.columns(2)
    
    # PRD Section
    with doc_col1:
        st.markdown("#### Product Requirements Document (PRD)")
        
        prd_input_method = st.radio(
            "PRD Input Method",
            ["Text Input", "File Upload"],
            key="prd_method",
            horizontal=True
        )
        
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
            prd_file = st.file_uploader(
                "Upload PRD File",
                type=['txt', 'json', 'md'],
                key="prd_file",
                help="Supported formats: TXT, JSON, Markdown"
            )
            
            if prd_file is not None:
                extracted_content = extract_text_from_file(prd_file)
                if extracted_content:
                    prd_content = extracted_content
                    st.success(f"✅ Loaded content from {prd_file.name}")
                    with st.expander("📄 Preview PRD Content"):
                        st.text_area("", value=prd_content[:500] + "..." if len(prd_content) > 500 else prd_content, height=100, disabled=True)
            else:
                prd_content = current_feature["prd"] if current_feature else ""
    
    # TRD Section  
    with doc_col2:
        st.markdown("#### Technical Requirements Document (TRD)")
        
        trd_input_method = st.radio(
            "TRD Input Method",
            ["Text Input", "File Upload"],
            key="trd_method",
            horizontal=True
        )
        
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
            trd_file = st.file_uploader(
                "Upload TRD File",
                type=['txt', 'json', 'md'],
                key="trd_file",
                help="Supported formats: TXT, JSON, Markdown"
            )
            
            if trd_file is not None:
                extracted_content = extract_text_from_file(trd_file)
                if extracted_content:
                    trd_content = extracted_content
                    st.success(f"✅ Loaded content from {trd_file.name}")
                    with st.expander("📄 Preview TRD Content"):
                        st.text_area("", value=trd_content[:500] + "..." if len(trd_content) > 500 else trd_content, height=100, disabled=True)
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
                new_id = add_or_update_feature(db, feature_details)
                save_database(db)
                st.session_state.selected_feature_id = new_id
                st.success(f"✅ Feature '{title}' saved successfully!")
                st.rerun()

    with action_col2:
        scan_disabled = not st.session_state.selected_feature_id or not title.strip()
        if st.button(
            "🔍 Run AI Compliance Scan", 
            type="secondary", 
            disabled=scan_disabled,
            use_container_width=True
        ):
            with st.spinner("🤔 AI is analyzing your feature for compliance issues..."):
                feature_snapshot = {
                    "title": title, 
                    "description": description, 
                    "prd": prd_content, 
                    "trd": trd_content
                }
                full_text_for_ai = f"Title: {title}\n\nDescription: {description}\n\nPRD: {prd_content}\n\nTRD: {trd_content}"
                raw_response = get_ai_analysis(full_text_for_ai)
                analysis = parse_llm_response(raw_response)
                add_scan(db, st.session_state.selected_feature_id, feature_snapshot, analysis)
                save_database(db)
                st.success("✅ Compliance scan completed and saved!")
                st.rerun()

    if scan_disabled and not st.session_state.selected_feature_id:
        st.caption("💡 Save the feature first to enable scanning")

    st.divider()

    # --- Display Scan History for Selected Feature ---
    st.markdown("### 📈 Compliance Scan History")
    
    if st.session_state.selected_feature_id:
        feature_scans = get_scans_for_feature(db, st.session_state.selected_feature_id)
        
        if not feature_scans:
            st.info("🔍 No compliance scans have been performed for this feature yet. Run your first scan above!")
        else:
            # Summary metrics
            total_scans = len(feature_scans)
            high_risk_scans = sum(1 for scan in feature_scans if scan['analysis'].get('classification') == 'YES')
            latest_scan = feature_scans[0] if feature_scans else None
            
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("Total Scans", total_scans)
            with metric_col2:
                st.metric("High Risk Detected", high_risk_scans, delta=f"{high_risk_scans}/{total_scans}")
            with metric_col3:
                if latest_scan:
                    latest_classification = latest_scan['analysis'].get('classification', 'N/A')
                    st.metric("Latest Status", latest_classification)
            
            st.divider()
            
            # Individual scan results
            for i, scan in enumerate(feature_scans):
                scan_number = len(feature_scans) - i
                timestamp = datetime.fromisoformat(scan["timestamp"])
                formatted_time = timestamp.strftime("%B %d, %Y at %I:%M %p")
                classification = scan['analysis'].get('classification', 'N/A')
                
                # Determine status emoji and color
                if classification == "YES":
                    status_emoji = "🚨"
                    status_text = "High Risk"
                elif classification == "NO":
                    status_emoji = "✅"
                    status_text = "Compliant"
                elif classification == "UNSURE":
                    status_emoji = "⚠️"
                    status_text = "Needs Review"
                else:
                    status_emoji = "❓"
                    status_text = "Unknown"
                
                with st.expander(
                    f"{status_emoji} Scan #{scan_number} - {status_text} ({formatted_time})", 
                    expanded=(i == 0)  # Expand the most recent scan by default
                ):
                    # Create tabs for better organization
                    analysis_tab, snapshot_tab = st.tabs(["🔍 Analysis Results", "📸 Feature Snapshot"])
                    
                    with analysis_tab:
                        render_analysis_section(scan["analysis"])
                    
                    with snapshot_tab:
                        render_feature_snapshot(scan["feature_snapshot"])
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
        st.markdown("")  # Spacer

    st.divider()

    db = load_database()
    features = db.get("features", [])

    if not features:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; color: #666;">
            <h3>🌟 Welcome to GeoGuard AI!</h3>
            <p>No features found yet. Create your first feature or upload multiple features using CSV.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Dashboard metrics
        total_features = len(features)
        
        # Calculate scan statistics
        total_scans = 0
        high_risk_features = 0
        for feature in features:
            feature_scans = get_scans_for_feature(db, feature["id"])
            total_scans += len(feature_scans)
            if feature_scans:
                latest_scan = feature_scans[0]
                if latest_scan['analysis'].get('classification') == 'YES':
                    high_risk_features += 1
        
        st.markdown("### 📊 Dashboard Overview")
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric("Total Features", total_features)
        with metric_col2:
            st.metric("Total Scans", total_scans)
        with metric_col3:
            st.metric("High Risk Features", high_risk_features)
        with metric_col4:
            compliance_rate = round((total_features - high_risk_features) / total_features * 100, 1) if total_features > 0 else 0
            st.metric("Compliance Rate", f"{compliance_rate}%")
        
        st.divider()
        
        # Search and filter
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_term = st.text_input("🔍 Search features", placeholder="Search by title or description...")
        with search_col2:
            status_filter = st.selectbox("Filter by Status", ["All", "High Risk", "Compliant", "Not Scanned", "Needs Review"])
        
        # Filter features based on search and status
        filtered_features = features
        if search_term:
            filtered_features = [
                f for f in filtered_features 
                if search_term.lower() in f['title'].lower() or search_term.lower() in f.get('description', '').lower()
            ]
        
        if status_filter != "All":
            filtered_by_status = []
            for feature in filtered_features:
                feature_scans = get_scans_for_feature(db, feature["id"])
                if not feature_scans:
                    if status_filter == "Not Scanned":
                        filtered_by_status.append(feature)
                else:
                    latest_classification = feature_scans[0]['analysis'].get('classification', 'N/A')
                    if (status_filter == "High Risk" and latest_classification == "YES") or \
                       (status_filter == "Compliant" and latest_classification == "NO") or \
                       (status_filter == "Needs Review" and latest_classification == "UNSURE"):
                        filtered_by_status.append(feature)
            filtered_features = filtered_by_status
        
        # Features list with improved styling
        st.markdown(f"### 🗂️ Features ({len(filtered_features)} of {len(features)})")
        
        if not filtered_features:
            st.info("No features match your current filters.")
        else:
            for feature in filtered_features:
                # Get latest scan info for this feature
                feature_scans = get_scans_for_feature(db, feature["id"])
                latest_classification = "Not Scanned"
                last_scan_date = "Never"
                
                if feature_scans:
                    latest_scan = feature_scans[0]
                    latest_classification = latest_scan['analysis'].get('classification', 'N/A')
                    last_scan_date = datetime.fromisoformat(latest_scan["timestamp"]).strftime("%m/%d/%Y")
                
                # Status indicators
                if latest_classification == "YES":
                    status_emoji = "🚨"
                    status_text = "High Risk"
                elif latest_classification == "NO":
                    status_emoji = "✅"
                    status_text = "Compliant"
                elif latest_classification == "UNSURE":
                    status_emoji = "⚠️"
                    status_text = "Needs Review"
                else:
                    status_emoji = "❓"
                    status_text = "Not Scanned"
                
                with st.container(border=True):
                    row_col1, row_col2, row_col3, row_col4 = st.columns([3, 2, 2, 1])
                    
                    with row_col1:
                        st.markdown(f"**{feature['title']}**")
                        description_preview = feature.get('description', '')
                        if len(description_preview) > 100:
                            description_preview = description_preview[:100] + "..."
                        st.caption(description_preview if description_preview else "No description")
                    
                    with row_col2:
                        st.markdown(f"{status_emoji} **{status_text}**")
                        st.caption(f"ID: {feature['id']}")
                    
                    with row_col3:
                        st.markdown("**Last Scan:**")
                        st.caption(last_scan_date)
                        if feature_scans:
                            st.caption(f"({len(feature_scans)} total scans)")
                    
                    with row_col4:
                        if st.button("View →", key=f"view_{feature['id']}", use_container_width=True):
                            st.session_state.selected_feature_id = feature["id"]
                            st.session_state.view = "detail"
                            st.rerun()


# ==============================================================================
#                                 MAIN ROUTER
# ==============================================================================

# Add a sidebar for navigation info
with st.sidebar:
    st.markdown("### ℹ️ About GeoGuard AI")
    st.markdown("""
    This tool helps you:
    - 📝 Document product features
    - 📤 Batch upload via CSV
    - 📁 Upload PRD/TRD files
    - 🔍 Run AI compliance scans  
    - 📊 Track risk assessments
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