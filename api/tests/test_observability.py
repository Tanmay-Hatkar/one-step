"""Error tracking stays off without a DSN and never collects user content."""

from unittest.mock import patch

from app.observability import PRIVATE_DATA_COLLECTION, init_error_tracking


def test_off_without_dsn() -> None:
    with patch("app.observability.sentry_sdk.init") as init:
        assert init_error_tracking("", "production", "1.0") is False
    init.assert_not_called()


def test_on_with_dsn_and_private_by_default() -> None:
    with patch("app.observability.sentry_sdk.init") as init:
        assert init_error_tracking("https://k@o0.ingest.sentry.io/1", "production", "1.0")
    kwargs = init.call_args.kwargs
    assert kwargs["data_collection"] is PRIVATE_DATA_COLLECTION
    assert kwargs["traces_sample_rate"] == 0.0
    assert PRIVATE_DATA_COLLECTION["http_bodies"] == []
    assert PRIVATE_DATA_COLLECTION["user_info"] is False
    assert PRIVATE_DATA_COLLECTION["gen_ai"] == {"inputs": False, "outputs": False}


def test_init_failure_does_not_crash() -> None:
    with patch("app.observability.sentry_sdk.init", side_effect=ValueError("bad dsn")):
        assert init_error_tracking("not-a-dsn", "production", "1.0") is False


def test_real_init_accepts_private_options() -> None:
    """The option names are valid for the installed SDK (no network: DSN never used)."""
    import sentry_sdk

    assert init_error_tracking("https://k@o0.ingest.sentry.io/1", "test", "1.0")
    sentry_sdk.init()  # reset to a no-op client
