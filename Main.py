from pathlib import Path
import pandas as pd


# ====== CONFIG ======
DATASET_FILE = "bcn_hack.csv"


# ====== LOAD DATASET ======
def load_dataset(file_path: str) -> pd.DataFrame:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset introuvable: {file_path}\n"
            "Mets le fichier CSV dans le dossier du projet avec le nom 'bcn_hack.csv'."
        )

    return pd.read_csv(path)


# ====== IMPROVED SCORING ======
def compute_scores(row):
    # Recovery score (real ability to pay)
    if row["legal_asset_finding"] == "employment_income":
        recovery = 90
    elif row["legal_asset_finding"] == "bank_account":
        recovery = 80
    elif row["legal_asset_finding"] == "vehicle":
        recovery = 60
    elif row["legal_asset_finding"] == "pension":
        recovery = 50
    else:
        recovery = 10  # lower than before

    # Contact score
    if row["call_outcome"] == "voicemail":
        contact = 50
    elif row["call_outcome"] == "busy":
        contact = 40
    elif row["call_outcome"] == "rings_out":
        contact = 20
    elif row["call_outcome"] == "invalid_number":
        contact = 5
    elif row["call_outcome"] == "not_debtor":
        contact = 10
    else:
        contact = 25

    # Debt value
    debt = row["debt_eur"]
    if debt > 50000:
        debt_score = 90
    elif debt > 20000:
        debt_score = 70
    elif debt > 10000:
        debt_score = 50
    else:
        debt_score = 30

    # FINAL PRIORITY (balanced)
    priority = int((0.5 * recovery) + (0.3 * debt_score) + (0.2 * contact))

    return recovery, contact, priority


# ====== SMART ACTION ======
def recommend_action(row):
    recovery, contact, priority = compute_scores(row)

    if recovery > 70:
        return "Strong recovery -> pursue aggressively"

    if recovery < 30 and contact < 20:
        return "Low value -> deprioritize"

    if contact < 15:
        return "Enrich data before contact"

    return "Monitor / soft approach"


# ====== HUMAN-STYLE EXPLANATION ======
def explain_case(row):
    recovery, contact, priority = compute_scores(row)

    insights = []

    if recovery > 70:
        insights.append("Assets detected (income or account)")
    elif recovery < 30:
        insights.append("No clear assets found")

    if contact < 15:
        insights.append("Contact data is weak")

    if row["debt_eur"] > 20000:
        insights.append("High financial exposure")

    if row["call_outcome"] in ["rings_out", "invalid_number"]:
        insights.append("Repeated failed contact attempts")

    if not insights:
        insights.append("Limited but usable signal")

    return " | ".join(insights)


# ====== MAIN ======
def main():
    df = load_dataset(DATASET_FILE)

    df["recovery_score"] = df.apply(lambda row: compute_scores(row)[0], axis=1)
    df["contact_score"] = df.apply(lambda row: compute_scores(row)[1], axis=1)
    df["priority_score"] = df.apply(lambda row: compute_scores(row)[2], axis=1)
    df["action"] = df.apply(recommend_action, axis=1)
    df["explanation"] = df.apply(explain_case, axis=1)

    print("\nTOP 10 HIGH-VALUE CASES (SMART PRIORITIZATION)\n")

    top_cases = df.sort_values(by="priority_score", ascending=False)

    for _, row in top_cases.head(10).iterrows():
        print(f"""
CASE {row['case_id']} ({row['country']})
Debt: €{row['debt_eur']}

Scores:
- Recovery: {row['recovery_score']}
- Contact: {row['contact_score']}
- Priority: {row['priority_score']}

Insight:
{row['explanation']}

Action:
{row['action']}
----------------------------------------
""")


if __name__ == "__main__":
    main()