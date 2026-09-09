"""
Presentation layer for recommended actions.

The actual Low/Medium/High/Critical -> action mapping lives in
src/config.py (single source of truth for the risk model), and
risk_engine.recommended_actions_for() is what the scoring pipeline uses.
This module adds the UI-facing framing on top: level descriptions,
urgency labels, and the standard disclaimer text, so app.py doesn't
need to hardcode any of that copy.
"""

from dataclasses import dataclass

from src.config import RECOMMENDED_ACTIONS

LEVEL_DESCRIPTIONS = {
    "Low": "Employee shows strong security awareness and low risk indicators.",
    "Medium": "Employee shows some risk indicators that warrant targeted follow-up.",
    "High": "Employee shows multiple risk indicators requiring active intervention.",
    "Critical": "Employee shows severe or compounding risk indicators requiring immediate action.",
}

LEVEL_URGENCY = {
    "Low": "Routine",
    "Medium": "Monitor",
    "High": "Action required",
    "Critical": "Immediate action",
}

DISCLAIMER = (
    "These recommendations are illustrative examples for a demonstrative "
    "Human Risk model, not universal security policy. Real-world actions "
    "should be defined by an organization's security and HR policies."
)


@dataclass
class RecommendationPanel:
    level: str
    description: str
    urgency: str
    actions: list[str]
    disclaimer: str = DISCLAIMER


def get_recommendation_panel(level: str) -> RecommendationPanel:
    return RecommendationPanel(
        level=level,
        description=LEVEL_DESCRIPTIONS.get(level, "Unknown risk level."),
        urgency=LEVEL_URGENCY.get(level, "Unknown"),
        actions=list(RECOMMENDED_ACTIONS.get(level, [])),
    )
