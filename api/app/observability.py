"""Error tracking. Off unless SENTRY_DSN is set; never sends recipes, prompts or IPs."""

import logging

import sentry_sdk

logger = logging.getLogger(__name__)

# What users type (recipes, dish descriptions) and what the model says stays out of reports.
PRIVATE_DATA_COLLECTION: dict = {
    "user_info": False,
    "cookies": {"mode": "off"},
    "http_bodies": [],
    "url_query_params": {"mode": "off"},
    "gen_ai": {"inputs": False, "outputs": False},
    "stack_frame_variables": False,
}


def init_error_tracking(dsn: str, environment: str, release: str) -> bool:
    """Start Sentry error reporting if a DSN is configured.

    Args:
        dsn: The Sentry project DSN; empty turns error tracking off.
        environment: e.g. "production" or "development".
        release: The app version, so errors group by release.

    Returns:
        True if error tracking started.
    """
    if not dsn:
        logger.info("SENTRY_DSN not set; error tracking is off")
        return False
    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            traces_sample_rate=0.0,
            data_collection=PRIVATE_DATA_COLLECTION,
        )
    except Exception:
        logger.exception("Could not start error tracking; continuing without it")
        return False
    logger.info("Error tracking on (%s)", environment)
    return True
