from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Chiave API usata da ChatGoogleGenerativeAI
    GOOGLE_API_KEY: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# istanza condivisa usata nel progetto
settings = Settings()