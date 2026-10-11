import logging
import logfire

from app.config import settings

_configured = False

def setup_logging(app=None) -> None:
    global _configured

    if not _configured:
        logfire.configure(
            service_name="GoaGuide_AI",
            token=settings.LOGFIRE_TOKEN,
            send_to_logfire="if-token-present"
        )

        logfire.instrument_openai()
        logfire.instrument_pydantic()

        logging.basicConfig(
            handlers=[logfire.LogfireLoggingHandler()],
            level=logging.INFO
        )
        _configured = True

    if app is not None:
        logfire.instrument_fastapi(app)

log = logfire

