from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv

load_dotenv()



class Settings(BaseSettings):

    groq_api_key: str = os.getenv('GROQ_API_KEY')

    groq_model: str = "openai/gpt-oss-120b"

    chroma_path: str = r"C:\Users\chitr\Documents\Projects\ai-study-assistant\data\student_content.db"

    sqlite_path: str = "./chat_history.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()