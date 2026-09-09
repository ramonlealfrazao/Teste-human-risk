"""
Configuration constants for the Human Risk Score model.

Centralizing weights here means the scoring logic in `risk_engine.py`
never hardcodes a number — every weight is named, documented, and can
be tuned/audited in one place. This mirrors how a real GRC risk model
should be governed: weights are a policy decision, not a code detail.

IMPORTANT: This is a DEMONSTRATIVE model built for a portfolio project.
The weights below are illustrative and not derived from an actuarial
or empirical study. See docs/risk_methodology.md for the full rationale.
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Risk factor weights (points added to the Human Risk Score, 0-100 scale)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskWeights:
    """Maximum point contribution of each human risk factor."""

    TRAINING_OVERDUE: int = 20          # security training overdue > threshold
    MFA_DISABLED: int = 15              # MFA not enabled for the employee
    AWARENESS_SCORE_MAX: int = 18       # scaled inversely from awareness_score (0-100)
    PHISHING_CLICKED: int = 10          # per campaign, capped (see PHISHING_CLICK_CAP)
    PHISHING_NOT_REPORTED: int = 8      # employee did not report a simulated phishing email
    POLICY_ACK_PENDING: int = 12        # security policy acknowledgment outstanding
    SECURITY_INCIDENT: int = 10         # per registered incident
    REPEATED_RISK_BEHAVIOR: int = 15    # 2+ risk factors triggered in prior assessment windows


WEIGHTS = RiskWeights()

# Caps to avoid a single repeated factor dominating the score unfairly
PHISHING_CLICK_CAP = 2          # max campaigns counted toward PHISHING_CLICKED
SECURITY_INCIDENT_CAP = 2       # max incidents counted toward SECURITY_INCIDENT

# Training is considered overdue after this many days since last_training_date
TRAINING_OVERDUE_DAYS = 90

# Human Risk Score is always clamped to this range
SCORE_MIN = 0
SCORE_MAX = 100

# ---------------------------------------------------------------------------
# Risk levels (thresholds are inclusive lower bounds)
# ---------------------------------------------------------------------------

RISK_LEVELS = (
    ("Critical", 76),
    ("High", 51),
    ("Medium", 26),
    ("Low", 0),
)

# ---------------------------------------------------------------------------
# Recommended actions per risk level (educational examples, not policy)
# ---------------------------------------------------------------------------

RECOMMENDED_ACTIONS = {
    "Low": [
        "Continue regular awareness training",
    ],
    "Medium": [
        "Assign targeted awareness training",
        "Send policy acknowledgment reminder",
    ],
    "High": [
        "Mandatory security awareness training",
        "Review MFA enrollment",
        "Manager follow-up",
    ],
    "Critical": [
        "Immediate security review",
        "Mandatory training enrollment",
        "Enforce MFA",
        "Additional monitoring",
    ],
}
