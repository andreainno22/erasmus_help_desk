from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Chiave API per Google Gemini
    GOOGLE_API_KEY: str | None = None

    # --- Percorsi Applicazione ---
    DB_PATH: str = str(Path(__file__).parent.parent.parent / "vector_db")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Istanza condivisa usata nel progetto
settings = Settings()