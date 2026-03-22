from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    anthropic_api_key: str = ""
    discord_token: str = ""
    discord_channel_id: int = 0

    data_dir: Path = Path("data")
    hn_top_n: int = 30
    relevance_threshold: float = 0.5

    # User interests seed — used by the LLM to score relevance
    user_interests: list[str] = [
        "deep-learning",
        "cuda",
        "gpu",
        "inference",
        "test-infrastructure",
        "pytorch",
        "llm",
        "systems-programming",
    ]


settings = Settings()
