from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # --- App ---
    app_env: str = Field(default="dev", validation_alias="APP_ENV")

    # --- OpenAI ---
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")

    # --- Database (MySQL) ---
    db_host: str = Field(default="localhost", validation_alias="DB_HOST")
    db_port: int = Field(default=3306, validation_alias="DB_PORT")
    db_user: str = Field(default="root", validation_alias="DB_USER")
    db_password: str = Field(default="", validation_alias="DB_PASSWORD")
    db_name: str = Field(default="", validation_alias="DB_NAME")

    # mysql driver: pymysql (sync) recomendado para empezar
    db_driver: str = Field(default="pymysql", validation_alias="DB_DRIVER")

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def database_url(self) -> str:
        # mysql+pymysql://user:pass@host:port/db
        return (
            f"mysql+{self.db_driver}://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
