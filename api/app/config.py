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
    recipes_path: Path = Field(default=API_ROOT / "data" / "recipes.json")
    substitutions_path: Path = Field(default=API_ROOT / "data" / "substitutions.json")
    techniques_path: Path = Field(default=API_ROOT / "data" / "techniques.json")

    # Input limits
    max_repertoire_text_chars: int = Field(default=1500)
    max_repertoire_dishes: int = Field(default=10, description="Dishes parsed from one text")
    max_kitchen_dishes: int = Field(
        default=30, description="Dishes per request: parsed ones plus ones marked cooked"
    )
    max_skip_ids: int = Field(default=50, description="'Not tonight' skips per request")
    default_cousin_count: int = Field(default=5)
    max_cousin_count: int = Field(default=8)

    # Paste a recipe (v1.3): a link or recipe text, rewritten from the user's kitchen
    max_paste_chars: int = Field(default=8000, description="Pasted text, or text kept from a page")
    paste_rate_limit: str = Field(default="10/minute", description="Per-IP limit on pastes")
    link_note_max_chars: int = Field(
        default=200, description="Words allowed around a link before it counts as recipe text"
    )
    max_photo_bytes: int = Field(default=4_000_000, description="Largest recipe photo accepted")
    photo_rate_limit: str = Field(default="6/minute", description="Per-IP limit on photo pastes")
    max_recent_cooked: int = Field(default=40, description="Recently cooked names per request")
    page_timeout_seconds: float = Field(default=8.0, description="Fetching a pasted link")
    max_page_bytes: int = Field(default=1_500_000, description="Most of a page that is read")
    max_page_redirects: int = Field(default=3)
    page_user_agent: str = Field(default="OneStepBot/1.0 (recipe link reader)")
    unreadable_hosts: str = Field(
        default="instagram.com,tiktok.com,facebook.com,fb.watch,youtube.com,youtu.be,x.com",
        description="Comma-separated sites that need a login or are video only",
    )

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

    # Accounts (optional passkey sign-in to sync a kitchen across devices)
    rp_name: str = Field(default="One Step", description="Shown by the passkey prompt")
    auth_rate_limit: str = Field(default="20/minute", description="Per-IP limit on sign-in calls")
    sync_rate_limit: str = Field(default="60/minute", description="Per-IP limit on kitchen sync")
    auth_challenge_seconds: int = Field(default=300, description="A passkey prompt's lifetime")
    session_days: int = Field(default=180, description="How long a sign-in lasts")
    max_synced_kitchen_bytes: int = Field(default=200_000, description="Largest synced kitchen")

    # Feedback and usage stats
    feedback_rate_limit: str = Field(default="5/minute", description="Per-IP feedback limit")
    events_rate_limit: str = Field(default="60/minute", description="Per-IP usage-event limit")
    max_feedback_chars: int = Field(default=2000)
    max_events_per_batch: int = Field(default=20)
    stats_default_days: int = Field(default=28, description="Window for /api/admin/stats")
    admin_token: str = Field(default="", description="Bearer token for stats; empty = off")

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
    def unreadable_host_list(self) -> list[str]:
        """Return the sites whose links can't be read, as a list."""
        return [h.strip().lower() for h in self.unreadable_hosts.split(",") if h.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
