from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    app_env: str = Field(default="dev", validation_alias="APP_ENV")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
