"""
Human Risk & Security Awareness Tracker — Streamlit application.

Educational/demonstrative GRC tool. All data is fictional. This app
performs NO real phishing simulation, credential collection, or
employee surveillance of any kind — see README.md for the full
ethical/safety disclaimer.

Run with: streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src import analytics, database as db
from src.recommendations import get_recommendation_panel

st.set_page_config(
    page_title="Human Risk & Security Awareness Tracker",
    page_icon="🛡️",
    layout="wide",
)

RISK_COLORS = {
    "Low": "#2E7D32",
    "Medium": "#F9A825",
    "High": "#EF6C00",
    "Critical": "#C62828",
}


def ensure_db_ready():
    """Streamlit reruns the whole script on every interaction, so this
    just makes sure the schema exists — it does NOT reseed data."""
    db.init_db()


@st.cache_resource
def get_conn():
    return db.get_connection()


def risk_badge(level: str) -> str:
    color = RISK_COLORS.get(level, "#999999")
    return f"<span style='background-color:{color};color:white;padding:2px 10px;border-radius:12px;font-size:0.85em'>{level}</span>"


def render_disclaimer_banner():
    st.info(
        "🔎 **Demonstrative project.** All employees, campaigns, and incidents "
        "are fictional. No real phishing emails, credential collection, or "
        "employee surveillance are performed by this application.",
        icon="ℹ️",
    )


def page_corporate_dashboard(conn):
    st.title("🛡️ Corporate Risk Dashboard")
    render_disclaimer_banner()

    kpis = analytics.get_corporate_kpis(conn)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Employees", kpis.total_employees)
    col2.metric("Training Completion", f"{kpis.training_completion_rate}%")
    col3.metric("MFA Adoption", f"{kpis.mfa_adoption_rate}%")
    col4.metric("Policy Acknowledgment", f"{kpis.policy_ack_rate}%")

    col5, col6, col7 = st.columns(3)
    col5.metric("Phishing Click Rate", f"{kpis.phishing_click_rate}%")
    col6.metric("Phishing Report Rate", f"{kpis.phishing_report_rate}%")
    col7.metric("Open Risk Actions", kpis.open_risk_actions)

    st.divider()

    left, right = st.columns([1, 1])

    with left:
        st.subheader("Risk Level Distribution")
        dist_df = pd.DataFrame(
            {
                "Level": ["Low", "Medium", "High", "Critical"],
                "Count": [kpis.low_risk, kpis.medium_risk, kpis.high_risk, kpis.critical_risk],
            }
        )
        fig = px.bar(
            dist_df, x="Level", y="Count", color="Level",
            color_discrete_map=RISK_COLORS,
            category_orders={"Level": ["Low", "Medium", "High", "Critical"]},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Security Awareness Campaigns")
        campaigns = analytics.get_campaign_summaries(conn)
        camp_df = pd.DataFrame(
            [
                {
                    "Campaign": c["name"],
                    "Completion %": c["completion_rate"],
                    "Awareness Score": c["awareness_score"],
                    "Risk Reduction %": c["risk_reduction"],
                }
                for c in campaigns
            ]
        )
        st.dataframe(camp_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Open Human Risk Actions")
    actions = db.get_open_actions(conn)
    if actions:
        actions_df = pd.DataFrame(
            [{"Employee": a["employee_id"], "Action": a["action"], "Date": a["action_date"]} for a in actions]
        )
        st.dataframe(actions_df.head(20), use_container_width=True, hide_index=True)
        if len(actions) > 20:
            st.caption(f"Showing 20 of {len(actions)} open actions.")
    else:
        st.caption("No open risk actions.")


def page_department_analysis(conn):
    st.title("🏢 Department Risk Analysis")
    render_disclaimer_banner()

    summaries = analytics.get_department_summaries(conn)
    df = pd.DataFrame(
        [
            {
                "Department": s.department,
                "Employees": s.employee_count,
                "Avg Risk Score": s.avg_risk_score,
                "Training Completion %": s.training_completion_rate,
                "MFA Adoption %": s.mfa_adoption_rate,
                "Avg Awareness Score": s.avg_awareness_score,
            }
            for s in summaries
        ]
    ).sort_values("Avg Risk Score", ascending=False)

    fig = px.bar(
        df, x="Department", y="Avg Risk Score", color="Avg Risk Score",
        color_continuous_scale=["#2E7D32", "#F9A825", "#C62828"],
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Department Details")
    st.dataframe(df, use_container_width=True, hide_index=True)


def page_trends(conn):
    st.title("📈 Human Risk Trends")
    render_disclaimer_banner()
    st.caption(
        "Historical periods in this demo are synthetically generated with an "
        "illustrative improvement trend — not real historical data."
    )

    trend = analytics.get_trend_series(conn)
    if not trend:
        st.warning("No historical data available. Run the seed script to generate it.")
        return

    df = pd.DataFrame([vars(p) for p in trend])
    df["period_date"] = pd.to_datetime(df["period_date"])

    st.subheader("Average Human Risk Score Over Time")
    fig_score = px.line(df, x="period_date", y="avg_risk_score", markers=True)
    fig_score.update_layout(yaxis_title="Avg Risk Score", xaxis_title="")
    st.plotly_chart(fig_score, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Training & Policy Completion")
        fig_training = px.line(
            df, x="period_date",
            y=["training_completion_rate", "policy_ack_rate"],
            markers=True,
        )
        fig_training.update_layout(yaxis_title="%", xaxis_title="", legend_title="")
        st.plotly_chart(fig_training, use_container_width=True)

    with col2:
        st.subheader("Phishing Simulation Rates")
        fig_phishing = px.line(
            df, x="period_date",
            y=["phishing_click_rate", "phishing_report_rate"],
            markers=True,
        )
        fig_phishing.update_layout(yaxis_title="%", xaxis_title="", legend_title="")
        st.plotly_chart(fig_phishing, use_container_width=True)

    st.subheader("Average Awareness Score")
    fig_awareness = px.line(df, x="period_date", y="avg_awareness_score", markers=True)
    fig_awareness.update_layout(yaxis_title="Avg Awareness Score", xaxis_title="")
    st.plotly_chart(fig_awareness, use_container_width=True)


def page_employee_profile(conn):
    st.title("👤 Employee Risk Profile")
    render_disclaimer_banner()

    employees = db.get_all_employees(conn)
    options = {f"{e['name']} ({e['employee_id']}, {e['department']})": e["employee_id"] for e in employees}
    selected_label = st.selectbox("Select an employee", sorted(options.keys()))
    employee_id = options[selected_label]

    profile = analytics.get_employee_profile(conn, employee_id)
    if profile is None:
        st.warning("No profile found.")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(profile.name)
        st.write(f"**Department:** {profile.department}  |  **Role:** {profile.role}  |  **Manager:** {profile.manager}")
        st.markdown(f"**Risk Level:** {risk_badge(profile.risk_level or 'Unknown')}", unsafe_allow_html=True)
        st.metric("Human Risk Score", profile.risk_score if profile.risk_score is not None else "N/A")

    with col2:
        st.write("**MFA Enabled:**", "✅" if profile.mfa_enabled else "❌")
        st.write("**Last Training:**", profile.last_training_date or "Never")
        st.write("**Awareness Score:**", profile.awareness_score if profile.awareness_score is not None else "N/A")
        st.write("**Policy Acknowledged:**", "✅" if profile.policy_acknowledged else "❌")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Risk Score Breakdown")
        if profile.factors:
            for f in profile.factors:
                st.write(f"+ {f['points']}  {f['label']}")
            st.write(f"**Total: {profile.risk_score}**")
        else:
            st.caption("No risk factors triggered — clean profile.")
        st.caption(
            "This score is a demonstrative model built for this portfolio "
            "project. See docs/risk_methodology.md for the full rationale."
        )

    with right:
        st.subheader("Recommended Actions")
        if profile.risk_level:
            panel = get_recommendation_panel(profile.risk_level)
            st.write(f"*{panel.description}*")
            st.write(f"**Urgency:** {panel.urgency}")
            for action in panel.actions:
                st.write(f"- {action}")
            st.caption(panel.disclaimer)

    st.divider()
    st.subheader("Phishing Simulation History")
    if profile.simulation_history:
        sim_df = pd.DataFrame(profile.simulation_history)
        st.dataframe(sim_df, use_container_width=True, hide_index=True)
    else:
        st.caption("No simulation history for this employee.")


def main():
    ensure_db_ready()
    conn = get_conn()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Corporate Dashboard", "Department Analysis", "Human Risk Trends", "Employee Profile"],
    )

    if page == "Corporate Dashboard":
        page_corporate_dashboard(conn)
    elif page == "Department Analysis":
        page_department_analysis(conn)
    elif page == "Human Risk Trends":
        page_trends(conn)
    elif page == "Employee Profile":
        page_employee_profile(conn)

    st.sidebar.divider()
    st.sidebar.caption(
        "Human Risk & Security Awareness Tracker — demonstrative GRC "
        "portfolio project. All data is fictional."
    )


if __name__ == "__main__":
    main()
