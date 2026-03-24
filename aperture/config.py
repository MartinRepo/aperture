from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    data_dir: Path = Path("data")
    hn_top_n: int = 30
    relevance_threshold: float = 0.5

    # User interests — included in harness prompts for LLM relevance scoring
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
