# Human Risk Score — Methodology

> **Status:** This is a demonstrative, illustrative scoring model built for a
> portfolio project. Weights and thresholds are not derived from an
> empirical or actuarial study. They are designed to be transparent,
> explainable, and directionally reasonable — not to be a production-ready
> risk model. Any real deployment would require calibration against
> historical incident data, stakeholder review, and legal/HR input.

## 1. Why an additive, explainable model

The Human Risk Score uses a simple **additive point system** rather than a
machine-learning model. This is a deliberate design choice for a GRC context:

- **Explainability**: every point on the score can be traced to a specific,
  named factor (e.g. "+20 Training overdue"). This matters because risk
  scores that affect people (training assignments, manager follow-up) need
  to be defensible and auditable — a black-box score is a governance risk
  in itself.
- **Auditability**: the breakdown is stored per assessment (`factors_json`
  in the `risk_assessments` table), so historical scores can be explained
  even after the underlying data changes.
- **Tunability**: every weight lives in `src/config.py`, not scattered
  through the codebase. Adjusting the model is a config change, not a
  code change.

## 2. Score range and risk levels

The score is an integer from **0 to 100**, clamped at both ends. It maps to
four risk levels using inclusive lower bounds:

| Level    | Score range |
|----------|-------------|
| Low      | 0–25        |
| Medium   | 26–50       |
| High     | 51–75       |
| Critical | 76–100      |

## 3. Risk factors and weights

| Factor | Max points | Rationale |
|---|---|---|
| **Training overdue** (>90 days since last training, or never trained) | +20 | Security training is the primary control against social engineering; lapses are the single strongest behavioral signal used here. |
| **MFA disabled** | +15 | MFA is one of the highest-leverage technical controls against credential compromise; its absence significantly raises the impact of any other risk factor. |
| **Low awareness score** (scaled) | up to +18 | Scaled *inversely* from a 0–100 awareness assessment score: `points = (100 - awareness_score) / 100 * 18`. A 0 score contributes the full 18 points; a 100 score contributes 0. |
| **Failed phishing simulation (clicked)** | +10 per campaign, capped at 2 campaigns (max +20) | Clicking a simulated phishing email is a direct behavioral indicator. Capped so that an employee who has clicked in many campaigns isn't scored disproportionately relative to other factors. |
| **Did not report simulated phishing** | +8 | Distinct from clicking: an employee who opened but neither clicked nor reported shows passive, rather than active, security engagement. |
| **Policy acknowledgment pending** | +12 | Represents a compliance gap — the employee has not formally acknowledged the security policy they're expected to follow. |
| **Security incident(s)** | +10 per incident, capped at 2 (max +20) | Each fictional incident (e.g. unlocked workstation, misdirected email) reflects a realized — not just potential — risk event. |
| **Repeated risky behavior** | +15 | A composite flag: set when an employee has triggered 2+ of the above categories across the current and prior assessment windows, representing a pattern rather than an isolated lapse. |

All factor calculations live in `src/risk_engine.py::calculate_risk_factors()`,
which is fully unit-tested in `tests/test_risk_engine.py` (boundary values,
caps, and invalid/negative inputs included).

## 4. Recommended actions

Recommended actions are looked up per risk level from a static table in
`src/config.py::RECOMMENDED_ACTIONS`. They are presented in the UI as
**educational examples**, not as universal or prescriptive security policy —
real organizations would define these based on their own HR, legal, and
security policies.

## 5. Data ethics and scope

- All employee, department, campaign, and incident data in this project is
  **synthetically generated** (`data/seed_data.py`), using a fixed random
  seed for reproducibility.
- No real phishing emails are sent, no credential-harvesting pages are
  created, and no real personal or sensitive employee data (passwords,
  national IDs, health data, etc.) is modeled or stored anywhere in the
  schema.
- The `security_incidents` table stores only short, generic fictional
  descriptions (e.g. "left workstation unlocked") — never real incident
  reports.
