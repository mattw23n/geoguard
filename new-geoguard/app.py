import streamlit as st
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
st.set_page_config(page_title="GeoGuard AI", page_icon="⚖️", layout="wide")

# --- Initialize Session State for Page Navigation ---
if "view" not in st.session_state:
    st.session_state.view = "list"  # 'list' or 'detail'
if "selected_feature_id" not in st.session_state:
    st.session_state.selected_feature_id = None


# ==============================================================================
#                             RENDER DETAIL VIEW
# ==============================================================================
def render_detail_view():
    """Renders the page for viewing/editing/scanning a single feature."""
    st.title("⚖️ Feature Details & Analysis")

    if st.button("← Back to All Features"):
        st.session_state.view = "list"
        st.session_state.selected_feature_id = None
        st.rerun()

    db = load_database()
    current_feature = None
    if st.session_state.selected_feature_id:
        for f in db["features"]:
            if f["id"] == st.session_state.selected_feature_id:
                current_feature = f
                break

    # --- Feature Details Form ---
    col1, col2 = st.columns(2)
    with col1:
        st.header("Feature Details")
        title = st.text_input("Title", value=current_feature["title"] if current_feature else "")
        description = st.text_area("Description", value=current_feature["description"] if current_feature else "", height=150)
    with col2:
        st.header("Related Documents")
        prd = st.text_area("PRD Content/Link", value=current_feature["prd"] if current_feature else "", height=70)
        trd = st.text_area("TRD Content/Link", value=current_feature["trd"] if current_feature else "", height=70)

    # --- Actions: Save and Scan ---
    actions_col1, actions_col2 = st.columns(2)
    with actions_col1:
        if st.button("Save Feature", type="primary"):
            feature_details = {
                "id": st.session_state.selected_feature_id,
                "title": title,
                "description": description,
                "prd": prd,
                "trd": trd,
            }
            new_id = add_or_update_feature(db, feature_details)
            save_database(db)
            st.session_state.selected_feature_id = new_id
            st.success(f"Feature '{title}' saved successfully!")
            st.rerun()

    with actions_col2:
        if st.session_state.selected_feature_id:  # Only show scan button for saved features
            if st.button("Scan this Version"):
                with st.spinner("Analyzing... The AI is thinking 🤔"):
                    feature_snapshot = {"title": title, "description": description, "prd": prd, "trd": trd}
                    full_text_for_ai = f"Title: {title}\n\nDescription: {description}\n\nPRD: {prd}\n\nTRD: {trd}"
                    raw_response = get_ai_analysis(full_text_for_ai)
                    analysis = parse_llm_response(raw_response)
                    add_scan(db, st.session_state.selected_feature_id, feature_snapshot, analysis)
                    save_database(db)
                    st.success("Scan complete and saved!")
                    st.rerun()

    st.divider()

    # --- Display Scan History for Selected Feature ---
    st.header("Scan History")
    if st.session_state.selected_feature_id:
        feature_scans = get_scans_for_feature(db, st.session_state.selected_feature_id)
        if not feature_scans:
            st.info("No scans have been performed for this feature yet.")
        else:
            for i, scan in enumerate(feature_scans):
                ts = datetime.fromisoformat(scan["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                classification = scan['analysis'].get('classification', 'N/A')
                with st.expander(f"Scan #{len(feature_scans) - i} ({ts}) - Classification: {classification}"):
                    st.subheader("AI Analysis")
                    st.json(scan["analysis"])
                    st.subheader("Feature Snapshot at Time of Scan")
                    st.json(scan["feature_snapshot"])
    else:
        st.info("Save this new feature to enable scanning.")


# ==============================================================================
#                               RENDER LIST VIEW
# ==============================================================================
def render_list_view():
    """Renders the home screen with a list of all created features."""
    st.title("⚖️ GeoGuard AI Feature Dashboard")
    st.markdown("Select a feature to view its details and scan history, or create a new one.")

    if st.button("＋ Create New Feature", type="primary"):
        st.session_state.selected_feature_id = None
        st.session_state.view = "detail"
        st.rerun()

    st.divider()

    db = load_database()
    features = db.get("features", [])

    if not features:
        st.info("No features found. Click 'Create New Feature' to get started.")
    else:
        st.header("Existing Features")
        for feature in features:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(feature["title"])
                    st.caption(f"ID: {feature['id']}")
                with col2:
                    if st.button("View Details", key=f"view_{feature['id']}"):
                        st.session_state.selected_feature_id = feature["id"]
                        st.session_state.view = "detail"
                        st.rerun()


# ==============================================================================
#                                 MAIN ROUTER
# ==============================================================================
if st.session_state.view == "list":
    render_list_view()
elif st.session_state.view == "detail":
    render_detail_view()