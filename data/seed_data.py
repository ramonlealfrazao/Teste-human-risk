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
    campaigns = []
    for campaign_id, name, target_dept in CAMPAIGN_DEFINITIONS:
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


def seed() -> None:
    print("Resetting database...")
    db.reset_db()

    print("Generating fictional employees...")
    employees = generate_employees(count=60)
    awareness_records = generate_awareness_records(employees)
    campaigns = generate_campaigns()
    simulation_results = generate_simulation_results(employees, campaigns)
    incidents = generate_incidents(employees)

    with db.session() as conn:
        for emp in employees:
            db.insert_employee(conn, emp)

        for record in awareness_records:
            db.insert_awareness_record(conn, record)

        for campaign in campaigns:
            db.insert_campaign(conn, campaign)

        for result in simulation_results:
            db.insert_simulation_result(conn, result)

        for incident in incidents:
            db.insert_security_incident(conn, incident)

        # Compute and store one risk assessment per employee
        awareness_by_emp = {r.employee_id: r for r in awareness_records}
        sim_by_emp: dict[str, list[SimulationResult]] = {}
        for r in simulation_results:
            sim_by_emp.setdefault(r.employee_id, []).append(r)
        incident_counts = {emp.employee_id: 0 for emp in employees}
        for inc in incidents:
            incident_counts[inc.employee_id] += 1

        print("Calculating Human Risk Scores...")
        for emp in employees:
            inputs = build_risk_inputs_for_employee(
                emp,
                awareness_by_emp[emp.employee_id],
                sim_by_emp.get(emp.employee_id, []),
                incident_counts[emp.employee_id],
            )
            assessment = assess_employee(inputs)
            factors_json = json.dumps([asdict(f) for f in assessment.factors])
            db.insert_risk_assessment(conn, assessment, factors_json)

            for action in assessment.recommended_actions:
                db.insert_risk_action(conn, emp.employee_id, action, TODAY)

    print(f"Seed complete: {len(employees)} employees, {len(campaigns)} campaigns, "
          f"{len(simulation_results)} simulation results, {len(incidents)} incidents.")


if __name__ == "__main__":
    seed()
