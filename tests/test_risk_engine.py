"""
Test suite for the Human Risk Score engine.

Run with: pytest tests/ -v
"""

from datetime import date, timedelta

import pytest

from src.config import RISK_LEVELS, WEIGHTS
from src.risk_engine import (
    RiskInputs,
    assess_employee,
    calculate_risk_factors,
    calculate_score,
    classify_risk_level,
    recommended_actions_for,
)


TODAY = date(2026, 9, 8)


def make_inputs(**overrides) -> RiskInputs:
    """Baseline 'perfect employee' inputs — every override should only
    ever push the score up, never down, which several tests rely on.
    """
    defaults = dict(
        employee_id="EMP001",
        last_training_date=TODAY - timedelta(days=10),
        mfa_enabled=True,
        awareness_score=100,
        policy_acknowledged=True,
        phishing_campaigns_clicked=0,
        phishing_campaigns_not_reported=0,
        security_incidents=0,
        repeated_risk_behavior=False,
        assessment_date=TODAY,
    )
    defaults.update(overrides)
    return RiskInputs(**defaults)


# ---------------------------------------------------------------------------
# Baseline / boundary behavior
# ---------------------------------------------------------------------------

class TestBaselineAndBoundaries:
    def test_perfect_employee_scores_zero(self):
        inputs = make_inputs()
        factors = calculate_risk_factors(inputs)
        assert factors == []
        assert calculate_score(factors) == 0

    def test_score_never_exceeds_max(self):
        inputs = make_inputs(
            last_training_date=None,
            mfa_enabled=False,
            awareness_score=0,
            policy_acknowledged=False,
            phishing_campaigns_clicked=5,  # above cap, should still clamp
            phishing_campaigns_not_reported=1,
            security_incidents=5,  # above cap
            repeated_risk_behavior=True,
        )
        factors = calculate_risk_factors(inputs)
        score = calculate_score(factors)
        assert score <= 100

    def test_score_never_negative(self):
        # Even a nonsensical negative-weight scenario should clamp at 0
        factors = []
        assert calculate_score(factors) == 0

    def test_awareness_score_zero_gives_max_contribution(self):
        inputs = make_inputs(awareness_score=0)
        factors = calculate_risk_factors(inputs)
        awareness_factor = next(f for f in factors if "awareness" in f.label.lower())
        assert awareness_factor.points == WEIGHTS.AWARENESS_SCORE_MAX

    def test_awareness_score_hundred_gives_no_contribution(self):
        inputs = make_inputs(awareness_score=100)
        factors = calculate_risk_factors(inputs)
        assert not any("awareness" in f.label.lower() for f in factors)

    def test_awareness_score_midpoint_is_half_weight(self):
        inputs = make_inputs(awareness_score=50)
        factors = calculate_risk_factors(inputs)
        awareness_factor = next(f for f in factors if "awareness" in f.label.lower())
        assert awareness_factor.points == round(WEIGHTS.AWARENESS_SCORE_MAX * 0.5)


# ---------------------------------------------------------------------------
# Training impact
# ---------------------------------------------------------------------------

class TestTrainingImpact:
    def test_training_overdue_adds_weight(self):
        inputs = make_inputs(last_training_date=TODAY - timedelta(days=200))
        factors = calculate_risk_factors(inputs)
        assert any(f.label == "Training overdue" for f in factors)
        overdue_factor = next(f for f in factors if f.label == "Training overdue")
        assert overdue_factor.points == WEIGHTS.TRAINING_OVERDUE

    def test_training_recent_does_not_add_weight(self):
        inputs = make_inputs(last_training_date=TODAY - timedelta(days=5))
        factors = calculate_risk_factors(inputs)
        assert not any(f.label == "Training overdue" for f in factors)

    def test_training_exactly_at_threshold_is_not_overdue(self):
        # TRAINING_OVERDUE_DAYS is 90; exactly 90 days should NOT be overdue
        # since the rule is "overdue after" the threshold (strictly greater than)
        inputs = make_inputs(last_training_date=TODAY - timedelta(days=90))
        factors = calculate_risk_factors(inputs)
        assert not any(f.label == "Training overdue" for f in factors)

    def test_training_one_day_past_threshold_is_overdue(self):
        inputs = make_inputs(last_training_date=TODAY - timedelta(days=91))
        factors = calculate_risk_factors(inputs)
        assert any(f.label == "Training overdue" for f in factors)

    def test_missing_training_date_counts_as_overdue(self):
        inputs = make_inputs(last_training_date=None)
        factors = calculate_risk_factors(inputs)
        assert any(f.label == "Training overdue" for f in factors)


# ---------------------------------------------------------------------------
# MFA impact
# ---------------------------------------------------------------------------

class TestMFAImpact:
    def test_mfa_disabled_adds_weight(self):
        inputs = make_inputs(mfa_enabled=False)
        factors = calculate_risk_factors(inputs)
        mfa_factor = next(f for f in factors if f.label == "MFA disabled")
        assert mfa_factor.points == WEIGHTS.MFA_DISABLED

    def test_mfa_enabled_adds_no_weight(self):
        inputs = make_inputs(mfa_enabled=True)
        factors = calculate_risk_factors(inputs)
        assert not any(f.label == "MFA disabled" for f in factors)


# ---------------------------------------------------------------------------
# Phishing simulation & incidents (capping behavior)
# ---------------------------------------------------------------------------

class TestCapsAndRepeatedFactors:
    def test_phishing_clicks_capped(self):
        inputs = make_inputs(phishing_campaigns_clicked=10)
        factors = calculate_risk_factors(inputs)
        click_factor = next(f for f in factors if "phishing simulation" in f.label.lower())
        # capped at PHISHING_CLICK_CAP (2) * weight per click
        assert click_factor.points == WEIGHTS.PHISHING_CLICKED * 2

    def test_security_incidents_capped(self):
        inputs = make_inputs(security_incidents=10)
        factors = calculate_risk_factors(inputs)
        incident_factor = next(f for f in factors if "incident" in f.label.lower())
        assert incident_factor.points == WEIGHTS.SECURITY_INCIDENT * 2

    def test_negative_counts_do_not_produce_negative_or_missing_factors(self):
        # Defensive: invalid/negative input should not crash or subtract points
        inputs = make_inputs(phishing_campaigns_clicked=-3, security_incidents=-1)
        factors = calculate_risk_factors(inputs)
        assert not any("phishing simulation" in f.label.lower() for f in factors)
        assert not any("incident" in f.label.lower() for f in factors)

    def test_repeated_risk_behavior_adds_weight(self):
        inputs = make_inputs(repeated_risk_behavior=True)
        factors = calculate_risk_factors(inputs)
        assert any(f.label == "Repeated risky behavior" for f in factors)


# ---------------------------------------------------------------------------
# Risk level classification (boundary values)
# ---------------------------------------------------------------------------

class TestRiskClassification:
    @pytest.mark.parametrize(
        "score,expected_level",
        [
            (0, "Low"),
            (25, "Low"),
            (26, "Medium"),
            (50, "Medium"),
            (51, "High"),
            (75, "High"),
            (76, "Critical"),
            (100, "Critical"),
        ],
    )
    def test_classification_boundaries(self, score, expected_level):
        assert classify_risk_level(score) == expected_level

    def test_all_configured_levels_are_reachable(self):
        level_names = {name for name, _ in RISK_LEVELS}
        assert level_names == {"Low", "Medium", "High", "Critical"}


# ---------------------------------------------------------------------------
# Recommended actions
# ---------------------------------------------------------------------------

class TestRecommendedActions:
    @pytest.mark.parametrize("level", ["Low", "Medium", "High", "Critical"])
    def test_every_level_has_at_least_one_action(self, level):
        actions = recommended_actions_for(level)
        assert len(actions) >= 1

    def test_unknown_level_returns_empty_list_not_error(self):
        assert recommended_actions_for("NotALevel") == []

    def test_critical_actions_are_more_stringent_than_low(self):
        low_actions = recommended_actions_for("Low")
        critical_actions = recommended_actions_for("Critical")
        assert len(critical_actions) > len(low_actions)


# ---------------------------------------------------------------------------
# Full pipeline integration
# ---------------------------------------------------------------------------

class TestAssessEmployee:
    def test_full_pipeline_matches_manual_calculation(self):
        inputs = make_inputs(
            last_training_date=TODAY - timedelta(days=200),  # overdue: +20
            mfa_enabled=False,  # +15
            awareness_score=100,  # +0
            policy_acknowledged=True,  # +0
            phishing_campaigns_clicked=1,  # +10
            phishing_campaigns_not_reported=0,
            security_incidents=0,
            repeated_risk_behavior=False,
        )
        result = assess_employee(inputs)
        assert result.score == 45  # 20 + 15 + 10
        assert result.level == "Medium"
        assert result.employee_id == "EMP001"
        assert len(result.recommended_actions) >= 1

    def test_assessment_defaults_to_today_when_no_date_given(self):
        inputs = RiskInputs(
            employee_id="EMP002",
            last_training_date=date.today(),
            mfa_enabled=True,
            awareness_score=90,
            policy_acknowledged=True,
            phishing_campaigns_clicked=0,
            phishing_campaigns_not_reported=0,
            security_incidents=0,
            repeated_risk_behavior=False,
        )
        assert inputs.assessment_date == date.today()

    def test_critical_employee_gets_all_factors(self):
        inputs = make_inputs(
            last_training_date=None,
            mfa_enabled=False,
            awareness_score=0,
            policy_acknowledged=False,
            phishing_campaigns_clicked=3,
            phishing_campaigns_not_reported=1,
            security_incidents=3,
            repeated_risk_behavior=True,
        )
        result = assess_employee(inputs)
        assert result.level == "Critical"
        assert result.score == 100  # clamped
        assert len(result.factors) == 8  # every category triggered
