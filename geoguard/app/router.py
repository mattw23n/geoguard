# Weak supervision router using phrasebooks and regex
import re

POSITIVE_CUES = [
    "age gate", "underage", "minors", "parental consent", "Jellybean", "Snowcap", "ASL",
    "report to NCMEC", "CSAM", "child sexual abuse", "data retention", "retention threshold", "DRT",
    "copyright blocking", "notice and action", "takedown", "local compliance policy", "geo-handler enforcement", "delivery constraint"
]
NEGATIVE_CUES = [
    "A/B test", "variant test", "market experiment", "trial run", "layout test", "theme test",
    "creator fund payout", "leaderboard", "mood-based PF", "rewards", "engagement features"
]

def label_feature(text):
    pos = any(re.search(rf"\b{re.escape(cue)}\b", text, re.IGNORECASE) for cue in POSITIVE_CUES)
    neg = any(re.search(rf"\b{re.escape(cue)}\b", text, re.IGNORECASE) for cue in NEGATIVE_CUES)
    if neg and not pos:
        return "NO", 0.95
    if pos and not neg:
        return "YES", 0.85
    if pos and neg:
        return "REVIEW", 0.5
    return "REVIEW", 0.5

def router_decision(feature):
    text = feature.get("feature_description", "")
    return label_feature(text)
