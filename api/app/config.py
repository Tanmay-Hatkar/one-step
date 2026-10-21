"""Application configuration, loaded from environment variables and `.env`."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = API_ROOT.parent


class Settings(BaseSettings):
    """All runtime settings. Every tunable constant lives here, not in code."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", API_ROOT / ".env"),
        extra="ignore",
    )

    # LLM
    openai_api_key: str = Field(default="", description="OpenAI API key")
    llm_model: str = Field(default="gpt-5.4-mini", description="Runtime model")
    seed_model: str = Field(default="gpt-5.5", description="Model for one-time seed generation")
    llm_reasoning_effort: str = Field(default="low", description="Reasoning effort for gpt-5.x")
    llm_timeout_seconds: float = Field(default=45.0, description="Per-call timeout")

    # Speech-to-text (voice input)
    transcribe_model: str = Field(default="gpt-4o-mini-transcribe", description="~$0.003/min")
    max_audio_bytes: int = Field(default=5_000_000, description="Largest clip accepted")
    min_audio_bytes: int = Field(default=1_000, description="Smaller clips are empty")
    voice_rate_limit: str = Field(default="10/minute", description="Per-IP limit on voice")

    # Cost safety
    daily_llm_call_cap: int = Field(default=2000, description="Max LLM calls per UTC day")
    rate_limit: str = Field(default="40/minute", description="Per-IP limit on LLM endpoints")

    # Data
    database_url: str = Field(default=f"sqlite:///{API_ROOT / 'one_step.db'}")
    dishes_path: Path = Field(default=API_ROOT / "data" / "dishes.json")

    # Input limits
    max_repertoire_text_chars: int = Field(default=1500)
    max_repertoire_dishes: int = Field(default=10, description="Dishes parsed from one text")
    max_kitchen_dishes: int = Field(
        default=30, description="Dishes per request: parsed ones plus ones marked cooked"
    )
    max_skip_ids: int = Field(default=50, description="'Not tonight' skips per request")
    default_cousin_count: int = Field(default=5)
    max_cousin_count: int = Field(default=8)

    # Kitchen ("what I have") and follow-up questions
    max_pantry_items: int = Field(default=60, description="Pantry items per request")
    max_questions: int = Field(default=3, description="Follow-up questions shown at most")
    question_min_gain: float = Field(
        default=0.05, description="Ask only if the answer moves suggestions at least this much"
    )
    question_top_k: int = Field(
        default=6, description="Suggestions compared when scoring a question"
    )

    # Map
    map_cousins_per_dish: int = Field(default=8, description="Cousins drawn around each dish")
    map_max_cousins: int = Field(default=40, description="Most cousins on one map")

    # Sharing
    share_rate_limit: str = Field(default="10/minute", description="Per-IP limit on new links")
    share_id_bytes: int = Field(default=6, description="Random bytes in a share id (8 chars)")

    # Evals
    eval_results_path: Path = Field(default=API_ROOT / "evals" / "results" / "latest.json")

    # Graph tuning — what counts as "one step"
    one_step_max_new_techniques: int = Field(default=1)
    one_step_max_new_ingredients: int = Field(default=6)
    max_cousins_per_region: int = Field(default=2)
    stretch_max_new_techniques: int = Field(
        default=2, description="A 'stretch' pick may add at most this many new skills"
    )

    # HTTP
    cors_origins: str = Field(default="http://localhost:3000", description="Comma-separated")
    log_level: str = Field(default="INFO")

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
