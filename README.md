# GeoGuard AI ⚖️

**GeoGuard AI** is a prototype system that utilizes the power of Large Language Models to automatically flag software features that require geo-specific legal compliance. It transforms regulatory detection from a manual, error-prone process into a traceable, auditable, and proactive workflow.

**Live Demo:** `[Link to your deployed Streamlit App]`

**Demo Video:** `[Link to your YouTube Demo Video]`

 
*(Hint: Replace this placeholder with a real screenshot or GIF of your application!)*

## Table of Contents
- [Problem Statement](#problem-statement)
- [Our Solution](#our-solution)
- [Key Features & Functionality](#key-features--functionality)
- [Tech Stack & Assets](#tech-stack--assets)
- [Additional Datasets](#additional-datasets)
- [Local Setup & Usage](#local-setup--usage)
- [Running the Evaluation Script](#running-the-evaluation-script)
- [Project Structure](#project-structure)

## Problem Statement

> As modern tech companies operate globally, every product feature must dynamically satisfy dozens of geographic regulations – from Brazil's data localization to GDPR. It is crucial to have automated visibility into key questions such as: "Does this feature require dedicated logic to comply with region-specific legal obligations?"
>
> Without it, potential risks include legal exposure from undetected compliance gaps, reactive firefighting when auditors inquire, and massive manual overhead in scaling global feature rollouts. The challenge is to build a prototype system that utilizes LLM capabilities to flag these features, turning regulatory detection from a blind spot into a traceable, auditable output.

## Our Solution

GeoGuard AI is an interactive web application designed for product managers and legal teams. It provides a centralized dashboard to manage software features and their compliance status.

Instead of relying on manual reviews, a user can input their feature's documentation (Title, Description, PRD, TRD), and our system leverages the Google Gemini model to perform an instant analysis. The AI, augmented with a curated knowledge base of legal regulations, determines if the feature requires geo-specific logic, provides clear reasoning, and cites the relevant law.

Crucially, every scan is saved as an immutable snapshot, creating a persistent, auditable history for each feature. This allows teams to track how a feature's compliance needs evolve and provides a clear evidence trail for regulatory inquiries.

## Key Features & Functionality

*   **AI-Powered Compliance Analysis:** Utilizes the Google Gemini model with a sophisticated prompt and a "Simplified RAG" approach to analyze feature artifacts. It distinguishes between legal requirements and business-driven decisions.
*   **Persistent Audit Trail:** Every feature and its associated scans are saved to a local JSON database. This creates a versioned history, allowing users to see how a feature's compliance needs have changed over time.
*   **Interactive Feature Dashboard:** A user-friendly Streamlit interface allows users to create new features, view a list of all existing features, and drill down into a detailed view for each one.
*   **Immutable Scan Snapshots:** When a scan is performed, the system saves a complete snapshot of the feature's text at that moment. This ensures the audit trail is accurate and reflects the exact information that was analyzed.
*   **Objective Performance Evaluation:** Includes a standalone script (`evaluate.py`) to test the LLM's accuracy, precision, and recall against a ground-truth dataset, enabling data-driven improvements to the AI's core logic.

## Tech Stack & Assets

#### Development Tools
*   **Language:** Python 3.12
*   **Virtual Environment:** `venv`
*   **Code Editor:** Visual Studio Code
*   **Version Control:** Git & GitHub

#### APIs Used
*   **Google Gemini API:** The core of our analysis engine, using the `gemini-1.5-flash` model for its speed and reasoning capabilities.

#### Libraries Used
*   **`streamlit`**: For building the interactive web application UI.
*   **`google-generativeai`**: The official Python SDK for the Gemini API.
*   **`pandas`**: Used in our evaluation script to load and manage the test dataset.
*   **`python-dotenv`**: For managing the API key securely in a local environment.
*   **`scikit-learn`**: Used in our evaluation script to generate a comprehensive classification report (accuracy, precision, recall, F1-score).

#### Assets Used
*   The project uses a modular structure with a local JSON file (`database.json`) acting as a simple, persistent database for features and scans.

## Additional Datasets

To enhance the AI's performance and ensure its reliability, we created two custom datasets:

1.  **Legal Knowledge Base (`data/legal_db.json`):** This file acts as the "brain" for our AI's Simplified RAG pattern. Instead of feeding the LLM raw, lengthy legal texts, we created concise, plain-English summaries of key regulations. This focuses the AI's attention and dramatically improves the accuracy of its analysis.
2.  **Evaluation Dataset (`data/test_data.csv`):** This is our ground-truth dataset used by the `evaluate.py` script. It contains a curated list of diverse feature descriptions, each manually labeled with the correct expected outcome (`YES`, `NO`, or `UNSURE`). This allows us to objectively measure the AI's performance and validate any changes to the prompt.

## Local Setup & Usage

You can run this application on your local machine by following these steps.


1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd geoguard-ai
    ```

### Using Docker (Recommended)

1. Build and start the container:

    ```bash
    docker-compose up -d
    ```

2. Access the application at http://localhost:8501

3. To stop the application:

    ```bash
    docker-compose down
    ```


### Manual Installation

1.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **⚠️ Set up your API Key:**
    This application requires a Google Gemini API key to function.
    -   Create a file named `.env` in the root directory of the project.
    -   Add your API key to this file in the following format:
        ```
        GOOGLE_API_KEY="your-api-key-here"
        ```
    -   The app will not run without this file. The `.env` file is ignored by Git, so your key will remain private.

4.  **Run the application:**
    ```bash
    streamlit run app.py
    ```
    Your browser should open with the application running.

## Running the Evaluation Script

To objectively measure the performance of the AI model against our test dataset, run the evaluation script from your terminal:

```bash
python evaluate.py
```
This will output a full classification report and a confusion matrix, showing the model's accuracy, precision, and recall for each class.

## Project Structure
```text
geoguard-ai/
├── .gitignore
├── README.md
├── app.py              # Main Streamlit application
├── evaluate.py         # Standalone script for testing the LLM
├── requirements.txt
├── data/
│   ├── database.json   # Local DB for features and scans
│   ├── legal_db.json   # AI's knowledge base
│   └── test_data.csv   # Ground truth for testing
└── src/
    ├── __init__.py
    ├── ai_core.py      # All LLM-related logic (Gemini)
    └── db_utils.py     # Functions for reading/writing the local DB
```