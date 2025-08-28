# GeoGuard AI

GeoGuard AI is a compliance analysis tool that helps determine if features require geo-specific legal compliance logic. The tool uses Google's Generative AI to analyze feature descriptions against a legal knowledge base.

## Features

- **Feature Management**: Create, update, and organize feature descriptions
- **AI-Powered Analysis**: Analyze features against legal regulations using Google's Gemini AI
- **Scan History**: Track all previous scans with timestamps and feature snapshots
- **Evaluation Framework**: Test AI performance against ground truth data
- **User-Friendly Interface**: Clean Streamlit interface for easy navigation

## Requirements

- Python 3.12+
- Google Gemini API key
- Docker (optional, for containerized deployment)

## Environment Setup

1. Copy the template file and create your own environment variables:

```bash
cp .env.template .env
```

2. Edit the `.env` file and add your Google API key:

```
GOOGLE_API_KEY=your_gemini_api_key_here
```

## Running the Application

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

1. Create and activate a virtual environment:

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
streamlit run app.py
```

4. Access the application at http://localhost:8501

## Evaluation

To evaluate the AI model against the test dataset:

```bash
python evaluate.py
```

## Project Structure

- `app.py`: Main Streamlit web application
- `evaluate.py`: Script to evaluate AI performance
- `src/ai_core.py`: AI analysis functionality using Google Gemini
- `src/db_utils.py`: Database utilities for storing features and scans
- `data/`: Directory containing database files and test data
  - `legal_db.json`: Knowledge base of legal regulations
  - `database.json`: Application database (auto-generated)
  - `test_data.csv`: Test dataset for evaluation

## Data Storage

The application uses JSON files to store data:
- Features and scan history are stored in `data/database.json`
- Legal knowledge base is stored in `data/legal_db.json`