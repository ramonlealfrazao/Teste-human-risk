"""
SQLite persistence layer for the Human Risk & Security Awareness Tracker.

This is the ONLY module that talks to the database. Every other module
(risk_engine, analytics, recommendations, the Streamlit UI) goes through
the functions here. That separation is what lets risk_engine.py be
tested with zero database setup.

All data stored is FICTIONAL. No real employee PII, credentials, or
passwords are ever written to this database — see models.py for the
exact fields that are captured.
"""

import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Iterator, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "human_risk_tracker.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    role TEXT NOT NULL,
    manager TEXT,
    mfa_enabled INTEGER NOT NULL DEFAULT 0,
    last_training_date TEXT
);

CREATE TABLE IF NOT EXISTS awareness_training (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    training_completed INTEGER NOT NULL DEFAULT 0,
    policy_acknowledged INTEGER NOT NULL DEFAULT 0,
    awareness_score INTEGER NOT NULL CHECK (awareness_score BETWEEN 0 AND 100),
    assessment_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    target_department TEXT,
    completion_rate REAL,
    awareness_score REAL,
    risk_reduction REAL,
    campaign_date TEXT
);

CREATE TABLE IF NOT EXISTS simulation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    opened INTEGER NOT NULL DEFAULT 0,
    clicked INTEGER NOT NULL DEFAULT 0,
    reported INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    assessment_date TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    level TEXT NOT NULL,
    factors_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    action TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    action_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS security_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    description TEXT NOT NULL,
    incident_date TEXT NOT NULL
);
"""


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: Streamlit can rerun the script on a
    # different thread than the one that created the connection. This app
    # only ever does one thing at a time per session (no concurrent writes
    # from multiple threads), so this is safe here.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session(db_path: Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    """Context manager that commits on success and rolls back on error."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    with session(db_path) as conn:
        conn.executescript(SCHEMA)


def reset_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Drops and recreates all tables. Used by seed_data.py so re-running
    the seed script always starts from a clean, consistent fictional
    dataset."""
    tables = [
        "risk_actions",
        "risk_assessments",
        "simulation_results",
        "security_incidents",
        "awareness_training",
        "campaigns",
        "employees",
    ]
    with session(db_path) as conn:
        for table in tables:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------

def insert_employee(conn: sqlite3.Connection, employee) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO employees
           (employee_id, name, department, role, manager, mfa_enabled, last_training_date)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            employee.employee_id,
            employee.name,
            employee.department,
            employee.role,
            employee.manager,
            int(employee.mfa_enabled),
            employee.last_training_date.isoformat() if employee.last_training_date else None,
        ),
    )


def get_all_employees(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM employees ORDER BY name").fetchall()


def get_employee(conn: sqlite3.Connection, employee_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM employees WHERE employee_id = ?", (employee_id,)
    ).fetchone()


def get_employees_by_department(conn: sqlite3.Connection, department: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM employees WHERE department = ? ORDER BY name", (department,)
    ).fetchall()


# ---------------------------------------------------------------------------
# Awareness training
# ---------------------------------------------------------------------------

def insert_awareness_record(conn: sqlite3.Connection, record) -> None:
    conn.execute(
        """INSERT INTO awareness_training
           (employee_id, training_completed, policy_acknowledged, awareness_score, assessment_date)
           VALUES (?, ?, ?, ?, ?)""",
        (
            record.employee_id,
            int(record.training_completed),
            int(record.policy_acknowledged),
            record.awareness_score,
            record.assessment_date.isoformat(),
        ),
    )


def get_latest_awareness_record(conn: sqlite3.Connection, employee_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        """SELECT * FROM awareness_training
           WHERE employee_id = ?
           ORDER BY assessment_date DESC LIMIT 1""",
        (employee_id,),
    ).fetchone()


# ---------------------------------------------------------------------------
# Campaigns & simulation results
# ---------------------------------------------------------------------------

def insert_campaign(conn: sqlite3.Connection, campaign) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO campaigns
           (campaign_id, name, target_department, completion_rate, awareness_score, risk_reduction, campaign_date)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            campaign.campaign_id,
            campaign.name,
            campaign.target_department,
            campaign.completion_rate,
            campaign.awareness_score,
            campaign.risk_reduction,
            campaign.campaign_date.isoformat() if campaign.campaign_date else None,
        ),
    )


def get_all_campaigns(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM campaigns ORDER BY campaign_id").fetchall()


def insert_simulation_result(conn: sqlite3.Connection, result) -> None:
    conn.execute(
        """INSERT INTO simulation_results
           (campaign_id, employee_id, opened, clicked, reported)
           VALUES (?, ?, ?, ?, ?)""",
        (
            result.campaign_id,
            result.employee_id,
            int(result.opened),
            int(result.clicked),
            int(result.reported),
        ),
    )


def get_simulation_results_for_employee(conn: sqlite3.Connection, employee_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM simulation_results WHERE employee_id = ?", (employee_id,)
    ).fetchall()


def get_simulation_results_for_campaign(conn: sqlite3.Connection, campaign_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM simulation_results WHERE campaign_id = ?", (campaign_id,)
    ).fetchall()


# ---------------------------------------------------------------------------
# Security incidents
# ---------------------------------------------------------------------------

def insert_security_incident(conn: sqlite3.Connection, incident) -> None:
    conn.execute(
        """INSERT INTO security_incidents (employee_id, description, incident_date)
           VALUES (?, ?, ?)""",
        (incident.employee_id, incident.description, incident.incident_date.isoformat()),
    )


def count_security_incidents(conn: sqlite3.Connection, employee_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM security_incidents WHERE employee_id = ?",
        (employee_id,),
    ).fetchone()
    return row["c"] if row else 0


# ---------------------------------------------------------------------------
# Risk assessments & actions
# ---------------------------------------------------------------------------

def insert_risk_assessment(conn: sqlite3.Connection, assessment, factors_json: str) -> None:
    conn.execute(
        """INSERT INTO risk_assessments
           (employee_id, assessment_date, score, level, factors_json)
           VALUES (?, ?, ?, ?, ?)""",
        (
            assessment.employee_id,
            assessment.assessment_date.isoformat(),
            assessment.score,
            assessment.level,
            factors_json,
        ),
    )


def get_latest_assessment(conn: sqlite3.Connection, employee_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        """SELECT * FROM risk_assessments
           WHERE employee_id = ?
           ORDER BY assessment_date DESC LIMIT 1""",
        (employee_id,),
    ).fetchone()


def get_assessment_history(conn: sqlite3.Connection, employee_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT * FROM risk_assessments
           WHERE employee_id = ?
           ORDER BY assessment_date ASC""",
        (employee_id,),
    ).fetchall()


def get_all_latest_assessments(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """One row per employee: their most recent risk assessment."""
    return conn.execute(
        """SELECT ra.* FROM risk_assessments ra
           INNER JOIN (
               SELECT employee_id, MAX(assessment_date) AS max_date
               FROM risk_assessments GROUP BY employee_id
           ) latest
           ON ra.employee_id = latest.employee_id AND ra.assessment_date = latest.max_date"""
    ).fetchall()


def insert_risk_action(conn: sqlite3.Connection, employee_id: str, action: str, action_date: date, status: str = "open") -> None:
    conn.execute(
        """INSERT INTO risk_actions (employee_id, action, status, action_date)
           VALUES (?, ?, ?, ?)""",
        (employee_id, action, status, action_date.isoformat()),
    )


def get_open_actions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM risk_actions WHERE status = 'open' ORDER BY action_date DESC"
    ).fetchall()


# ---------------------------------------------------------------------------
# Historical data for trend charts
# ---------------------------------------------------------------------------

def get_all_risk_assessments(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every stored assessment (not just the latest per employee) —
    used to build the Human Risk Trends chart."""
    return conn.execute(
        "SELECT * FROM risk_assessments ORDER BY assessment_date ASC"
    ).fetchall()


def get_all_awareness_records(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every stored awareness/training snapshot across all periods."""
    return conn.execute(
        "SELECT * FROM awareness_training ORDER BY assessment_date ASC"
    ).fetchall()


def get_simulation_results_with_campaign_dates(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Simulation results joined with their campaign's date, so phishing
    click/report rates can be computed as of any given period."""
    return conn.execute(
        """SELECT s.*, c.campaign_date FROM simulation_results s
           JOIN campaigns c ON s.campaign_id = c.campaign_id"""
    ).fetchall()
