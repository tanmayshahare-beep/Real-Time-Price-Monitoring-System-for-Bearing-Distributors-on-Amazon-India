import requests
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
MODEL = os.getenv('OLLAMA_MODEL', 'hf.co/quelmap/Lightning-4b-GGUF-short-ctx:Q4_K_M')

def ask_ollama(prompt: str) -> str:
    """Send a prompt to Ollama and return the response."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
        if resp.status_code == 200:
            return resp.json()['response']
        else:
            return f"Error: {resp.status_code} - {resp.text}"
    except Exception as e:
        return f"Exception: {str(e)}"
