# Confidence calibration, self-consistency vote
# Confidence calibration and self-consistency voting
import numpy as np

def calibrate_confidence(raw_scores):
    # Platt scaling or averaging for self-consistency
    if isinstance(raw_scores, list):
        return float(np.mean(raw_scores))
    return min(max(float(raw_scores), 0.0), 1.0)
