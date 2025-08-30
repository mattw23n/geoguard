# GeoGuard AI ⚖️

**GeoGuard AI** is a prototype system that utilizes the power of Large Language Models to automatically flag software features that require geo-specific legal compliance. It transforms regulatory detection from a manual, error-prone process into a traceable, auditable, and proactive workflow.

**Live Demo:** [https://geoguard-t4.streamlit.app/](https://geoguard-t4.streamlit.app/)

**Demo Video:** `[Link to your YouTube Demo Video]`

## Table of Contents
- [Problem Statement](#problem-statement)
- [Our Solution](#our-solution)
- [Key Features & Functionality](#key-features--functionality)
- [Tech Stack & Assets](#tech-stack--assets)
- [Local Setup & Usage](#local-setup--usage)
- [Running Scripts](#running-scripts)
- [Project Structure](#project-structure)

## Problem Statement

> As modern tech companies operate globally, every product feature must dynamically satisfy dozens of geographic regulations – from Brazil's data localization to GDPR. It is crucial to have automated visibility into key questions such as: "Does this feature require dedicated logic to comply with region-specific legal obligations?"
>
> Without it, potential risks include legal exposure from undetected compliance gaps, reactive firefighting when auditors inquire, and massive manual overhead in scaling global feature rollouts. The challenge is to build a prototype system that utilizes LLM capabilities to flag these features, turning regulatory detection from a blind spot into a traceable, auditable output.

## Our Solution

GeoGuard AI is an interactive web application designed for product managers and legal teams. It provides a centralized dashboard to manage software features and their compliance status.

Instead of relying on manual reviews, a user can input their feature's documentation (Title, Description, PRD, TRD), and our system leverages the Google Gemini model to perform an instant analysis. The AI, augmented with a curated and dynamically manageable knowledge base, determines if the feature requires geo-specific logic, provides clear reasoning, and cites the relevant law.

Crucially, every scan is saved as an immutable snapshot to a **cloud-hosted Supabase database**, creating a persistent, auditable history for each feature. This allows teams to track how a feature's compliance needs evolve and provides a clear evidence trail for regulatory inquiries.

## Key Features & Functionality

*   **AI-Powered Compliance Analysis:** Utilizes the Google Gemini model with a sophisticated prompt and a "Simplified RAG" approach to analyze feature artifacts.
*   **Centralized Cloud Database:** All features, scans, legal rules, and terminology are stored in a robust, cloud-hosted **Supabase** PostgreSQL database.
*   **Dynamic Knowledge Base Management:** A built-in settings page allows administrators to add, edit, and delete legal rules and internal terminology directly from the UI, keeping the AI's knowledge base up-to-date without code changes.
*   **Interactive Feature Dashboard:** A user-friendly Streamlit interface allows users to create, search, filter, and bulk-manage features.
*   **Batch Feature Upload:** Efficiently import multiple features at once from a CSV file.
*   **Immutable Scan Snapshots:** When a scan is performed, the system saves a complete snapshot of the feature's text at that moment, ensuring the audit trail is accurate.
*   **Objective Performance Evaluation:** Includes a standalone script (`evaluate.py`) to test the LLM's accuracy against a ground-truth dataset, enabling data-driven improvements.

## Tech Stack & Assets

#### Development Tools
*   **Language:** Python 3.12
*   **Virtual Environment:** `venv`
*   **Containerization:** Docker
*   **Version Control:** Git & GitHub

#### APIs & Services
*   **Google Gemini API:** The core of our analysis engine, using the `gemini-2.0-flash` model.
*   **Supabase:** Cloud-hosted PostgreSQL database and backend for all application data.

#### Key Libraries
*   **`streamlit`**: For building the interactive web application UI.
*   **`supabase`**: The official Python client for interacting with the Supabase database.
*   **`google-generativeai`**: The official Python SDK for the Gemini API.
*   **`pandas`**: Used for CSV processing (batch uploads) and in our evaluation script.
*   **`python-dotenv`**: For managing environment variables securely.
*   **`scikit-learn`**: Used in our evaluation script to generate a comprehensive classification report.

## Local Setup & Usage

You can run this application on your local machine by following these steps.

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd new-geoguard
    ```

### Using Docker (Recommended)

1.  **Set up Environment Variables:**
    -   Create a file named `.env` by copying the template: `cp .env.template .env`
    -   Edit the `.env` file and add your API keys and database credentials.

2.  **Build and start the container:**
    ```bash
    docker-compose up --build -d
    ```

3.  **Access the application** at [http://localhost:8501](http://localhost:8501)

4.  **To stop the application:**
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

3.  **⚠️ Set up your Environment Variables:**
    -   Create a file named `.env` in the root directory.
    -   Add your credentials to this file in the following format:
        ```env
        # .env
        GEMINI_API_KEY="your-gemini-api-key"
        SUPABASE_URL="https://your-project-ref.supabase.co"
        SUPABASE_KEY="your-supabase-service-role-key"
        ```
    -   The app will not run without these variables.

4.  **Run the application:**
    ```bash
    streamlit run app.py
    ```
    Your browser should open with the application running.

## Running Scripts

The project includes scripts for evaluation and data generation.

### Evaluation Script
To objectively measure the performance of the AI model against our test dataset, run the evaluation script from your terminal:
```bash
python evaluate.py
```
This will output a full classification report and a confusion matrix.

### Results Generation Script
To run the AI analysis on a sample dataset (`sample-dataset/sample_data.csv`) and generate a results file, use:
```bash
python generate_results.py
```
The output will be saved to `sample-dataset/sample_data_results.csv`.

## Project Structure
```text
new-geoguard/
├── .env.template       # Template for environment variables
├── Dockerfile
├── docker-compose.yml
├── README.md
├── app.py              # Main Streamlit application
├── evaluate.py         # Standalone script for testing the LLM
├── generate_results.py # Script to generate results from sample data
├── requirements.txt
├── data/
│   └── test_data.csv   # Ground truth for the evaluation script
├── sample-dataset/
│   ├── sample_data.csv # Sample input data for generation
│   └── sample_data_results.csv # Generated output
└── src/
    ├── __init__.py
    ├── ai_core.py      # All LLM-related logic (prompting, Gemini calls)
    └── db_utils.py     # Functions for interacting