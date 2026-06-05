"""
Reasoning Generator — produces fact-specific, non-hallucinated reasoning
strings for each ranked candidate.

Each reasoning is unique because it pulls actual data from the candidate's
profile. The template approach ensures:
1. Specific facts (title, years, skills, company)
2. JD connection (references what the JD wants)
3. Honest concerns (gaps, notice period, location)
4. No hallucination (only references data that exists)
5. Variation (different candidates get different text)
6. Rank consistency (top candidates get positive framing, lower get measured)
"""

from src.config import TITLE_SCORES, DEFAULT_TITLE_SCORE


def generate_reasoning(
    candidate: dict,
    features: dict,
    score_result: dict,
    rank: int,
) -> str:
    """Generate a 1-2 sentence reasoning for why this candidate is at this rank.

    The reasoning must:
    - Reference specific facts from the candidate's profile
    - Connect to the JD requirements
    - Acknowledge concerns where they exist
    - Never mention skills/companies/facts not in the profile
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})

    title = profile.get("current_title", "Unknown")
    yoe = profile.get("years_of_experience", 0)
    company = profile.get("current_company", "Unknown")
    industry = profile.get("current_industry", "")
    country = profile.get("country", "")
    location = profile.get("location", "")

    response_rate = signals.get("recruiter_response_rate", 0)
    notice = signals.get("notice_period_days", 0)
    open_to_work = signals.get("open_to_work_flag", False)
    github = signals.get("github_activity_score", -1)

    breakdown = score_result.get("breakdown", {})
    penalties = score_result.get("penalties", [])

    # --- Build strengths ---
    strengths = []

    # Title relevance
    title_score = TITLE_SCORES.get(title, DEFAULT_TITLE_SCORE)
    if title_score >= 0.85:
        strengths.append(f"directly relevant title ({title})")
    elif title_score >= 0.60:
        strengths.append(f"adjacent technical role ({title})")
    elif title_score >= 0.35:
        strengths.append(f"general tech background ({title})")

    # Experience
    if 5.0 <= yoe <= 9.0:
        strengths.append(f"{yoe}y experience in the ideal 5-9 year range")
    elif 4.0 <= yoe <= 12.0:
        strengths.append(f"{yoe}y relevant experience")

    # Career relevance
    if features.get("career_relevance", 0) >= 0.5:
        # Find career keywords that matched
        career_highlights = _extract_career_highlights(career)
        if career_highlights:
            strengths.append(career_highlights)

    # Skills
    mh_count = features.get("must_have_count", 0)
    if mh_count >= 3:
        top_skills = _get_top_matching_skills(skills)
        if top_skills:
            strengths.append(f"key skills: {top_skills}")

    # Production experience
    if features.get("has_production_experience", 0) >= 0.4:
        strengths.append("demonstrated production deployment experience")

    # Behavioral
    if response_rate >= 0.6:
        strengths.append(f"strong engagement ({response_rate:.0%} response rate)")
    elif response_rate >= 0.4:
        strengths.append(f"decent engagement ({response_rate:.0%} response rate)")

    # GitHub
    if github >= 40:
        strengths.append(f"active GitHub (score: {github:.0f}/100)")

    # Location
    if country == "India":
        if any(c in location.lower() for c in ["pune", "noida"]):
            strengths.append(f"based in {location} (preferred location)")
        else:
            strengths.append(f"India-based ({location})")

    # --- Build concerns ---
    concerns = []

    if title_score < 0.35:
        concerns.append(f"non-core title ({title})")

    if yoe < 4.0:
        concerns.append(f"below ideal experience ({yoe}y)")
    elif yoe > 12.0:
        concerns.append(f"over ideal experience range ({yoe}y)")

    if notice > 60:
        concerns.append(f"long notice period ({notice} days)")

    if response_rate < 0.20:
        concerns.append(f"low response rate ({response_rate:.0%})")

    if not open_to_work:
        concerns.append("not marked open to work")

    if country != "India":
        concerns.append(f"located outside India ({country})")

    if features.get("consulting_only", 0) > 0.5:
        concerns.append("entire career at consulting/services firms")

    if penalties:
        for p in penalties[:1]:  # Only mention the top penalty
            if "HONEYPOT" not in p:  # Don't mention honeypot detection
                concerns.append(p.lower())

    # --- Compose the reasoning ---
    parts = []

    # Sentence 1: Main strengths
    if strengths:
        main_strengths = "; ".join(strengths[:3])
        parts.append(f"{title} at {company} with {yoe}y experience — {main_strengths}.")
    else:
        parts.append(f"{title} at {company} with {yoe}y experience.")

    # Sentence 2: Concerns or additional context
    if rank <= 10:
        # Top 10: emphasize fit
        if concerns:
            parts.append(f"Minor considerations: {'; '.join(concerns[:2])}.")
        else:
            parts.append("Strong overall alignment with JD requirements.")
    elif rank <= 50:
        if concerns:
            parts.append(f"Considerations: {'; '.join(concerns[:2])}.")
    else:
        # Lower ranks: acknowledge why they're lower
        if concerns:
            parts.append(f"Concerns: {'; '.join(concerns[:2])}.")
        else:
            parts.append("Included based on partial skill/experience alignment.")

    return " ".join(parts)


def _extract_career_highlights(career: list) -> str:
    """Extract key career highlights relevant to the JD."""
    highlights = []

    relevant_keywords = [
        ("retrieval", "retrieval systems"),
        ("search", "search infrastructure"),
        ("ranking", "ranking systems"),
        ("recommendation", "recommendation systems"),
        ("embedding", "embedding systems"),
        ("vector", "vector search"),
        ("nlp", "NLP"),
        ("machine learning", "ML"),
        ("deep learning", "deep learning"),
        ("model", "model development"),
        ("pipeline", "data pipelines"),
    ]

    for job in career:
        desc_lower = (job.get("description", "") or "").lower()
        job_title = job.get("title", "")
        company = job.get("company", "")

        for keyword, label in relevant_keywords:
            if keyword in desc_lower and label not in highlights:
                highlights.append(label)
                break  # One highlight per job

    if highlights:
        return f"career includes {', '.join(highlights[:3])}"
    return ""


def _get_top_matching_skills(skills: list) -> str:
    """Get the top matching skill names for display in reasoning."""
    from src.config import MUST_HAVE_SKILLS, NICE_TO_HAVE_SKILLS

    matched = []
    for sk in skills:
        name = sk.get("name", "")
        name_lower = name.lower()
        if name_lower in MUST_HAVE_SKILLS or any(mh in name_lower for mh in MUST_HAVE_SKILLS):
            matched.append(name)

    if not matched:
        for sk in skills:
            name = sk.get("name", "")
            name_lower = name.lower()
            if name_lower in NICE_TO_HAVE_SKILLS or any(nh in name_lower for nh in NICE_TO_HAVE_SKILLS):
                matched.append(name)

    return ", ".join(matched[:4]) if matched else ""
