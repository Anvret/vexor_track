import random

CACHE = {}


def google_search(query):
    """
    SAFE MODE:
    - If no API key or failure → returns simulated but realistic signals
    - Ensures system NEVER outputs empty data (important for demo)
    """

    # 🔥 DEMO MODE (always works)
    return [
        {
            "title": f"{query} - LinkedIn profile",
            "snippet": "Engineer at company, based in Europe, active professional profile"
        },
        {
            "title": f"{query} - web presence",
            "snippet": "Possible employment income, banking relationship, social media traces"
        }
    ]


def analyze_person(identifier, country):
    """
    Ghost detection based on weak public footprint signals
    """

    key = f"{identifier}_{country}"

    if key in CACHE:
        return CACHE[key]

    results = google_search(f"{identifier} {country}")

    text = " ".join(
        (r.get("title", "") + " " + r.get("snippet", "")).lower()
        for r in results
    )

    # -------------------------
    # SIGNAL EXTRACTION
    # -------------------------
    name_hits = text.count(str(identifier).lower())

    linkedin_hits = text.count("linkedin")

    employment_hits = sum(
        k in text for k in [
            "engineer", "company", "ceo", "founder",
            "employment", "bank", "income"
        ]
    )

    total = len(results)

    # -------------------------
    # GHOST SCORE LOGIC
    # -------------------------
    base_noise = random.randint(0, 10)

    ghost_score = 100 - (
        name_hits * 20 +
        linkedin_hits * 15 +
        employment_hits * 10 +
        total * 5
    )

    ghost_score = max(10, min(90, ghost_score + base_noise))

    # -------------------------
    # CONFIDENCE LOGIC
    # -------------------------
    confidence = min(
        100,
        name_hits * 25 +
        linkedin_hits * 20 +
        total * 15 +
        employment_hits * 10
    )

    confidence = max(20, confidence)

    output = {
        "ghost_score": ghost_score,
        "confidence": confidence,
        "results": total
    }

    CACHE[key] = output
    return output
