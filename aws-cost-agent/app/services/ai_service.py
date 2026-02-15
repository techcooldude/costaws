"""AI service scaffold."""

from app.config import settings


class AIService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY


ai_service = AIService()
