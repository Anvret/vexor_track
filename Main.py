from pathlib import Path
import pandas as pd
from finder import analyze_person


# =====================
# LOAD DATA
# =====================
def load_dataset(path):
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError("CSV not found")
    return pd.read_csv(file)


# =====================
# CORE SCORING
# =====================
def compute_scores(row):

    # ---------------------
    # RECOVERY
    # ---------------------
    recovery_map = {
        "employment_income": 90,
        "bank_account": 80,
        "vehicle": 60,
        "pension": 50
    }
    recovery = recovery_map.get(row["legal_asset_finding"], 10)

    # ---------------------
    # CONTACT
    # ---------------------
    contact_map = {
        "voicemail": 50,
        "busy": 40,
        "rings_out": 20,
        "invalid_number": 5,
        "not_debtor": 10
    }
    contact = contact_map.get(row["call_outcome"], 25)

    # ---------------------
    # DEBT VALUE
    # ---------------------
    debt = row["debt_eur"]
    debt_score = (
        90 if debt > 50000 else
        70 if debt > 20000 else
        50 if debt > 10000 else
        30
    )

    # ---------------------
    # ENRICHMENT LAYER
    # ---------------------
    enrichment = analyze_person(row["case_id"], row["country"])

    ghost_score = enrichment["ghost_score"]
    confidence = enrichment["confidence"]

    # ---------------------
    # FINAL PRIORITY SCORE
    # ---------------------
    priority = int(
        0.35 * recovery +
        0.25 * debt_score +
        0.15 * contact +
        0.25 * (100 - ghost_score)
    )

    return recovery, contact, debt_score, priority, ghost_score, confidence


# =====================
# MAIN
# =====================
def main():

    df = load_dataset("bcn_hack.csv")

    # 🔥 FAST MODE FOR DEMO
    df = df.head(10)

    computed = df.apply(lambda r: pd.Series(compute_scores(r)), axis=1)

    computed.columns = [
        "recovery_score",
        "contact_score",
        "debt_score",
        "priority_score",
        "ghost_score",
        "confidence"
    ]

    df = pd.concat([df, computed], axis=1)

    df["final_score"] = df["priority_score"] * (df["confidence"] / 100)

    top = df.sort_values("final_score", ascending=False)

    print("\n=== TOP CASES ===\n")

    for _, row in top.head(10).iterrows():
        print(f"""
CASE {row['case_id']} ({row['country']})
Debt: €{row['debt_eur']}

Recovery: {row['recovery_score']}
Contact: {row['contact_score']}
Debt Score: {row['debt_score']}
Ghost Score: {row['ghost_score']}
Confidence: {row['confidence']}
Final Score: {row['final_score']:.2f}

Decision:
{"ENRICH / INVESTIGATE" if row["ghost_score"] > 60 else "PURSUE DIRECTLY"}

----------------------------------------
""")


if __name__ == "__main__":
    main()