from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Vexor Case Prioritization", layout="wide")

DATA_FILE = "scored_cases.csv"


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(
            f"{path} not found. Run Main.py first to generate scored_cases.csv"
        )
    return pd.read_csv(file)


def score_badge(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def explain_priority(row: pd.Series):
    priority_score = float(row.get("priority_score", 0))
    recovery_score = float(row.get("recovery_score", 0))
    contact_score = float(row.get("contact_score", 0))
    debt_score = float(row.get("debt_score", 0))
    ghost_score = float(row.get("ghost_score", 50))
    debt_amount = float(row.get("debt_eur", 0))
    debt_age = float(row.get("debt_age_months", 0))
    call_attempts = float(row.get("call_attempts", 0))

    if priority_score >= 70:
        score_label = "High"
        summary = "This case should be reviewed first because several signals are favorable."
    elif priority_score >= 45:
        score_label = "Medium"
        summary = "This case is interesting, but the signals are mixed."
    else:
        score_label = "Low"
        summary = "This case is less attractive right now because the strongest signals are weak."

    positive_points = []
    negative_points = []
    neutral_points = []

    if recovery_score >= 80:
        positive_points.append(f"Recoverability is strong ({int(recovery_score)}/100).")
    elif recovery_score >= 50:
        neutral_points.append(f"Recoverability is moderate ({int(recovery_score)}/100).")
    else:
        negative_points.append(f"Recoverability is weak ({int(recovery_score)}/100).")

    if contact_score >= 50:
        positive_points.append(
            f"Contactability is good ({int(contact_score)}/100), so outreach may be easier."
        )
    elif contact_score >= 20:
        neutral_points.append(f"Contactability is average ({int(contact_score)}/100).")
    else:
        negative_points.append(
            f"Contactability is poor ({int(contact_score)}/100), so direct action is harder."
        )

    if debt_score >= 75:
        positive_points.append(
            f"The debt amount is high (€{debt_amount:,.0f}), which makes the case financially important."
        )
    elif debt_score >= 40:
        neutral_points.append(f"The debt amount is medium (€{debt_amount:,.0f}).")
    else:
        negative_points.append(f"The debt amount is relatively low (€{debt_amount:,.0f}).")

    if ghost_score <= 35:
        positive_points.append(
            f"Public-footprint signals are strong (ghost score: {int(ghost_score)}), so enrichment looks easier."
        )
    elif ghost_score <= 60:
        neutral_points.append(
            f"Public-footprint signals are moderate (ghost score: {int(ghost_score)})."
        )
    else:
        negative_points.append(
            f"Very little public-footprint signal was found (ghost score: {int(ghost_score)})."
        )

    if "age_penalty" in row.index:
        age_penalty = float(row.get("age_penalty", 0))
        if age_penalty >= 10:
            negative_points.append(
                f"The debt is old ({int(debt_age)} months), which reduces urgency."
            )
        elif debt_age > 0:
            neutral_points.append(f"Debt age is {int(debt_age)} months.")

    if "friction_penalty" in row.index:
        friction_penalty = float(row.get("friction_penalty", 0))
        if friction_penalty >= 8:
            negative_points.append(
                f"There have already been {int(call_attempts)} call attempts, which increases servicing cost."
            )
        elif call_attempts > 0:
            neutral_points.append(f"There have been {int(call_attempts)} call attempts so far.")

    return {
        "score_label": score_label,
        "summary": summary,
        "positive_points": positive_points,
        "negative_points": negative_points,
        "neutral_points": neutral_points,
    }


def main():
    st.title("Vexor - Debt Case Prioritization")
    st.caption("Actionable ranking for anonymized debt collection cases")

    try:
        df = load_data(DATA_FILE)
    except Exception as e:
        st.error(str(e))
        st.info("Run this first in terminal: python3 Main.py")
        return

    st.subheader("Overview")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total cases", len(df))
    col2.metric("Average priority score", round(df["priority_score"].mean(), 1))
    col3.metric("High priority cases", int((df["priority_score"] >= 70).sum()))
    col4.metric("Countries covered", df["country"].nunique())

    st.divider()

    st.sidebar.header("Filters")

    countries = ["All"] + sorted(df["country"].dropna().unique().tolist())
    decisions = ["All"] + sorted(df["decision"].dropna().unique().tolist())
    origins = ["All"] + sorted(df["debt_origin"].dropna().unique().tolist())

    selected_country = st.sidebar.selectbox("Country", countries)
    selected_decision = st.sidebar.selectbox("Decision", decisions)
    selected_origin = st.sidebar.selectbox("Debt origin", origins)

    min_debt, max_debt = int(df["debt_eur"].min()), int(df["debt_eur"].max())
    debt_range = st.sidebar.slider(
        "Debt range (€)",
        min_value=min_debt,
        max_value=max_debt,
        value=(min_debt, max_debt),
    )

    min_priority, max_priority = int(df["priority_score"].min()), int(df["priority_score"].max())
    priority_range = st.sidebar.slider(
        "Priority score",
        min_value=min_priority,
        max_value=max_priority,
        value=(min_priority, max_priority),
    )

    filtered = df.copy()

    if selected_country != "All":
        filtered = filtered[filtered["country"] == selected_country]

    if selected_decision != "All":
        filtered = filtered[filtered["decision"] == selected_decision]

    if selected_origin != "All":
        filtered = filtered[filtered["debt_origin"] == selected_origin]

    filtered = filtered[
        (filtered["debt_eur"] >= debt_range[0])
        & (filtered["debt_eur"] <= debt_range[1])
        & (filtered["priority_score"] >= priority_range[0])
        & (filtered["priority_score"] <= priority_range[1])
    ]

    filtered = filtered.sort_values(["final_score", "debt_eur"], ascending=[False, False])

    st.subheader("Top actionable cases")

    preferred_display_columns = [
        "case_id",
        "country",
        "debt_eur",
        "debt_origin",
        "debt_age_months",
        "call_outcome",
        "legal_asset_finding",
        "priority_score",
        "final_score",
        "decision",
        "linkedin_info",
        "reasoning",
    ]

    if "linkedin_info" not in filtered.columns:
        filtered["linkedin_info"] = "Not available (no enrichment credits)"

    display_columns = [col for col in preferred_display_columns if col in filtered.columns]
    table_df = filtered[display_columns].copy()

    st.dataframe(
        table_df,
        width="stretch",
        hide_index=True,
        height=360,
    )

    st.divider()
    st.subheader("Case details")

    if filtered.empty:
        st.warning("No cases match the current filters.")
        return

    case_options = filtered["case_id"].tolist()
    selected_case = st.selectbox("Select a case", case_options)

    case = filtered[filtered["case_id"] == selected_case].iloc[0]

    left, right = st.columns([1, 1])

    with left:
        st.markdown(f"### Case {case['case_id']}")
        st.write(f"**Country:** {case['country']}")
        st.write(f"**Debt amount:** €{case['debt_eur']}")
        st.write(f"**Debt origin:** {case['debt_origin']}")
        st.write(f"**Debt age:** {case['debt_age_months']} months")
        st.write(f"**Call attempts:** {case['call_attempts']}")
        st.write(f"**Call outcome:** {case['call_outcome']}")
        st.write(f"**Legal asset finding:** {case['legal_asset_finding']}")
        if "linkedin_info" in case.index:
            st.write(f"**LinkedIn enrichment:** {case['linkedin_info']}")

    with right:
        st.markdown("### Decision summary")
        st.write(f"**Priority score:** {case['priority_score']} ({score_badge(case['priority_score'])})")
        st.write(f"**Final score:** {case['final_score']}")
        st.write(f"**Decision:** {case['decision']}")

        explanation = explain_priority(case)

        st.markdown("### Score explanation")
        st.write(f"**Score level:** {explanation['score_label']}")
        st.write(explanation["summary"])

        if explanation["positive_points"]:
            st.markdown("**What helps this case**")
            for point in explanation["positive_points"]:
                st.write(f"- {point}")

        if explanation["negative_points"]:
            st.markdown("**What hurts this case**")
            for point in explanation["negative_points"]:
                st.write(f"- {point}")

        if explanation["neutral_points"]:
            st.markdown("**Other context**")
            for point in explanation["neutral_points"]:
                st.write(f"- {point}")

        if "reasoning" in case.index:
            st.markdown("### Model reasoning")
            st.write(case["reasoning"])
        else:
            st.write("Model reasoning is not available in the current scored output.")

        extra_cols = [
            "recovery_score",
            "contact_score",
            "debt_score",
            "ghost_score",
            "footprint_summary",
            "age_penalty",
            "friction_penalty",
        ]

        available_extra = [c for c in extra_cols if c in case.index]
        if available_extra:
            st.markdown("### Score components")
            for col in available_extra:
                st.write(f"**{col}:** {case[col]}")

    st.divider()
    st.download_button(
        label="Download filtered cases as CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="filtered_scored_cases.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()