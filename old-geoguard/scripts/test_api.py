#!/usr/bin/env python3
"""
Quick test to verify Gemini API connection using google.generativeai
"""

import sys
from pathlib import Path

# Add parent directory to path for app imports
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

from app.utils import get_gemini_response

def test_api_connection():
    print("🔗 Testing Gemini API Connection (google.generativeai)")
    print("=" * 50)
    
    simple_prompt = "Respond with exactly this JSON format: {\"message\": \"Hello from Gemini!\", \"status\": \"working\"}"
    
    try:
        print("📡 Sending test request...")
        response = get_gemini_response(simple_prompt)
        
        print("✅ API Response received!")
        
        # Extract the text content
        content = response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        print(f"Response content: {content}")
        
        # Try to parse as JSON
        import json
        try:
            parsed = json.loads(content)
            print(f"✅ JSON parsed successfully: {parsed}")
        except:
            print("⚠️ Response is not valid JSON, but API connection works")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_connection()
    if success:
        print("\n🎉 API connection test passed!")
    else:
        print("\n💥 API connection test failed!")
        sys.exit(1)
