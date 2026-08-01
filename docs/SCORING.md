# Scoring notes

The starter uses intentionally transparent lexical and structural checks. Each response produces:

- A 0–100 score for every dimension
- Flags with category, severity, confidence, matched text, and explanation
- Evidence notes that explain why a score changed

Higher is always better. For toxicity, bias, hallucination risk, and safety, the evaluator returns a **safety-style score** rather than the probability of harm. This avoids mixing directions on charts.

## Calibration warning

The confidence values in the baseline flags are engineering defaults, not statistically calibrated probabilities. Before claiming formal assurance:

1. Build a representative labeled evaluation set.
2. Measure precision, recall, subgroup error rates, and confidence calibration.
3. Select thresholds based on the cost of false positives and false negatives.
4. Validate with domain experts and affected stakeholders.
5. Keep humans in the loop for high-impact decisions.
