# Human Risk & Security Awareness Tracker

A demonstrative GRC application that models how human behavior — training
completion, MFA adoption, phishing simulation results, policy
acknowledgment, and security incidents — can be turned into an
explainable **Human Risk Score**, and used to drive targeted, risk-based
security awareness actions.

Built as a portfolio project to demonstrate applied GRC / Human Risk
Management thinking combined with clean software engineering practice.

> ⚠️ **All data in this project is fictional.** This application performs
> no real phishing simulation, credential collection, or employee
> surveillance. See [Ethical & Safety Disclaimer](#ethical--safety-disclaimer)
> below.

---

## Project Overview

Organizations increasingly recognize that technical controls alone don't
prevent security incidents — human behavior does. This project simulates
how a security/GRC team could track **Human Risk** at the individual,
department, and company level, and turn that into prioritized, explainable
action.

## Business Problem

Security teams often have fragmented visibility into human risk: training
completion sits in an LMS, phishing simulation results sit in a separate
platform, MFA status sits in IT, and policy acknowledgments sit in a
compliance tool. Without a unified view, it's hard to answer basic
questions:

- Which employees or departments carry the most human risk right now?
- Is our security awareness training actually reducing risk over time?
- What specific action should we take for a specific employee, and why?

## Solution

A single application that:

1. Models fictional employees and their security behaviors
2. Computes an explainable **Human Risk Score (0–100)** per employee, with a
   transparent, documented breakdown of every contributing factor
3. Classifies risk into **Low / Medium / High / Critical** levels
4. Maps each level to example recommended actions
5. Visualizes risk at the corporate, department, and individual level
6. Tracks security awareness campaigns and their impact on risk over time

## Architecture

Clean separation between UI, business logic, and data:

```
Streamlit UI (app.py)
        │
        ▼
Analytics layer (src/analytics.py)   ─── aggregates for dashboards
        │
        ▼
Risk Engine (src/risk_engine.py)     ─── pure scoring logic, no I/O
        │
        ▼
Database layer (src/database.py)     ─── the only module that touches SQLite
```

The risk engine is intentionally pure (plain functions, no database or UI
dependency), which is what allows the entire scoring model to be unit
tested in isolation — see [Testing](#testing).

## Features

- **Employee Management** — fictional employee records (department, role,
  manager, MFA status, training history)
- **Security Awareness Tracking** — training completion, policy
  acknowledgment, awareness scores
- **Phishing Simulation Tracking** *(simulation data only — no real
  emails)* — open/click/report rates per fictional campaign
- **Human Risk Score** — explainable, per-employee, with full factor
  breakdown
- **Corporate Dashboard** — company-wide KPIs (risk distribution, training
  completion, MFA adoption, policy acknowledgment, phishing click/report
  rates, open risk actions)
- **Department Analysis** — risk score and awareness metrics by department
- **Employee Risk Profile** — individual drill-down with score breakdown,
  recommended actions, and simulation history
- **Security Awareness Campaigns** — fictional campaign tracking with
  completion, awareness score, and risk reduction metrics

## Human Risk Methodology & Risk Scoring

The full scoring model — every factor, its weight, and the rationale
behind it — is documented in
[`docs/risk_methodology.md`](docs/risk_methodology.md).

In short: an additive, capped, 0–100 point system across 8 factors
(training, MFA, awareness score, phishing simulation results, policy
acknowledgment, incidents, and repeated risk behavior), chosen deliberately
over a black-box model for **explainability and auditability** — a
score that affects real people's training assignments needs to be
defensible.

## Dashboard

Three levels of visibility:

| View | Purpose |
|---|---|
| Corporate Dashboard | Company-wide KPIs and risk distribution |
| Department Analysis | Risk and awareness metrics by department |
| Employee Profile | Individual score breakdown and recommended actions |

## Technologies

- **Python 3.12+**
- **Streamlit** — web UI
- **Pandas** — data shaping for dashboard tables
- **SQLite** — persistence
- **Plotly** — charts
- **pytest** — testing

## Installation

```bash
git clone <repo-url>
cd human-risk-tracker
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

1. Seed the fictional dataset (60 employees, 5 campaigns, simulation
   results, incidents, and computed risk assessments):

   ```bash
   python -m data.seed_data
   ```

2. Run the app:

   ```bash
   streamlit run app.py
   ```

3. Open the URL Streamlit prints (typically `http://localhost:8501`).

## Testing

```bash
pytest tests/ -v
```

35 tests covering:
- Baseline and boundary score values
- Training and MFA impact
- Factor caps (phishing clicks, security incidents)
- Risk level classification boundaries
- Invalid/negative input handling
- Full pipeline integration (`assess_employee`)

## Screenshots

<img width="1904" height="927" alt="Captura de tela 2026-09-09 104713" src="https://github.com/user-attachments/assets/16f887f1-f02e-4c9c-b407-499e9978bfa6" />
<img width="1905" height="931" alt="Captura de tela 2026-09-09 104735" src="https://github.com/user-attachments/assets/264e329c-2c88-4a8e-b20b-3c9599917f91" />
<img width="1901" height="935" alt="risk" src="https://github.com/user-attachments/assets/b8c0fca2-c43b-4676-a1c4-3b8942ff27af" />
<img width="1905" height="934" alt="Captura de tela 2026-09-09 104644" src="https://github.com/user-attachments/assets/56c6f8ad-8cd9-4ffb-8367-6d3058106b8f" />


## Future Improvements

- Historical trend charts (risk score, training completion, MFA adoption,
  phishing click/report rate over time) once multiple assessment periods
  exist in the seed data
- Before/after risk reduction view for completed training campaigns
- Configurable weight editor in the UI (currently config-file only)
- CSV export of dashboard views
- Role-based access (e.g. manager sees only their team)

## Ethical & Safety Disclaimer

This project is built strictly for **educational and portfolio purposes**.

- All employees, departments, campaigns, incidents, and simulation results
  are **synthetically generated** fictional data.
- This application does **not** send real phishing emails, does **not**
  create fake login/credential-harvesting pages, and does **not** collect
  real credentials.
- No real personal data, passwords, or sensitive employee information is
  modeled or stored anywhere in the schema.
- The Human Risk Score is a **demonstrative model**, not a validated or
  production-ready risk assessment methodology. See
  [`docs/risk_methodology.md`](docs/risk_methodology.md) for full
  methodology and limitations.





