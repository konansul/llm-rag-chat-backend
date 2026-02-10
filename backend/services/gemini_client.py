import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = os.getenv("MODEL_NAME")

def generate_reply(history: list[dict]) -> str:

    contents = [ ]
    for msg in history:
        role = "model" if msg["role"] == "assistant" else msg["role"]
        contents.append(
            {
                "role": role,
                "parts": [{"text": msg["content"]}],
            }
        )

    response = client.models.generate_content(
        model = MODEL_NAME,
        contents = contents,
    )

    return response.text