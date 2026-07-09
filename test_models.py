from google import genai
from core.config import Config

client = genai.Client(api_key=Config.GEMINI_API_KEY)

for model in client.models.list():
    print(model.name)
