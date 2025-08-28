# Project TODOs

This document outlines the remaining development tasks. Please follow the specified Git workflow for each task to ensure a clean and manageable development process.

**Standard Git Workflow:**
1.  Pull the latest changes from the `dev` branch: `git pull origin dev`
2.  Create a new feature branch from `dev`: `git checkout -b feature/your-branch-name`
3.  Make your changes and commit them.
4.  Push your branch to the remote repository: `git push origin feature/your-branch-name`
5.  Create a Pull Request (PR) from your feature branch to the `dev` branch on GitHub.

---

### `[ ]` Task 1: AI-LLM Updates & Prompt Engineering

**Description:** The AI is not performing as expected. Sometimes, it references random laws unrelated to the current feature. We need to ensure the prompt engineering is correct and returns the expected result most of the time.

*   **Files to Change:** `src/ai_core.py`
*   **Hints & How to Start:**
    1.  **Add Strict Constraints:** The most effective way to prevent the LLM from "hallucinating" is to be extremely explicit in your instructions. Modify the master prompt to include a direct command like:
        > "You **MUST** base your reasoning and regulation citation **ONLY** on the information provided in the 'REFERENCE LEGAL CONTEXT'. Do not invent or reference any laws not present in that context."
    2.  **Lower the Temperature:** For factual, deterministic tasks, a lower temperature is better. When calling the Gemini API, ensure you are setting a low temperature to reduce randomness.
        ```python
        # In src/ai_core.py, inside get_ai_analysis
        generation_config = genai.types.GenerationConfig(
            temperature=0.1 
        )
        response = model.generate_content(
            master_prompt,
            generation_config=generation_config
        )
        ```
    3.  **Refine the "Unknown Law" Instruction:** Strengthen the safety instruction to be even clearer.
        > "If the feature mentions a law not in your context, your classification **MUST** be 'UNSURE'. Your reasoning **MUST** state that the law was found but is not in your knowledge base."
*   **Git Workflow:**
    *   Create a branch named `feature/prompt-engineering-tuning`.
    *   Push all changes to this branch and create a PR to `dev`.

---

### `[ ]` Task 2: Frontend Presentation Updates

**Description:** The frontend doesn't look very presentable. It shows all the necessary data, but it's not doing it as best as it can. This includes the uneven textboxes for PRD and TRD, as well as the scan results being in a raw JSON format, which is unreadable for non-technical users.

*   **Files to Change:** `app.py`
*   **Hints & How to Start:**
    1.  **Fix Uneven Textboxes:** Use `st.columns` to place the PRD and TRD text areas side-by-side so they align perfectly.
        ```python
        # In app.py, inside render_detail_view()
        st.header("Related Documents")
        col1, col2 = st.columns(2)
        with col1:
            prd = st.text_area("PRD Content/Link", ...)
        with col2:
            trd = st.text_area("TRD Content/Link", ...)
        ```
    2.  **Human-Readable Scan Results:** Instead of using `st.json()`, parse the analysis dictionary and display each key-value pair with proper labels and formatting. Use Streamlit's status elements for better visual cues.
        ```python
        # In app.py, inside the scan history loop
        analysis = scan['analysis']
        classification = analysis.get('classification', 'N/A')

        if classification == "YES":
            st.error(f"**Classification:** {classification}")
        elif classification == "NO":
            st.success(f"**Classification:** {classification}")
        else: # UNSURE or ERROR
            st.warning(f"**Classification:** {classification}")

        st.markdown("**Reasoning:**")
        st.info(analysis.get("reasoning", "No reasoning provided."))
        
        st.markdown("**Relevant Regulation:**")
        st.info(analysis.get("regulation", "None"))
        ```
    3.  **Readable Feature Snapshot:** Apply the same principle to the `feature_snapshot`. Instead of `st.json()`, display it as a formatted block of text or a series of labeled fields.
*   **Git Workflow:**
    *   Create a branch named `feature/frontend-ux-improvements`.
    *   Push all changes to this branch and create a PR to `dev`.

---

### `[ ]` Task 3: Comprehensive LLM Evaluation

**Description:** The `evaluate.py` script has limited test cases and its metrics only focus on the "YES" case. The evaluation should be expanded to cover all cases and provide a holistic view of the model's performance.

*   **Files to Change:** `evaluate.py`, `data/test_data.csv`, `requirements.txt`
*   **Hints & How to Start:**
    1.  **Expand the Test Dataset:** First, add more diverse test cases to `data/test_data.csv`. Include several examples for "NO" and "UNSURE" classifications to ensure the model is tested on its ability to correctly reject and flag ambiguity. Use the test features from the previous prompt as a starting point.
    2.  **Use a Standard Metrics Library:** Manually calculating metrics for all classes is complex. Use `scikit-learn`, the industry standard. Add `scikit-learn` to your `requirements.txt` file.
    3.  **Implement `classification_report`:** This single function from `scikit-learn` provides precision, recall, and F1-score for *every class* automatically. It's the perfect tool for this job.
        ```python
        # In evaluate.py, update calculate_metrics
        from sklearn.metrics import classification_report, confusion_matrix
        import pandas as pd

        def calculate_metrics(y_true, y_pred):
            """Calculates and prints a full classification report."""
            labels = sorted(list(set(y_true + y_pred)))
            report = classification_report(y_true, y_pred, labels=labels)
            print(report)

            print("\n--- Confusion Matrix ---")
            # A confusion matrix helps visualize where the model is making mistakes
            cm = confusion_matrix(y_true, y_pred, labels=labels)
            cm_df = pd.DataFrame(cm, index=labels, columns=labels)
            print(cm_df)
        ```
*   **Git Workflow:**
    *   Create a branch named `feature/comprehensive-evaluation-metrics`.
    *   Push all changes to this branch and create a PR to `dev`.

---

### `[ ]` Task 4: Legal DB Population

**Description:** The `legal_db.json` file currently contains only 3 laws. It needs to be populated with summaries of several other key regulations to improve the AI's knowledge base.

*   **Files to Change:** `data/legal_db.json`
*   **Hints & How to Start:**
    1.  **Research & Summarize:** For each law, perform a quick search for a high-level summary (e.g., "EU Digital Service Act summary"). Your goal is to extract the core, actionable requirement for a tech company. **Do not copy-paste long legal text.**
    2.  **Focus on Actionable Requirements:**
        *   **EU DSA:** Focus on its rules about illegal content removal, user reporting mechanisms, and transparency for recommendation algorithms.
        *   **US State Laws (CA, FL, UT):** These are similar. Focus on the core themes: age verification, restricting features for minors (like push notifications at night), and providing parental controls.
        *   **NCMEC Reporting:** The key requirement is that online service providers have a legal obligation to report any discovered Child Sexual Abuse Material (CSAM) to the National Center for Missing & Exploited Children.
    3.  **Add to JSON:** Format your summaries and add them to `data/legal_db.json`. Use a clear, consistent key for each new entry.
        ```json
        // Example entry to add in data/legal_db.json
        "EU_DSA": "The EU Digital Service Act (DSA) requires online platforms to have clear processes for users to report illegal content, and for the platform to act on these reports. It also mandates transparency in how recommendation systems and online advertising work.",
        "US_NCMEC_REPORTING": "US federal law requires providers of electronic communication services to report any apparent instances of child sexual abuse material (CSAM) they become aware of to the National Center for Missing & Exploited Children (NCMEC)."
        ```
*   **Git Workflow:**
    *   Create a branch named `feature/populate-legal-db`.
    *   Push all changes to this branch and create a PR to `dev`.