"""
Generates a fictional dataset for the Human Risk & Security Awareness
Tracker and seeds the SQLite database.

ALL data produced here — names, departments, campaigns, incidents — is
synthetic and generated for demonstration purposes only. No real people,
companies, or events are represented.

Usage:
    python -m data.seed_data
"""

import random
from datetime import date, timedelta

from src import database as db
from src.models import (
    AwarenessRecord,
    Campaign,
    Employee,
    SecurityIncident,
    SimulationResult,
)
from src.risk_engine import RiskInputs, assess_employee

import json
from dataclasses import asdict

random.seed(42)  # deterministic dataset across re-runs

TODAY = date(2026, 9, 8)

DEPARTMENTS = ["Finance", "HR", "IT", "Sales", "Legal", "Operations", "Marketing"]

FIRST_NAMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Hugo",
    "Isabela", "João", "Karina", "Lucas", "Mariana", "Nuno", "Olivia",
    "Pedro", "Raquel", "Sofia", "Tiago", "Valentina", "William", "Yara",
    "Zeca", "Beatriz", "Caio", "Duda", "Eduardo", "Fernanda", "Gustavo", "Helena",
]

LAST_NAMES = [
    "Silva", "Souza", "Oliveira", "Costa", "Pereira", "Almeida", "Ferreira",
    "Rodrigues", "Gomes", "Martins", "Araujo", "Barbosa", "Rocha", "Dias",
    "Nunes", "Teixeira", "Moreira", "Cardoso", "Ramos", "Pinto",
]

ROLES_BY_DEPT = {
    "Finance": ["Analyst", "Controller", "Manager"],
    "HR": ["Recruiter", "HR Business Partner", "Manager"],
    "IT": ["Support Analyst", "Systems Engineer", "IT Manager"],
    "Sales": ["Account Executive", "SDR", "Sales Manager"],
    "Legal": ["Legal Counsel", "Compliance Analyst"],
    "Operations": ["Ops Analyst", "Operations Manager"],
    "Marketing": ["Marketing Analyst", "Content Specialist", "Marketing Manager"],
}

CAMPAIGN_DEFINITIONS = [
    ("CAMP-001", "Password Security", None),
    ("CAMP-002", "Phishing Awareness Q1", None),
    ("CAMP-003", "MFA Awareness", None),
    ("CAMP-004", "Remote Work Security", None),
    ("CAMP-005", "Data Protection", None),
]

INCIDENT_DESCRIPTIONS = [
    "Reported suspicious USB device found in the office",
    "Sent internal document to wrong recipient",
    "Used weak password flagged by password audit tool",
    "Left workstation unlocked in shared area",
]


def random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_employees(count: int = 60) -> list[Employee]:
    employees = []
    managers_by_dept = {dept: random_name() for dept in DEPARTMENTS}

    for i in range(1, count + 1):
        dept = random.choice(DEPARTMENTS)
        role = random.choice(ROLES_BY_DEPT[dept])
        # Skew training recency: most employees trained recently, some overdue
        days_since_training = random.choices(
            [random.randint(0, 60), random.randint(61, 90), random.randint(91, 400)],
            weights=[0.6, 0.2, 0.2],
        )[0]
        last_training = TODAY - timedelta(days=days_since_training)
        mfa_enabled = random.random() > 0.22  # ~78% MFA adoption

        employees.append(
            Employee(
                employee_id=f"EMP{i:03d}",
                name=random_name(),
                department=dept,
                role=role,
                manager=managers_by_dept[dept],
                mfa_enabled=mfa_enabled,
                last_training_date=last_training,
            )
        )
    return employees


def generate_awareness_records(employees: list[Employee]) -> list[AwarenessRecord]:
    records = []
    for emp in employees:
        # Awareness score loosely correlated with training recency
        overdue = (TODAY - emp.last_training_date).days > 90
        base_score = random.randint(35, 65) if overdue else random.randint(60, 98)
        policy_ack = random.random() > (0.35 if overdue else 0.08)

        records.append(
            AwarenessRecord(
                employee_id=emp.employee_id,
                training_completed=not overdue,
                policy_acknowledged=policy_ack,
                awareness_score=base_score,
                assessment_date=TODAY,
            )
        )
    return records


def generate_campaigns() -> list[Campaign]:
    """Spreads the 5 campaigns across the last ~150 days so phishing
    click/report rates can be tracked over time (see get_trend_series)."""
    campaigns = []
    # Oldest campaign ~150 days ago, most recent ~10 days ago
    campaign_day_offsets = [150, 115, 80, 45, 10]
    for (campaign_id, name, target_dept), offset in zip(CAMPAIGN_DEFINITIONS, campaign_day_offsets):
        completion_rate = round(random.uniform(65, 98), 1)
        awareness_score = round(random.uniform(55, 90), 1)
        risk_reduction = round(random.uniform(10, 40), 1)
        campaigns.append(
            Campaign(
                campaign_id=campaign_id,
                name=name,
                target_department=target_dept,
                completion_rate=completion_rate,
                awareness_score=awareness_score,
                risk_reduction=risk_reduction,
                campaign_date=TODAY - timedelta(days=offset),
            )
        )
    return campaigns


def generate_simulation_results(
    employees: list[Employee], campaigns: list[Campaign]
) -> list[SimulationResult]:
    results = []
    for campaign in campaigns:
        for emp in employees:
            opened = random.random() > 0.15
            clicked = opened and random.random() < 0.14  # ~14% click rate among openers
            reported = opened and not clicked and random.random() < 0.55
            results.append(
                SimulationResult(
                    campaign_id=campaign.campaign_id,
                    employee_id=emp.employee_id,
                    opened=opened,
                    clicked=clicked,
                    reported=reported,
                )
            )
    return results


def generate_incidents(employees: list[Employee]) -> list[SecurityIncident]:
    incidents = []
    # Roughly 12% of employees have at least one fictional incident
    at_risk_employees = random.sample(employees, k=max(1, len(employees) // 8))
    for emp in at_risk_employees:
        num_incidents = random.choices([1, 2, 3], weights=[0.7, 0.25, 0.05])[0]
        for _ in range(num_incidents):
            incidents.append(
                SecurityIncident(
                    employee_id=emp.employee_id,
                    description=random.choice(INCIDENT_DESCRIPTIONS),
                    incident_date=TODAY - timedelta(days=random.randint(1, 180)),
                )
            )
    return incidents


def build_risk_inputs_for_employee(
    emp: Employee,
    awareness_record: AwarenessRecord,
    sim_results: list[SimulationResult],
    incident_count: int,
) -> RiskInputs:
    clicked_count = sum(1 for r in sim_results if r.clicked)
    not_reported_count = sum(1 for r in sim_results if r.opened and not r.clicked and not r.reported)
    repeated_risk = clicked_count >= 2 or (not awareness_record.policy_acknowledged and incident_count > 0)

    return RiskInputs(
        employee_id=emp.employee_id,
        last_training_date=emp.last_training_date,
        mfa_enabled=emp.mfa_enabled,
        awareness_score=awareness_record.awareness_score,
        policy_acknowledged=awareness_record.policy_acknowledged,
        phishing_campaigns_clicked=clicked_count,
        phishing_campaigns_not_reported=not_reported_count,
        security_incidents=incident_count,
        repeated_risk_behavior=repeated_risk,
        assessment_date=TODAY,
    )


# Historical periods (days before TODAY) used to build the Human Risk
# Trends chart. Oldest first. The last entry (0) always represents the
# "current" state already generated above — earlier periods are
# synthesized with a general improvement trend leading up to it, which
# is a reasonable illustrative assumption for a demo dataset (not real
# historical data).
PERIOD_OFFSETS = [150, 120, 90, 60, 30, 0]
MAX_OFFSET = max(PERIOD_OFFSETS)


def _mfa_enable_offset(final_mfa_enabled: bool) -> int | None:
    """Picks a fictional 'day this employee turned MFA on', so the
    company-wide MFA adoption trend is derived from real per-employee
    state rather than a hardcoded curve."""
    if not final_mfa_enabled:
        return None
    return random.randint(20, 140)


def generate_historical_records(
    employees: list[Employee],
    awareness_by_emp: dict,
    sim_by_emp: dict,
    incidents_by_emp: dict,
) -> tuple[list[AwarenessRecord], dict]:
    """For each employee, builds one AwarenessRecord and one RiskInputs
    per historical period, with earlier periods generally worse than the
    final (offset=0) state — simulating gradual improvement from ongoing
    awareness training and campaigns.

    Returns (historical_awareness_records, risk_inputs_by_period) where
    risk_inputs_by_period maps period_offset -> list[RiskInputs].
    """
    historical_awareness: list[AwarenessRecord] = []
    risk_inputs_by_period: dict[int, list[RiskInputs]] = {offset: [] for offset in PERIOD_OFFSETS}

    for emp in employees:
        final_awareness = awareness_by_emp[emp.employee_id]
        mfa_enable_offset = _mfa_enable_offset(emp.mfa_enabled)

        for offset in PERIOD_OFFSETS:
            period_date = TODAY - timedelta(days=offset)

            if offset == 0:
                awareness_score = final_awareness.awareness_score
                training_completed = final_awareness.training_completed
                policy_ack = final_awareness.policy_acknowledged
            else:
                trend_fraction = offset / MAX_OFFSET  # 1.0 oldest -> 0.2 for the 30-day mark
                degrade = int(trend_fraction * random.randint(15, 35))
                awareness_score = max(15, final_awareness.awareness_score - degrade)
                training_completed = random.random() > (0.15 + trend_fraction * 0.35)
                policy_ack = random.random() > (0.05 + trend_fraction * 0.30)

            historical_awareness.append(
                AwarenessRecord(
                    employee_id=emp.employee_id,
                    training_completed=training_completed,
                    policy_acknowledged=policy_ack,
                    awareness_score=awareness_score,
                    assessment_date=period_date,
                )
            )

            # Surrogate last_training_date consistent with training_completed
            if training_completed:
                last_training_period = period_date - timedelta(days=random.randint(1, 60))
            else:
                last_training_period = period_date - timedelta(days=random.randint(120, 300))

            # MFA at this point in time, derived from the fictional enable date
            if mfa_enable_offset is not None:
                enable_date = TODAY - timedelta(days=mfa_enable_offset)
                mfa_at_period = period_date >= enable_date
            else:
                mfa_at_period = False

            # Only count phishing campaigns that had already run by this period
            relevant_sims = [
                r for r in sim_by_emp.get(emp.employee_id, [])
                if r.campaign_id in CAMPAIGN_DATE_BY_ID
                and CAMPAIGN_DATE_BY_ID[r.campaign_id] <= period_date
            ]
            clicked_count = sum(1 for r in relevant_sims if r.clicked)
            not_reported_count = sum(
                1 for r in relevant_sims if r.opened and not r.clicked and not r.reported
            )

            incident_count = sum(
                1 for inc in incidents_by_emp.get(emp.employee_id, [])
                if inc.incident_date <= period_date
            )

            repeated_risk = clicked_count >= 2 or (not policy_ack and incident_count > 0)

            risk_inputs_by_period[offset].append(
                RiskInputs(
                    employee_id=emp.employee_id,
                    last_training_date=last_training_period,
                    mfa_enabled=mfa_at_period,
                    awareness_score=awareness_score,
                    policy_acknowledged=policy_ack,
                    phishing_campaigns_clicked=clicked_count,
                    phishing_campaigns_not_reported=not_reported_count,
                    security_incidents=incident_count,
                    repeated_risk_behavior=repeated_risk,
                    assessment_date=period_date,
                )
            )

    return historical_awareness, risk_inputs_by_period


def seed() -> None:
    print("Resetting database...")
    db.reset_db()

    print("Generating fictional employees...")
    employees = generate_employees(count=60)
    awareness_records = generate_awareness_records(employees)
    campaigns = generate_campaigns()
    simulation_results = generate_simulation_results(employees, campaigns)
    incidents = generate_incidents(employees)

    global CAMPAIGN_DATE_BY_ID
    CAMPAIGN_DATE_BY_ID = {c.campaign_id: c.campaign_date for c in campaigns}

    awareness_by_emp = {r.employee_id: r for r in awareness_records}
    sim_by_emp: dict[str, list[SimulationResult]] = {}
    for r in simulation_results:
        sim_by_emp.setdefault(r.employee_id, []).append(r)
    incidents_by_emp: dict[str, list[SecurityIncident]] = {}
    for inc in incidents:
        incidents_by_emp.setdefault(inc.employee_id, []).append(inc)

    print(f"Building {len(PERIOD_OFFSETS)} historical assessment periods per employee...")
    historical_awareness, risk_inputs_by_period = generate_historical_records(
        employees, awareness_by_emp, sim_by_emp, incidents_by_emp
    )

    with db.session() as conn:
        for emp in employees:
            db.insert_employee(conn, emp)

        for record in historical_awareness:
            db.insert_awareness_record(conn, record)

        for campaign in campaigns:
            db.insert_campaign(conn, campaign)

        for result in simulation_results:
            db.insert_simulation_result(conn, result)

        for incident in incidents:
            db.insert_security_incident(conn, incident)

        print("Calculating Human Risk Scores across all periods...")
        total_assessments = 0
        for offset in PERIOD_OFFSETS:
            for inputs in risk_inputs_by_period[offset]:
                assessment = assess_employee(inputs)
                factors_json = json.dumps([asdict(f) for f in assessment.factors])
                db.insert_risk_assessment(conn, assessment, factors_json)
                total_assessments += 1

                # Only open risk actions for the CURRENT period (offset 0) —
                # historical periods are for trend charts, not live actions.
                if offset == 0:
                    for action in assessment.recommended_actions:
                        db.insert_risk_action(conn, inputs.employee_id, action, TODAY)

    print(
        f"Seed complete: {len(employees)} employees, {len(campaigns)} campaigns, "
        f"{len(simulation_results)} simulation results, {len(incidents)} incidents, "
        f"{total_assessments} risk assessments across {len(PERIOD_OFFSETS)} periods."
    )


CAMPAIGN_DATE_BY_ID: dict = {}


if __name__ == "__main__":
    seed()
