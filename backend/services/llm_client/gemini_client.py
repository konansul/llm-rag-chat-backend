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

def generate_chat_title(history: list[dict]) -> str:
    dialogue = "\n".join(
        f"{m['role']}: {m['content']}" for m in history
    )

    prompt = f"""
Generate a chat title.

Conversation:
{dialogue}

Rules:
- Output ONLY the title
- Exactly 2 or 3 words
- No quotes
- No punctuation at the end
- Same language as the conversation
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[{ "role": "user", "parts": [{"text": prompt}],}],
    )

    title = (response.text or "").strip()

    title = title.strip('"').strip("'").strip()
    title = title.split("\n")[0].strip()
    title_words = title.split()
    title = " ".join(title_words[:3])
    if len(title_words) < 2:
        return "New chat"
    return title[:60].rstrip()

def answer_question(question: str, context: str, model: str = MODEL_NAME) -> str:
    prompt = f"""
You are a helpful assistant.
Answer the user's question using ONLY the provided CONTEXT.
If the answer is not explicitly in the context, say exactly:
"I don't know based on the document."

CONTEXT:
{context}

QUESTION:
{question}
""".strip()

    response = client.models.generate_content(
        model=model,
        contents=[{"role": "user", "parts": [{"text": prompt}]}],
    )

    return response.text