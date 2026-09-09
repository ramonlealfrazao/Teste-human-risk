"""
Domain models for the Human Risk & Security Awareness Tracker.

These are plain dataclasses — no database or UI dependencies — so the
risk engine can be tested and reasoned about in complete isolation.
All data represented here is FICTIONAL and generated for demonstration
purposes only. No real employee, credential, or personal data is
modeled or stored.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Employee:
    employee_id: str
    name: str
    department: str
    role: str
    manager: str
    mfa_enabled: bool
    last_training_date: Optional[date] = None


@dataclass
class AwarenessRecord:
    employee_id: str
    training_completed: bool
    policy_acknowledged: bool
    awareness_score: int  # 0-100
    assessment_date: date


@dataclass
class SimulationResult:
    """Result of a single fictional employee within a phishing simulation
    campaign. No real email is sent and no credential is ever collected —
    this only stores the outcome of a simulated exercise."""

    campaign_id: str
    employee_id: str
    opened: bool
    clicked: bool
    reported: bool


@dataclass
class SecurityIncident:
    employee_id: str
    description: str
    incident_date: date


@dataclass
class RiskFactorContribution:
    """One line item in the score breakdown, e.g. '+20 Training overdue'."""

    label: str
    points: int


@dataclass
class RiskAssessment:
    employee_id: str
    assessment_date: date
    score: int
    level: str
    factors: list[RiskFactorContribution] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


@dataclass
class Campaign:
    campaign_id: str
    name: str
    target_department: Optional[str]
    completion_rate: float
    awareness_score: float
    risk_reduction: float
    campaign_date: Optional[date] = None
