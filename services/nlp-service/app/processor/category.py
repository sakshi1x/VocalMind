# Category classification logic
"""Grievance category classification using zero-shot classification.

Model: MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
Note: DeBERTa does not support MPS, so we force CPU via device_map.
"""

import logging
from pathlib import Path
from transformers import pipeline as hf_pipeline, AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)
BASE_DIR = Path("/Users/rumsan/Documents/apps/grievance-ai-system")

UPLOAD_DIR = BASE_DIR / "uploads"

MODEL_CACHE_DIR = UPLOAD_DIR / "model_cache"
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_classifier = None

MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

GRIEVANCE_LABELS = [
    "payment_not_received",
    "partial_payment",
    "fraud_or_misconduct",
    "technical_issue",
    "eligibility_issue",
    "general_feedback",
]


def _get_classifier():
    global _classifier
    if _classifier is None:
        logger.info(f"Loading zero-shot classifier: {MODEL_NAME}")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=str(MODEL_CACHE_DIR))
        model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_NAME,
            cache_dir=str(MODEL_CACHE_DIR),
        )
        model.to("cpu")
        _classifier = hf_pipeline(
            "zero-shot-classification",
            model=model,
            tokenizer=tokenizer,
            device=-1,
        )
    return _classifier


def classify_grievance(text: str, category: list[str]) -> dict:
    """Classify text into a grievance category using zero-shot classification.

    Returns:
        dict with 'category' (label) and 'confidence' (0-1 score).
    """
    pipe = _get_classifier()
    result = pipe(text[:512], category)
    category = result["labels"][0]
    confidence = round(float(result["scores"][0]), 4)
    logger.info(f"Category: {category} ({confidence:.3f})")
    return {"category": category, "confidence": confidence}


def is_grievance(text: str, threshold: float = 0.3) -> bool:
    """Determine if the text is a grievance (vs general_feedback)."""
    result = classify_grievance(text)
    return result["category"] != "general_feedback" or result["confidence"] < threshold