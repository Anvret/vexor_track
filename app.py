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


# Human-readable explanation for why a case has a high or low score
def explain_priority(row: pd.Series) -> str:
    reasons = []

    priority_score = float(row.get("priority_score", 0))
    recovery_score = float(row.get("recovery_score", 0))
    contact_score = float(row.get("contact_score", 0))
    debt_score = float(row.get("debt_score", 0))
    ghost_score = float(row.get("ghost_score", 50))

    if priority_score >= 70:
        level = "This case scores high because"
    elif priority_score >= 45:
        level = "This case scores medium because"
    else:
        level = "This case scores low because"

    if recovery_score >= 80:
        reasons.append("there is a strong recoverability signal")
    elif recovery_score <= 20:
        reasons.append("there is no strong recoverability signal")

    if contact_score >= 50:
        reasons.append("the debtor seems more reachable than average")
    elif contact_score <= 10:
        reasons.append("contactability is very weak")

    if debt_score >= 75:
        reasons.append("the economic value of the case is high")
    elif debt_score <= 30:
        reasons.append("the debt amount is relatively small")

    if ghost_score <= 35:
        reasons.append("public-footprint signals are relatively strong")
    elif ghost_score >= 70:
        reasons.append("very little public-footprint signal was found")

    if "age_penalty" in row.index and float(row["age_penalty"]) >= 10:
        reasons.append("the debt is older, which reduces urgency")

    if "friction_penalty" in row.index and float(row["friction_penalty"]) >= 8:
        reasons.append("multiple failed attempts make the case more operationally expensive")

    if not reasons:
        reasons.append("the available signals are mixed")

    return level + " " + ", ".join(reasons) + "."


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
    col2.metric("Avg priority", round(df["priority_score"].mean(), 1))
    col3.metric("High priority cases", int((df["priority_score"] >= 70).sum()))
    col4.metric("Countries", df["country"].nunique())

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
        (filtered["debt_eur"] >= debt_range[0]) &
        (filtered["debt_eur"] <= debt_range[1]) &
        (filtered["priority_score"] >= priority_range[0]) &
        (filtered["priority_score"] <= priority_range[1])
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
        "reasoning",
    ]
    display_columns = [col for col in preferred_display_columns if col in filtered.columns]

    if "reasoning" not in filtered.columns:
        st.info("The current scored_cases.csv file does not include a reasoning column yet. The app will still work without it.")

    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True,
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
        st.write(f"**Debt:** €{case['debt_eur']}")
        st.write(f"**Debt origin:** {case['debt_origin']}")
        st.write(f"**Debt age:** {case['debt_age_months']} months")
        st.write(f"**Call attempts:** {case['call_attempts']}")
        st.write(f"**Call outcome:** {case['call_outcome']}")
        st.write(f"**Legal asset finding:** {case['legal_asset_finding']}")

    with right:
        st.markdown("### Decision summary")
        st.write(f"**Priority score:** {case['priority_score']} ({score_badge(case['priority_score'])})")
        st.write(f"**Final score:** {case['final_score']}")
        st.write(f"**Decision:** {case['decision']}")
        st.markdown("### Score explanation")
        st.write(explain_priority(case))
        if "reasoning" in case.index:
            st.write(f"**Model reasoning:** {case['reasoning']}")
        else:
            st.write("**Model reasoning:** Not available in the current scored output")

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