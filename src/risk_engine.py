"""
Human Risk Score engine.

This module is intentionally pure: every function takes plain data in
and returns plain data out, with no database or UI dependency. That
makes the scoring model fully unit-testable and easy to audit — which
matters for a risk model, since "how was this number produced" should
always be answerable.

DISCLAIMER: This is a demonstrative, illustrative risk-scoring model
built for a portfolio project. The weights and thresholds are not
derived from an empirical or actuarial study. See
docs/risk_methodology.md for the full rationale behind each factor.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from src.config import (
    PHISHING_CLICK_CAP,
    RECOMMENDED_ACTIONS,
    RISK_LEVELS,
    SCORE_MAX,
    SCORE_MIN,
    SECURITY_INCIDENT_CAP,
    TRAINING_OVERDUE_DAYS,
    WEIGHTS,
)
from src.models import RiskAssessment, RiskFactorContribution


@dataclass
class RiskInputs:
    """All fields the risk engine needs for one employee assessment.

    This is deliberately separate from the `Employee`/`AwarenessRecord`
    persistence models: it's the flattened, already-joined view the
    scoring function actually consumes, which keeps the engine decoupled
    from how data happens to be stored.
    """

    employee_id: str
    last_training_date: Optional[date]
    mfa_enabled: bool
    awareness_score: int  # 0-100, higher = more security-aware
    policy_acknowledged: bool
    phishing_campaigns_clicked: int  # count of campaigns where employee clicked
    phishing_campaigns_not_reported: int  # count where employee neither reported nor was safe
    security_incidents: int
    repeated_risk_behavior: bool  # 2+ risk factors triggered in prior assessment windows
    assessment_date: date = None  # defaults to today if not provided

    def __post_init__(self):
        if self.assessment_date is None:
            self.assessment_date = date.today()


def _is_training_overdue(inputs: RiskInputs) -> bool:
    """An employee with no training on record is treated as overdue."""
    if inputs.last_training_date is None:
        return True
    days_since = (inputs.assessment_date - inputs.last_training_date).days
    return days_since > TRAINING_OVERDUE_DAYS


def _awareness_contribution(awareness_score: int) -> int:
    """Scales inversely: a 0 awareness score contributes the full weight,
    a 100 awareness score contributes 0. Linear interpolation in between.
    """
    awareness_score = max(0, min(100, awareness_score))
    fraction_at_risk = (100 - awareness_score) / 100
    return round(fraction_at_risk * WEIGHTS.AWARENESS_SCORE_MAX)


def calculate_risk_factors(inputs: RiskInputs) -> list[RiskFactorContribution]:
    """Builds the explainable breakdown of every factor that contributes
    to an employee's Human Risk Score. Only factors that actually apply
    show up in the list — this is what powers the "+20 Training overdue"
    style explanation in the UI.
    """
    factors: list[RiskFactorContribution] = []

    if _is_training_overdue(inputs):
        factors.append(
            RiskFactorContribution("Training overdue", WEIGHTS.TRAINING_OVERDUE)
        )

    if not inputs.mfa_enabled:
        factors.append(
            RiskFactorContribution("MFA disabled", WEIGHTS.MFA_DISABLED)
        )

    awareness_points = _awareness_contribution(inputs.awareness_score)
    if awareness_points > 0:
        factors.append(
            RiskFactorContribution("Low awareness score", awareness_points)
        )

    clicked_count = max(0, min(inputs.phishing_campaigns_clicked, PHISHING_CLICK_CAP))
    if clicked_count > 0:
        factors.append(
            RiskFactorContribution(
                f"Failed phishing simulation ({clicked_count}x)",
                WEIGHTS.PHISHING_CLICKED * clicked_count,
            )
        )

    if inputs.phishing_campaigns_not_reported > 0:
        factors.append(
            RiskFactorContribution(
                "Did not report simulated phishing", WEIGHTS.PHISHING_NOT_REPORTED
            )
        )

    if not inputs.policy_acknowledged:
        factors.append(
            RiskFactorContribution(
                "Policy acknowledgment pending", WEIGHTS.POLICY_ACK_PENDING
            )
        )

    incident_count = max(0, min(inputs.security_incidents, SECURITY_INCIDENT_CAP))
    if incident_count > 0:
        factors.append(
            RiskFactorContribution(
                f"Security incident(s) ({incident_count}x)",
                WEIGHTS.SECURITY_INCIDENT * incident_count,
            )
        )

    if inputs.repeated_risk_behavior:
        factors.append(
            RiskFactorContribution(
                "Repeated risky behavior", WEIGHTS.REPEATED_RISK_BEHAVIOR
            )
        )

    return factors


def calculate_score(factors: list[RiskFactorContribution]) -> int:
    """Sums factor contributions and clamps to the valid score range."""
    total = sum(f.points for f in factors)
    return max(SCORE_MIN, min(SCORE_MAX, total))


def classify_risk_level(score: int) -> str:
    """Maps a numeric score to a Low/Medium/High/Critical level using the
    inclusive lower-bound thresholds defined in config.RISK_LEVELS.
    """
    for level_name, lower_bound in RISK_LEVELS:
        if score >= lower_bound:
            return level_name
    # Should be unreachable since RISK_LEVELS covers down to 0
    return "Low"


def recommended_actions_for(level: str) -> list[str]:
    """Returns the example educational recommendations for a risk level.
    These are illustrative, not universal security policy.
    """
    return list(RECOMMENDED_ACTIONS.get(level, []))


def assess_employee(inputs: RiskInputs) -> RiskAssessment:
    """Runs the full pipeline for one employee: factors -> score -> level
    -> recommendations -> a complete, explainable RiskAssessment.
    """
    factors = calculate_risk_factors(inputs)
    score = calculate_score(factors)
    level = classify_risk_level(score)
    actions = recommended_actions_for(level)

    return RiskAssessment(
        employee_id=inputs.employee_id,
        assessment_date=inputs.assessment_date,
        score=score,
        level=level,
        factors=factors,
        recommended_actions=actions,
    )
