import os

from google import genai
from google.genai import types
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


client = genai.Client(api_key = os.getenv("GEMINI_API_KEY"))

texts = [
    "What is the meaning of life?",
    "What is the purpose of existence?",
    "How do I bake a cake?",
]

result = client.models.embed_content(
    model="gemini-embedding-001",
    contents=texts,
    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
)

print(result)

df = pd.DataFrame(
    cosine_similarity([e.values for e in result.embeddings]),
    index=texts,
    columns=texts,
)

print(df)