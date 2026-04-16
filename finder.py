CACHE = {}


def google_search(query: str):
    """
    Deterministic demo search.
    Because the dataset is anonymized, this simulates different public-footprint levels
    without pretending to be a real lookup.
    """
    digits = "".join(ch for ch in query if ch.isdigit())
    bucket = int(digits) % 4 if digits else 0

    if bucket == 0:
        return [
            {
                "title": f"{query} - LinkedIn profile",
                "snippet": "Active professional profile with role history and company references",
            },
            {
                "title": f"{query} - business registry result",
                "snippet": "Possible director or founder signal with registration reference",
            },
            {
                "title": f"{query} - public web mention",
                "snippet": "Multiple identity matches across public sources",
            },
        ]

    if bucket == 1:
        return [
            {
                "title": f"{query} - directory result",
                "snippet": "Partial profile with employment mention",
            },
            {
                "title": f"{query} - web mention",
                "snippet": "Limited but usable public footprint",
            },
        ]

    if bucket == 2:
        return [
            {
                "title": f"{query} - sparse result",
                "snippet": "Very limited public information available",
            }
        ]

    return [
        {
            "title": f"{query} - registry reference",
            "snippet": "Possible company or banking relationship signal",
        },
        {
            "title": f"{query} - social mention",
            "snippet": "Some public presence but fragmented identity trail",
        },
    ]


def analyze_person(identifier: str, country: str):
    key = f"{identifier}_{country}"
    if key in CACHE:
        return CACHE[key]

    results = google_search(f"{identifier} {country}")
    text = " ".join(
        (r.get("title", "") + " " + r.get("snippet", "")).lower()
        for r in results
    )

    linkedin_hits = text.count("linkedin")
    registry_hits = text.count("registry") + text.count("registration")
    company_hits = text.count("company") + text.count("director") + text.count("founder")
    employment_hits = text.count("employment") + text.count("professional") + text.count("role")
    banking_hits = text.count("bank") + text.count("banking") + text.count("account")
    total_results = len(results)

    footprint_score = (
        linkedin_hits * 12
        + registry_hits * 10
        + company_hits * 8
        + employment_hits * 6
        + banking_hits * 8
        + total_results * 8
    )

    ghost_score = max(20, min(85, 90 - footprint_score))

    if ghost_score <= 35:
        summary = "strong public footprint"
    elif ghost_score <= 55:
        summary = "medium public footprint"
    else:
        summary = "weak public footprint"

    signals_found = []
    if linkedin_hits:
        signals_found.append("LinkedIn mention")
    if registry_hits:
        signals_found.append("Registry mention")
    if company_hits:
        signals_found.append("Company-related signal")
    if employment_hits:
        signals_found.append("Employment-related signal")
    if banking_hits:
        signals_found.append("Banking-related signal")
    if not signals_found:
        signals_found.append("No strong public signal found")

    if ghost_score <= 35:
        enrichment_recommendation = "Proceed with targeted enrichment"
    elif ghost_score <= 55:
        enrichment_recommendation = "Manual verification recommended"
    else:
        enrichment_recommendation = "Limited footprint; deprioritize enrichment"

    output = {
        "ghost_score": ghost_score,
        "summary": summary,
        "results": total_results,
        "signals_found": signals_found,
        "enrichment_recommendation": enrichment_recommendation,
    }
    CACHE[key] = output
    return output
