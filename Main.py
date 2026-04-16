from pathlib import Path

import pandas as pd
from finder import analyze_person


DATASET_FILE = "bcn_hack.csv"
FAST_MODE = False  # Set to True only for quick demos
FAST_MODE_ROWS = 10
OUTPUT_FILE = "scored_cases.csv"


# =====================
# LOAD DATA
# =====================
def load_dataset(path: str) -> pd.DataFrame:
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(file)


# =====================
# SCORE HELPERS
# =====================
def score_recovery(legal_asset_finding: str) -> int:
    recovery_map = {
        "employment_income": 95,
        "bank_account": 85,
        "vehicle": 60,
        "pension": 50,
        "multiple": 75,
        "assets_not_seizable": 20,
        "no_assets_found": 10,
        "not_initiated": 15,
    }
    return recovery_map.get(str(legal_asset_finding), 15)


def score_contact(call_outcome: str) -> int:
    contact_map = {
        "payment_plan": 95,
        "voicemail": 55,
        "busy": 45,
        "relative": 35,
        "rings_out": 18,
        "invalid_number": 5,
        "not_debtor": 8,
        "denies_identity": 8,
        "hung_up": 12,
        "needs_proof": 25,
        "wont_pay": 18,
        "never_owed": 0,
    }
    return contact_map.get(str(call_outcome), 25)


def score_debt_value(debt_eur: float) -> int:
    if debt_eur >= 75000:
        return 100
    if debt_eur >= 50000:
        return 90
    if debt_eur >= 20000:
        return 75
    if debt_eur >= 10000:
        return 55
    if debt_eur >= 5000:
        return 40
    return 25


def score_origin(debt_origin: str) -> int:
    origin_map = {
        "mortgage_shortfall": 80,
        "sme_loan": 75,
        "personal_loan": 65,
        "auto_loan": 60,
        "consumer_loan": 55,
        "credit_card": 45,
        "utility": 25,
        "telecom": 20,
    }
    return origin_map.get(str(debt_origin), 40)


def compute_age_penalty(debt_age_months: int) -> int:
    if debt_age_months >= 30:
        return 20
    if debt_age_months >= 18:
        return 10
    if debt_age_months >= 12:
        return 5
    return 0


def compute_friction_penalty(call_attempts: int) -> int:
    if call_attempts >= 7:
        return 18
    if call_attempts >= 5:
        return 12
    if call_attempts >= 3:
        return 6
    return 0


# =====================
# CORE SCORING
# =====================
def compute_scores(row: pd.Series) -> pd.Series:
    recovery_score = score_recovery(str(row["legal_asset_finding"]))
    contact_score = score_contact(str(row["call_outcome"]))
    debt_score = score_debt_value(float(row["debt_eur"]))
    origin_score = score_origin(str(row["debt_origin"]))

    age_penalty = compute_age_penalty(int(row["debt_age_months"]))
    friction_penalty = compute_friction_penalty(int(row["call_attempts"]))

    enrichment = analyze_person(str(row["case_id"]), str(row["country"]))
    ghost_score = int(enrichment.get("ghost_score", 50))
    footprint_summary = enrichment.get("summary", "unknown footprint")
    footprint_results = int(enrichment.get("results", 0))

    enrichment_bonus = max(0, 100 - ghost_score) * 0.15

    priority_score = int(
        0.40 * recovery_score
        + 0.20 * debt_score
        + 0.12 * contact_score
        + 0.10 * origin_score
        + enrichment_bonus
        - age_penalty
        - friction_penalty
    )
    priority_score = max(0, min(100, priority_score))

    return pd.Series(
        {
            "recovery_score": recovery_score,
            "contact_score": contact_score,
            "debt_score": debt_score,
            "origin_score": origin_score,
            "ghost_score": ghost_score,
            "footprint_summary": footprint_summary,
            "footprint_results": footprint_results,
            "age_penalty": age_penalty,
            "friction_penalty": friction_penalty,
            "priority_score": priority_score,
        }
    )


# =====================
# DECISION LAYER
# =====================
def make_decision(row: pd.Series) -> str:
    if row["call_outcome"] == "never_owed":
        return "STOP / DISPUTE REVIEW"

    # High value + strong recovery → go hard
    if row["priority_score"] >= 75 and row["recovery_score"] >= 80:
        return "PURSUE AGGRESSIVELY"

    # Good case but cannot reach → enrich first
    if row["priority_score"] >= 60 and row["contact_score"] <= 10:
        return "ENRICH BEFORE CONTACT"

    # Solid case → normal action
    if row["priority_score"] >= 50:
        return "PRIORITIZED SOFT ACTION"

    # Low value → ignore for now
    return "DEPRIORITIZE / MONITOR"


def next_best_action(row: pd.Series) -> str:
    if row["decision"] == "STOP / DISPUTE REVIEW":
        return "Review legal dispute / liability issue before any outreach"
    if row["decision"] == "PURSUE AGGRESSIVELY":
        return "Immediate collector review and repayment / settlement outreach"
    if row["decision"] == "ENRICH BEFORE CONTACT":
        return "Verify phone / address and enrich employment or asset signals first"
    if row["decision"] == "PRIORITIZED SOFT ACTION":
        return "Schedule structured outreach and monitor response quality"
    return "Keep in low-priority queue and revisit only if new signal appears"


def priority_band(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


# =====================
# REASONING LAYER
# =====================
def build_reasoning(row: pd.Series) -> str:
    reasons = []

    if row["recovery_score"] >= 80:
        reasons.append("strong recoverability")
    elif row["recovery_score"] >= 50:
        reasons.append("moderate recoverability")
    else:
        reasons.append("weak recoverability")

    if row["contact_score"] >= 50:
        reasons.append("good contactability")
    elif row["contact_score"] >= 20:
        reasons.append("average contactability")
    else:
        reasons.append("poor contactability")

    if row["debt_score"] >= 70:
        reasons.append("high debt value")
    elif row["debt_score"] >= 40:
        reasons.append("medium debt value")
    else:
        reasons.append("low debt value")

    if row["origin_score"] >= 70:
        reasons.append("high-value debt type")
    elif row["origin_score"] <= 25:
        reasons.append("lower-value debt type")

    if row["ghost_score"] <= 35:
        reasons.append("strong public footprint")
    elif row["ghost_score"] <= 60:
        reasons.append("moderate public footprint")
    else:
        reasons.append("weak public footprint")

    if row["age_penalty"] >= 10:
        reasons.append("older debt")
    elif int(row["debt_age_months"]) <= 8:
        reasons.append("recent debt")

    if row["friction_penalty"] >= 12:
        reasons.append("many failed attempts")
    elif int(row["call_attempts"]) <= 2:
        reasons.append("few attempts so far")

    return ", ".join(reasons)


# =====================
# PLACEHOLDER ENRICHMENT
# =====================
def build_linkedin_placeholder() -> str:
    return "Not available (no enrichment credits)"


# =====================
# MAIN
# =====================
def main() -> None:
    df = load_dataset(DATASET_FILE)

    if FAST_MODE:
        df = df.head(FAST_MODE_ROWS).copy()
    else:
        df = df.copy()

    computed = df.apply(compute_scores, axis=1)
    df = pd.concat([df, computed], axis=1)

    df["final_score"] = df["priority_score"]
    df["priority_band"] = df["priority_score"].apply(priority_band)
    df["decision"] = df.apply(make_decision, axis=1)
    df["next_best_action"] = df.apply(next_best_action, axis=1)
    df["reasoning"] = df.apply(build_reasoning, axis=1)
    df["linkedin_info"] = build_linkedin_placeholder()

    top = df.sort_values(["final_score", "debt_eur"], ascending=[False, False])

    print("\n=== TOP CASES ===\n")

    for _, row in top.head(10).iterrows():
        print(
            f"CASE {row['case_id']} ({row['country']})\n"
            f"Debt: €{row['debt_eur']} | Origin: {row['debt_origin']} | Age: {row['debt_age_months']} months\n"
            f"Call Outcome: {row['call_outcome']} | Legal Asset Finding: {row['legal_asset_finding']}\n\n"
            f"Recovery Score: {row['recovery_score']}\n"
            f"Contact Score: {row['contact_score']}\n"
            f"Debt Score: {row['debt_score']}\n"
            f"Origin Score: {row['origin_score']}\n"
            f"Ghost Score: {row['ghost_score']}\n"
            f"Priority Score: {row['priority_score']} ({row['priority_band']})\n"
            f"Final Score: {row['final_score']:.2f}\n\n"
            f"Decision: {row['decision']}\n"
            f"Next Best Action: {row['next_best_action']}\n"
            f"Why: {row['reasoning']}\n"
            "----------------------------------------"
        )

    export_columns = [
        "case_id",
        "country",
        "debt_eur",
        "debt_origin",
        "debt_age_months",
        "call_attempts",
        "call_outcome",
        "legal_asset_finding",
        "recovery_score",
        "contact_score",
        "debt_score",
        "origin_score",
        "ghost_score",
        "footprint_summary",
        "footprint_results",
        "friction_penalty",
        "priority_score",
        "priority_band",
        "final_score",
        "decision",
        "next_best_action",
        "reasoning",
        "linkedin_info",
    ]
    top[export_columns].to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved scored output to {OUTPUT_FILE}\n")


if __name__ == "__main__":
    main()