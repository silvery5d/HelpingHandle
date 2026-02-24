from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "HelpingHandle"
    debug: bool = False

    database_url: str = "sqlite:///./helpinghandle.db"

    api_key_prefix: str = "hh_"

    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5-20251001"
    claude_max_tokens: int = 2048

    max_prefilter_candidates: int = 50
    agent_online_threshold_minutes: int = 5
    status_stale_threshold_minutes: int = 30

    initial_balance: float = 100.0
    platform_fee_rate: float = 0.01
    required_verifiers: int = 5

    allowed_origins: list[str] = ["https://helpinghandle.ai"]

    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
