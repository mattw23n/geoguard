import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    model = None

LEGAL_DB_PATH = os.path.join("data", "legal_db.json")


def get_ai_analysis(feature_text):
    """
    Analyzes the feature text using the Gemini model and a legal knowledge base.
    """
    if not model:
        return None

    try:
        with open(LEGAL_DB_PATH, "r") as f:
            legal_context = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        legal_context = {}

    context_str = "\n\n".join(
        [f"Regulation: {k}\nDetails: {v}" for k, v in legal_context.items()]
    )

    master_prompt = f"""
    You are a legal compliance analysis AI for a global tech company.
    Your task is to determine if a feature requires geo-specific legal compliance logic.
    You must distinguish between a legal obligation and a business decision (e.g., market testing).

    ---
    REFERENCE LEGAL CONTEXT:
    {context_str}
    ---
    FEATURE ARTIFACTS TO ANALYZE:
    {feature_text}
    ---

    Based on the provided context and feature artifacts, provide your analysis.
    Your response MUST be a single, valid JSON object with three keys:
    1. "classification": (string) Must be one of "YES", "NO", or "UNSURE".
    2. "reasoning": (string) A step-by-step explanation for your classification.
    3. "regulation": (string) The name of the most relevant regulation from the context (e.g., "GDPR_DATA_LOCALIZATION"), or "None" if not applicable.
    
    **IMPORTANT SAFETY INSTRUCTION:** If the feature artifacts explicitly mention a law, regulation, or legal requirement (e.g., "Brazil's LGPD", "India's IT Act") that is NOT described in the REFERENCE LEGAL CONTEXT above, you MUST classify the feature as "UNSURE". In your reasoning, you must state that a potential legal requirement was found but it is not in your knowledge base.

    Output ONLY the JSON object, with no other text or formatting.
    """

    try:
        response = model.generate_content(master_prompt)
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None


def parse_llm_response(response_text):
    """
    Parses the LLM's JSON response string into a Python dictionary.
    """
    if not response_text:
        return {
            "classification": "ERROR",
            "reasoning": "No response from AI.",
            "regulation": "None",
        }
    try:
        # Clean up potential markdown formatting from the model
        if "```json" in response_text:
            response_text = response_text.split("```json\n")[1].split("```")[0]
        return json.loads(response_text)
    except (json.JSONDecodeError, IndexError):
        return {
            "classification": "ERROR",
            "reasoning": "Failed to parse the AI's response. The format was invalid.",
            "regulation": "None",
        }