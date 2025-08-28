# Utility functions for Gemini API integration
import os
import google.generativeai as genai
from pathlib import Path

# Load environment variables from .env file
def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# Load .env and configure genai
load_env()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_gemini_response(prompt: str) -> dict:
    """
    Get response from Gemini using the official google.generativeai library
    Returns a dict that matches the original API response format for compatibility
    """
    try:
        # Initialize the model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Configure generation parameters
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            top_p=0.8,
            top_k=40,
            max_output_tokens=2048
        )
        
        print(f"🤖 Sending request to Gemini...")
        
        # Generate response
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        print(f"✅ Received response from Gemini")
        
        # Convert to the expected format for backward compatibility
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": response.text
                            }
                        ]
                    }
                }
            ]
        }
        
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"error": "API request failed", "details": "' + str(e) + '"}'
                            }
                        ]
                    }
                }
            ]
        }
