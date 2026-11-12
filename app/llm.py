"""Calls the AI model. We use the free `openai` client library, but point it at Groq
(or Ollama / Gemini) using LLM_BASE_URL from the .env file."""
from openai import OpenAI

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


class LLMError(Exception):
    """Raised when the AI model cannot be reached or is not set up."""


def ask_llm(system_prompt, user_message):
    """Send the prompt to the AI model and return its text reply."""
    if not LLM_API_KEY:
        raise LLMError("API key missing in .env. Please set LLM_API_KEY (see .env.example).")

    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0,  # 0 = no creativity, same answer every time
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception as e:
        raise LLMError(f"Could not get an answer from the AI model: {e}")
    text = response.choices[0].message.content.strip()
    # Replace special characters the model sometimes uses with normal ones
    for odd, normal in {"‑": "-", "‐": "-", "【": "[", "】": "]"}.items():
        text = text.replace(odd, normal)
    return text
