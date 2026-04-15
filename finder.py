import requests

CACHE = {}


def google_search(query):
    """
    Optional web enrichment.
    If API fails or missing → returns empty safely.
    """

    try:
        # OPTIONAL: replace with SerpAPI if you have key
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "engine": "google",
            "api_key": "YOUR_KEY",  # or hardcoded for hackathon
            "num": 5
        }

        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        return data.get("organic_results", [])

    except:
        return []


def analyze_person(identifier, country):
    """
    Ghost detection + identity signal extraction
    """

    key = f"{identifier}_{country}"

    if key in CACHE:
        return CACHE[key]

    query = f"{identifier} {country} linkedin company profile"
    results = google_search(query)

    text = " ".join(
        (r.get("title", "") + " " + r.get("snippet", "")).lower()
        for r in results
    )

    # -------------------------
    # SIGNALS
    # -------------------------
    name_hits = text.count(str(identifier).lower())
    linkedin_hits = text.count("linkedin")

    company_hits = sum(
        k in text for k in ["ceo", "founder", "engineer", "company", "director"]
    )

    total = len(results)

    # -------------------------
    # GHOST SCORE
    # -------------------------
    if total == 0:
        ghost_score = 100
    else:
        ghost_score = max(
            0,
            100 - (name_hits * 25 + linkedin_hits * 20 + company_hits * 15)
        )

    # -------------------------
    # CONFIDENCE
    # -------------------------
    confidence = min(
        100,
        name_hits * 30 + linkedin_hits * 25 + total * 10
    )

    output = {
        "ghost_score": ghost_score,
        "confidence": confidence,
        "results": total
    }

    CACHE[key] = output
    return output