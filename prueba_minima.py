"""Primera llamada mínima a Gemini vía SDK OpenAI (JSON mode)."""

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()  # lee .env

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    # Trailing slash obligatorio en la práctica con este SDK
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

resp = client.chat.completions.create(
    model=os.getenv("OPENAI_MODEL", "gemini-3.5-flash-lite"),
    messages=[
        {"role": "system", "content": "Responda solo JSON con clave saludo."},
        {"role": "user", "content": "Di hola en JSON."},
    ],
    temperature=0,
    response_format={"type": "json_object"},  # JSON mode
)

print(resp.choices[0].message.content)
print("tokens:", resp.usage)
