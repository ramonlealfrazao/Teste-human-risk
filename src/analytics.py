"""
Analytics layer: turns raw database rows into the aggregated views the
Streamlit dashboard needs (corporate KPIs, department breakdowns, trends).

This module reads from the database but contains no UI code and no
risk-scoring logic — it's purely aggregation/shaping of data that has
already been computed and stored by risk_engine.py + seed_data.py.
"""

import json
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass

from src import database as db


@dataclass
class CorporateKPIs:
    total_employees: int
    low_risk: int
    medium_risk: int
    high_risk: int
    critical_risk: int
    training_completion_rate: float
    mfa_adoption_rate: float
    policy_ack_rate: float
    phishing_click_rate: float
    phishing_report_rate: float
    open_risk_actions: int


def get_corporate_kpis(conn: sqlite3.Connection) -> CorporateKPIs:
    employees = db.get_all_employees(conn)
    total = len(employees)

    assessments = db.get_all_latest_assessments(conn)
    level_counts = Counter(a["level"] for a in assessments)

    mfa_enabled_count = sum(1 for e in employees if e["mfa_enabled"])

    # Latest awareness record per employee determines training/policy completion
    completed_training = 0
    policy_acknowledged = 0
    for emp in employees:
        record = db.get_latest_awareness_record(conn, emp["employee_id"])
        if record:
            completed_training += bool(record["training_completed"])
            policy_acknowledged += bool(record["policy_acknowledged"])

    all_sim_results = conn.execute("SELECT * FROM simulation_results").fetchall()
    opened = [r for r in all_sim_results if r["opened"]]
    clicked = [r for r in opened if r["clicked"]]
    reported = [r for r in opened if r["reported"]]

    click_rate = (len(clicked) / len(opened) * 100) if opened else 0.0
    report_rate = (len(reported) / len(opened) * 100) if opened else 0.0

    open_actions = len(db.get_open_actions(conn))

    return CorporateKPIs(
        total_employees=total,
        low_risk=level_counts.get("Low", 0),
        medium_risk=level_counts.get("Medium", 0),
        high_risk=level_counts.get("High", 0),
        critical_risk=level_counts.get("Critical", 0),
        training_completion_rate=round(completed_training / total * 100, 1) if total else 0.0,
        mfa_adoption_rate=round(mfa_enabled_count / total * 100, 1) if total else 0.0,
        policy_ack_rate=round(policy_acknowledged / total * 100, 1) if total else 0.0,
        phishing_click_rate=round(click_rate, 1),
        phishing_report_rate=round(report_rate, 1),
        open_risk_actions=open_actions,
    )


@dataclass
class DepartmentSummary:
    department: str
    avg_risk_score: float
    training_completion_rate: float
    mfa_adoption_rate: float
    avg_awareness_score: float
    employee_count: int


def get_department_summaries(conn: sqlite3.Connection) -> list[DepartmentSummary]:
    employees = db.get_all_employees(conn)
    by_dept: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for emp in employees:
        by_dept[emp["department"]].append(emp)

    assessments_by_emp = {
        a["employee_id"]: a for a in db.get_all_latest_assessments(conn)
    }

    summaries = []
    for dept, emps in sorted(by_dept.items()):
        scores = [
            assessments_by_emp[e["employee_id"]]["score"]
            for e in emps
            if e["employee_id"] in assessments_by_emp
        ]
        awareness_scores = []
        completed = 0
        for e in emps:
            record = db.get_latest_awareness_record(conn, e["employee_id"])
            if record:
                awareness_scores.append(record["awareness_score"])
                completed += bool(record["training_completed"])

        mfa_count = sum(1 for e in emps if e["mfa_enabled"])

        summaries.append(
            DepartmentSummary(
                department=dept,
                avg_risk_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
                training_completion_rate=round(completed / len(emps) * 100, 1) if emps else 0.0,
                mfa_adoption_rate=round(mfa_count / len(emps) * 100, 1) if emps else 0.0,
                avg_awareness_score=round(sum(awareness_scores) / len(awareness_scores), 1)
                if awareness_scores else 0.0,
                employee_count=len(emps),
            )
        )
    return summaries


@dataclass
class EmployeeProfile:
    employee_id: str
    name: str
    department: str
    role: str
    manager: str
    mfa_enabled: bool
    last_training_date: str | None
    awareness_score: int | None
    policy_acknowledged: bool | None
    risk_score: int | None
    risk_level: str | None
    factors: list[dict]
    recommended_actions: list[str]
    simulation_history: list[dict]


def get_employee_profile(conn: sqlite3.Connection, employee_id: str) -> EmployeeProfile | None:
    emp = db.get_employee(conn, employee_id)
    if emp is None:
        return None

    awareness = db.get_latest_awareness_record(conn, employee_id)
    assessment = db.get_latest_assessment(conn, employee_id)
    sim_results = db.get_simulation_results_for_employee(conn, employee_id)

    factors = json.loads(assessment["factors_json"]) if assessment else []

    # Recommended actions are re-derived from config so the profile always
    # reflects the current level's action list, even if actions table
    # only stores what was open at seed time.
    from src.risk_engine import recommended_actions_for
    actions = recommended_actions_for(assessment["level"]) if assessment else []

    sim_history = [
        {
            "campaign_id": r["campaign_id"],
            "opened": bool(r["opened"]),
            "clicked": bool(r["clicked"]),
            "reported": bool(r["reported"]),
        }
        for r in sim_results
    ]

    return EmployeeProfile(
        employee_id=emp["employee_id"],
        name=emp["name"],
        department=emp["department"],
        role=emp["role"],
        manager=emp["manager"],
        mfa_enabled=bool(emp["mfa_enabled"]),
        last_training_date=emp["last_training_date"],
        awareness_score=awareness["awareness_score"] if awareness else None,
        policy_acknowledged=bool(awareness["policy_acknowledged"]) if awareness else None,
        risk_score=assessment["score"] if assessment else None,
        risk_level=assessment["level"] if assessment else None,
        factors=factors,
        recommended_actions=actions,
        simulation_history=sim_history,
    )


def get_campaign_summaries(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.get_all_campaigns(conn)
