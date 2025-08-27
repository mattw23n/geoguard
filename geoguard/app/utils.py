# Utility functions for Gemini API integration
import os
import requests

def get_gemini_response(prompt: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    params = {"key": api_key}
    response = requests.post(endpoint, headers=headers, params=params, json=data)
    return response.json()
