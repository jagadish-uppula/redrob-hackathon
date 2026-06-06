"""
Scoring Engine — combines extracted features into a final composite score.

The scorer applies the weighted feature combination and then multiplicative
penalties for honeypots, consulting-only careers, and other red flags
identified from the JD.
"""

from typing import Optional

from src.config import (
    SCORING_WEIGHTS,
    HONEYPOT_PENALTY,
    CONSULTING_ONLY_PENALTY,
    TITLE_CHASER_PENALTY,
    CV_ONLY_PENALTY,
    RESEARCH_ONLY_PENALTY,
    TITLE_SCORES,
    DEFAULT_TITLE_SCORE,
)
from src.honeypot import detect_honeypot
from src.jd_parser import JDRequirements


def compute_score(
    candidate: dict,
    features: dict,
    jd_requirements: Optional[JDRequirements] = None,
) -> dict:
    """Compute the final ranking score for a candidate.

    Args:
        candidate: The raw candidate dict from candidates.jsonl
        features: The feature dict from features.extract_features()
        jd_requirements: Optional JD requirements (reserved for future use)

    Returns:
        dict with 'final_score', 'base_score', 'penalties', and 'breakdown'
    """
    # -----------------------------------------------------------------
    # Step 1: Weighted base score from features
    # -----------------------------------------------------------------
    base_components = {
        "title_match":      features["title_match"],
        "career_relevance": features["career_relevance"],
        "skills_match":     features["skills_match"],
        "experience_fit":   features["experience_fit"],
        "education":        features["education"],
        "location":         features["location"],
        "behavioral":       features["behavioral"],
    }

    base_score = sum(
        base_components[key] * SCORING_WEIGHTS[key]
        for key in SCORING_WEIGHTS
    )

    # -----------------------------------------------------------------
    # Step 2: Skill trust modifier
    # If skills trust is low (keyword stuffer), reduce score
    # -----------------------------------------------------------------
    trust = features.get("skill_trust", 0.5)
    if trust < 0.3:
        base_score *= (0.5 + trust)  # Penalty for untrustworthy skills

    # -----------------------------------------------------------------
    # Step 3: Multiplicative penalties
    # -----------------------------------------------------------------
    penalties = []
    penalty_multiplier = 1.0

    # Honeypot detection
    is_honeypot, honeypot_reasons = detect_honeypot(candidate)
    if is_honeypot:
        penalty_multiplier *= HONEYPOT_PENALTY
        penalties.append(f"HONEYPOT: {'; '.join(honeypot_reasons)}")

    # Consulting-only career
    if features.get("consulting_only", 0) > 0.5:
        penalty_multiplier *= CONSULTING_ONLY_PENALTY
        penalties.append("Entire career at consulting/services firms")

    # Title-chaser pattern
    if features.get("title_chaser", 0) > 0.5:
        penalty_multiplier *= TITLE_CHASER_PENALTY
        penalties.append("Title-chaser: avg tenure < 18 months across 3+ jobs")

    # Computer vision only (check if CV skills dominate without NLP/IR)
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "")
    if title == "Computer Vision Engineer":
        skills = candidate.get("skills", [])
        skill_names_lower = {s.get("name", "").lower() for s in skills}
        has_nlp = any(
            kw in skill_names_lower
            for kw in ["nlp", "natural language processing", "retrieval",
                       "search", "ranking", "information retrieval",
                       "text classification", "text mining"]
        )
        if not has_nlp:
            penalty_multiplier *= CV_ONLY_PENALTY
            penalties.append("Computer vision only — no NLP/IR exposure")

    # Research-only check for AI Research Engineers
    if title == "AI Research Engineer":
        if features.get("has_production_experience", 0) < 0.2:
            penalty_multiplier *= RESEARCH_ONLY_PENALTY
            penalties.append("AI Research with no production deployment signals")

    # -----------------------------------------------------------------
    # Step 4: Bonus for very strong candidates
    # Small boost if multiple strong signals align
    # -----------------------------------------------------------------
    bonus = 1.0
    if (features["title_match"] >= 0.85 and
            features["career_relevance"] >= 0.5 and
            features["behavioral"] >= 0.6):
        # Strong alignment bonus
        bonus = 1.05

    if (features.get("has_production_experience", 0) >= 0.5 and
            features.get("must_have_count", 0) >= 3):
        # Production + skills alignment
        bonus *= 1.03

    # -----------------------------------------------------------------
    # Step 5: Final score
    # -----------------------------------------------------------------
    final_score = base_score * penalty_multiplier * bonus

    # Clamp to [0, 1]
    final_score = max(0.0, min(1.0, final_score))

    return {
        "final_score": round(final_score, 6),
        "base_score": round(base_score, 6),
        "penalty_multiplier": round(penalty_multiplier, 4),
        "bonus": round(bonus, 4),
        "penalties": penalties,
        "breakdown": {
            k: round(v, 4) for k, v in base_components.items()
        },
    }
