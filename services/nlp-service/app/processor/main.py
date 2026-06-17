import asyncio

from app.processor.category import classify_grievance
from app.processor.sentiment import analyze_emotion, analyze_sentiment, derive_urgency


async def analyze(text: str, category: list[str]) -> dict:
    print("  ├─ classifying category...")
    category_result = await asyncio.to_thread(classify_grievance, text, category)
    print(f"  ├─ category → {category_result['category']} ({category_result['confidence']:.2f})")

    print("  ├─ analysing sentiment...")
    sentiment_result = await asyncio.to_thread(analyze_sentiment, text)
    print(f"  ├─ sentiment → {sentiment_result['label']} ({sentiment_result['score']:.2f})")

    print("  ├─ detecting emotion...")
    emotion_result = await asyncio.to_thread(analyze_emotion, text)
    print(f"  ├─ emotion  → {emotion_result['label']} ({emotion_result['score']:.2f})")

    urgency = derive_urgency(emotion_result["label"])
    print(f"  └─ urgency  → {urgency}")

    return {
        "category": category_result["category"],
        "category_confidence": category_result["confidence"],
        "sentiment": sentiment_result["label"],
        "sentiment_score": sentiment_result["score"],
        "emotion": emotion_result["label"],
        "emotion_score": emotion_result["score"],
        "urgency": urgency,
    }
