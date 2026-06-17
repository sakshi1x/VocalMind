


"""Language detection service using langdetect."""

import logging
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """Detect the language of the given text.

    Returns an ISO 639-1 code (e.g. 'en', 'ne', 'hi').
    Falls back to 'unknown' on detection failure.
    """
    try:
        lang = detect(text)
        logger.info(f"Detected language: {lang}")
        if lang =="en":
            return "en"
        else:
            return "non-en"
    except LangDetectException as e:        

        logger.error(f"Unexpected error occurred: {e}")
        return "unknown"

