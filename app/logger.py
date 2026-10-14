
import logging

import logfire

from app.config import settings

_configured = False


def setup_logging(app=None) -> None:
    global _configured

    if not _configured:
        logfire.configure(
            service_name="goaguide",
            token=settings.LOGFIRE_TOKEN
        )

        logfire.instrument_openai()
        logfire.instrument_pydantic()

        logging.basicConfig(
            level=logging.INFO,
            handlers=[logfire.LogfireLoggingHandler()],
            force=True,
        )

        _configured = True

    if app is not None:
        logfire.instrument_fastapi(app)


log = logfire
