# Utility functions for Gemini API integration
import os
from google import genai
from pathlib import Path
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

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

def get_structured_response(prompt: str, response_schema: Type[T]) -> T:
    """
    Get structured response from Gemini using Pydantic schema
    """
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        print(f"Sending structured request to Gemini...")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": response_schema,
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048
            }
        )
        
        print(f"Received structured response from Gemini")
        return response.parsed
        
    except Exception as e:
        print(f"Gemini structured API error: {e}")
        # Return a default instance with error info
        if hasattr(response_schema, 'model_fields'):
            # Create a default instance with error values
            default_values = {}
            for field_name, field_info in response_schema.model_fields.items():
                if field_name in ['decision', 'detector_decision']:
                    default_values[field_name] = "ERROR"
                elif field_name == 'confidence':
                    default_values[field_name] = 0.0
                elif field_name in ['reason', 'reasoning_summary']:
                    default_values[field_name] = f"API Error: {str(e)}"
                elif 'list' in str(field_info.annotation).lower():
                    default_values[field_name] = []
                elif 'dict' in str(field_info.annotation).lower():
                    default_values[field_name] = {}
                else:
                    default_values[field_name] = ""
            
            return response_schema(**default_values)
        else:
            raise

def get_gemini_response(prompt: str) -> dict:
    """
    Legacy function for backward compatibility
    """
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        print(f"Sending request to Gemini...")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048
            }
        )
        
        print(f"Received response from Gemini")
        
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
        print(f"Gemini API error: {e}")
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
