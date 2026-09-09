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


@dataclass
class TrendPoint:
    period_date: str
    avg_risk_score: float
    training_completion_rate: float
    policy_ack_rate: float
    avg_awareness_score: float
    phishing_click_rate: float
    phishing_report_rate: float


def get_trend_series(conn: sqlite3.Connection) -> list[TrendPoint]:
    """Builds one TrendPoint per historical assessment period, aggregating
    across all employees. Used to power the Human Risk Trends chart.

    Phishing rates are computed cumulatively as of each period date (only
    campaigns whose campaign_date has occurred by that period are counted),
    which is why the underlying `campaigns` table carries a campaign_date.
    """
    assessments = db.get_all_risk_assessments(conn)
    awareness_records = db.get_all_awareness_records(conn)
    sims_with_dates = db.get_simulation_results_with_campaign_dates(conn)

    period_dates = sorted({a["assessment_date"] for a in assessments})

    points = []
    for period in period_dates:
        period_scores = [a["score"] for a in assessments if a["assessment_date"] == period]
        avg_score = round(sum(period_scores) / len(period_scores), 1) if period_scores else 0.0

        period_awareness = [r for r in awareness_records if r["assessment_date"] == period]
        training_rate = (
            round(sum(1 for r in period_awareness if r["training_completed"]) / len(period_awareness) * 100, 1)
            if period_awareness else 0.0
        )
        policy_rate = (
            round(sum(1 for r in period_awareness if r["policy_acknowledged"]) / len(period_awareness) * 100, 1)
            if period_awareness else 0.0
        )
        avg_awareness = (
            round(sum(r["awareness_score"] for r in period_awareness) / len(period_awareness), 1)
            if period_awareness else 0.0
        )

        # Cumulative phishing exposure as of this period: only campaigns
        # that had already run by `period` count toward the rate.
        relevant_sims = [s for s in sims_with_dates if s["campaign_date"] and s["campaign_date"] <= period]
        opened = [s for s in relevant_sims if s["opened"]]
        clicked = [s for s in opened if s["clicked"]]
        reported = [s for s in opened if s["reported"]]
        click_rate = round(len(clicked) / len(opened) * 100, 1) if opened else 0.0
        report_rate = round(len(reported) / len(opened) * 100, 1) if opened else 0.0

        points.append(
            TrendPoint(
                period_date=period,
                avg_risk_score=avg_score,
                training_completion_rate=training_rate,
                policy_ack_rate=policy_rate,
                avg_awareness_score=avg_awareness,
                phishing_click_rate=click_rate,
                phishing_report_rate=report_rate,
            )
        )
    return points
