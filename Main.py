from pathlib import Path

import pandas as pd
from finder import analyze_person



DATASET_FILE = "bcn_hack.csv"
# FAST_MODE limits processing to a subset of rows for quick demos.
# Set FAST_MODE = False to process the full dataset.
FAST_MODE = False  # Set to True only for quick demos
FAST_MODE_ROWS = 10


# =====================
# LOAD DATA
# =====================
def load_dataset(path: str) -> pd.DataFrame:
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(file)


# =====================
# CORE SCORING
# =====================
def compute_scores(row: pd.Series):
    # RECOVERY
    recovery_map = {
        "employment_income": 90,
        "bank_account": 80,
        "vehicle": 60,
        "pension": 50,
    }
    recovery = recovery_map.get(row["legal_asset_finding"], 10)

    # CONTACT
    contact_map = {
        "voicemail": 50,
        "busy": 40,
        "rings_out": 20,
        "invalid_number": 5,
        "not_debtor": 10,
    }
    contact = contact_map.get(row["call_outcome"], 25)

    # DEBT VALUE
    debt = row["debt_eur"]
    debt_score = (
        90 if debt > 50000 else
        70 if debt > 20000 else
        50 if debt > 10000 else
        30
    )

    # ENRICHMENT LAYER
    enrichment = analyze_person(str(row["case_id"]), str(row["country"]))
    ghost_score = enrichment.get("ghost_score", 50)
    confidence = enrichment.get("confidence", 20)

    # FINAL PRIORITY SCORE
    priority_score = int(
        0.35 * recovery +
        0.25 * debt_score +
        0.15 * contact +
        0.25 * (100 - ghost_score)
    )

    return pd.Series({
        "recovery_score": recovery,
        "contact_score": contact,
        "debt_score": debt_score,
        "priority_score": priority_score,
        "ghost_score": ghost_score,
        "confidence": confidence,
    })


# =====================
# DECISION LAYER
# =====================
def make_decision(row: pd.Series) -> str:
    if row["ghost_score"] > 60:
        return "ENRICH / INVESTIGATE"
    if row["recovery_score"] >= 80:
        return "PURSUE DIRECTLY"
    if row["contact_score"] <= 10:
        return "VERIFY CONTACT DATA"
    return "MONITOR / SOFT APPROACH"


# =====================
# MAIN
# =====================
def main():
    df = load_dataset(DATASET_FILE)

    if FAST_MODE:
        df = df.head(FAST_MODE_ROWS).copy()
    else:
        df = df.copy()

    computed = df.apply(compute_scores, axis=1)
    df = pd.concat([df, computed], axis=1)

    df["final_score"] = (df["priority_score"] * (df["confidence"] / 100)).round(2)
    df["decision"] = df.apply(make_decision, axis=1)

    top = df.sort_values("final_score", ascending=False)

    print("\n=== TOP CASES ===\n")

    for _, row in top.head(10).iterrows():
        print(
            f"CASE {row['case_id']} ({row['country']})\n"
            f"Debt: €{row['debt_eur']}\n\n"
            f"Recovery Score: {row['recovery_score']}\n"
            f"Contact Score: {row['contact_score']}\n"
            f"Debt Score: {row['debt_score']}\n"
            f"Ghost Score: {row['ghost_score']}\n"
            f"Confidence: {row['confidence']}\n"
            f"Priority Score: {row['priority_score']}\n"
            f"Final Score: {row['final_score']:.2f}\n\n"
            f"Decision: {row['decision']}\n"
            "----------------------------------------"
        )


if __name__ == "__main__":
    main()