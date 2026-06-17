def compute_urgency(sentiment, emotion, category):
    if emotion == "anger" and sentiment == "negative":
        return "high"
    if category == "complaint":
        return "medium"
    return "low"
