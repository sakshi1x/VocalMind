# Sentiment analysis logic
"""Sentiment & emotion analysis service using HuggingFace models.

- Emotion: j-hartmann/emotion-english-distilroberta-base (anger, joy, sadness, etc.)
- Sentiment: distilbert-base-uncased-finetuned-sst-2-english (positive/negative)
"""

import logging
from pathlib import Path
from transformers import pipeline as hf_pipeline

logger = logging.getLogger(__name__)

BASE_DIR = Path("/Users/rumsan/Documents/apps/grievance-ai-system")

UPLOAD_DIR = BASE_DIR / "uploads"

MODEL_CACHE_DIR = UPLOAD_DIR / "model_cache"
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


_emotion_pipeline = None
_sentiment_pipeline = None

EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"
SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"

EMOTION_MAP = {
    "joy": "happy",
    "sadness": "sad",
    "anger": "anger",
    "fear": "fear",
    "surprise": "surprise",
    "disgust": "disgust",
    "neutral": "neutral",
}

URGENCY_MAP = {
    "anger": "high",
    "fear": "high",
    "disgust": "high",
    "sad": "medium",
    "surprise": "medium",
    "neutral": "low",
    "happy": "low",
}


def _get_emotion_pipeline():
    global _emotion_pipeline
    if _emotion_pipeline is None:
        logger.info(f"Loading emotion model: {EMOTION_MODEL}")
        _emotion_pipeline = hf_pipeline(
            "text-classification",
            model=EMOTION_MODEL,
            top_k=1,
            model_kwargs={"cache_dir": str(MODEL_CACHE_DIR)},
        )
    return _emotion_pipeline


def _get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        logger.info(f"Loading sentiment model: {SENTIMENT_MODEL}")
        _sentiment_pipeline = hf_pipeline(
            "sentiment-analysis",
            model=SENTIMENT_MODEL,
            model_kwargs={"cache_dir": str(MODEL_CACHE_DIR)},
        )
    return _sentiment_pipeline


def analyze_emotion(text: str) -> dict:
    """Classify emotion (happy, sad, anger, fear, surprise, disgust, neutral)."""
    pipe = _get_emotion_pipeline()
    result = pipe(text[:512])[0][0]
    raw_label = result["label"].lower()
    emotion = EMOTION_MAP.get(raw_label, raw_label)
    logger.info(f"Emotion: {emotion} ({result['score']:.3f})")
    return {"label": emotion, "score": round(result["score"], 4)}


def analyze_sentiment(text: str) -> dict:
    """Classify sentiment (positive/negative) with confidence score."""
    pipe = _get_sentiment_pipeline()
    result = pipe(text[:512])[0]
    logger.info(f"Sentiment: {result['label']} ({result['score']:.3f})")
    return {"label": result["label"].lower(), "score": round(result["score"], 4)}


def derive_urgency(emotion: str) -> str:
    """Derive urgency level from emotion label."""
    return URGENCY_MAP.get(emotion, "medium")