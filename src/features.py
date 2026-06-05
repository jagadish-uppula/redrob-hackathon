"""
Feature Extractor — converts raw candidate JSON into numerical feature vectors.

Pure Python implementation (no ML models) designed for speed:
~0.5ms per candidate → 100K candidates in ~50 seconds.

Feature groups:
1. Title Match (0-1)
2. Career Relevance (0-1)
3. Skills Match (0-1)
4. Experience Fit (0-1)
5. Education Score (0-1)
6. Location Score (0-1)
7. Behavioral Score (0-1)
"""

import math
import re
from datetime import datetime, date
from typing import Dict, Any

from src.config import (
    TITLE_SCORES, DEFAULT_TITLE_SCORE,
    CAREER_KEYWORDS_TIER1, CAREER_KEYWORDS_TIER2,
    CAREER_KEYWORDS_PRODUCTION, CAREER_KEYWORDS_DATA,
    MUST_HAVE_SKILLS, NICE_TO_HAVE_SKILLS, AI_RELEVANT_SKILLS,
    CONSULTING_COMPANIES, IT_SERVICES_INDUSTRY,
    IDEAL_EXPERIENCE_YEARS, EXPERIENCE_SIGMA,
    MIN_RELEVANT_YEARS, MAX_RELEVANT_YEARS,
    PREFERRED_COUNTRY, PREFERRED_CITIES, TIER1_CITIES,
    EDUCATION_TIER_SCORES, RELEVANT_FIELDS,
    ACTIVITY_DECAY_DAYS, IDEAL_NOTICE_DAYS, MAX_ACCEPTABLE_NOTICE,
    MIN_RESPONSE_RATE, IDEAL_RESPONSE_RATE, MIN_PROFILE_COMPLETE,
)


# Reference date for the dataset (competition runs ~June 2026)
REFERENCE_DATE = date(2026, 6, 1)


def extract_features(candidate: dict) -> Dict[str, float]:
    """Extract all scoring features from a candidate record.

    Returns a dict of feature_name → float (all normalized to 0-1 range).
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    education = candidate.get("education", [])
    skills = candidate.get("skills", [])
    certs = candidate.get("certifications", [])
    signals = candidate.get("redrob_signals", {})

    features = {}

    # -----------------------------------------------------------------
    # 1. TITLE MATCH
    # -----------------------------------------------------------------
    features["title_match"] = _compute_title_score(profile)

    # -----------------------------------------------------------------
    # 2. CAREER RELEVANCE
    # -----------------------------------------------------------------
    career_result = _compute_career_relevance(career, profile)
    features["career_relevance"] = career_result["relevance"]
    features["has_production_experience"] = career_result["production"]
    features["consulting_only"] = career_result["consulting_only"]
    features["title_chaser"] = career_result["title_chaser"]
    features["career_keyword_density"] = career_result["keyword_density"]

    # -----------------------------------------------------------------
    # 3. SKILLS MATCH
    # -----------------------------------------------------------------
    skills_result = _compute_skills_score(skills, signals, profile)
    features["skills_match"] = skills_result["match_score"]
    features["skill_trust"] = skills_result["trust_score"]
    features["must_have_count"] = skills_result["must_have_count"]
    features["nice_to_have_count"] = skills_result["nice_to_have_count"]

    # -----------------------------------------------------------------
    # 4. EXPERIENCE FIT
    # -----------------------------------------------------------------
    features["experience_fit"] = _compute_experience_score(profile)

    # -----------------------------------------------------------------
    # 5. EDUCATION
    # -----------------------------------------------------------------
    features["education"] = _compute_education_score(education)

    # -----------------------------------------------------------------
    # 6. LOCATION
    # -----------------------------------------------------------------
    features["location"] = _compute_location_score(profile, signals)

    # -----------------------------------------------------------------
    # 7. BEHAVIORAL
    # -----------------------------------------------------------------
    features["behavioral"] = _compute_behavioral_score(signals)

    return features


# =====================================================================
# 1. TITLE MATCHING
# =====================================================================

def _compute_title_score(profile: dict) -> float:
    """Score based on current job title alignment with target role."""
    title = profile.get("current_title", "")
    return TITLE_SCORES.get(title, DEFAULT_TITLE_SCORE)


# =====================================================================
# 2. CAREER RELEVANCE
# =====================================================================

def _compute_career_relevance(career: list, profile: dict) -> dict:
    """Analyze career history for relevance, production experience,
    consulting-only patterns, and title-chaser behavior."""

    if not career:
        return {
            "relevance": 0.0,
            "production": 0.0,
            "consulting_only": 1.0,
            "title_chaser": 0.0,
            "keyword_density": 0.0,
        }

    total_keyword_score = 0.0
    total_production_score = 0.0
    total_months = 0
    consulting_months = 0
    job_tenures = []

    for job in career:
        desc = (job.get("description", "") or "").lower()
        company = (job.get("company", "") or "").lower()
        industry = (job.get("industry", "") or "")
        company_size = job.get("company_size", "")
        duration = job.get("duration_months", 0)
        total_months += duration
        job_tenures.append(duration)

        # Check if this is a consulting/services company
        is_consulting = (
            company in CONSULTING_COMPANIES
            or any(c in company for c in CONSULTING_COMPANIES)
            or (industry == IT_SERVICES_INDUSTRY and company_size in ("5001-10000", "10001+"))
        )
        if is_consulting:
            consulting_months += duration

        # Score career description keywords (weighted by duration)
        duration_weight = min(duration / 24.0, 1.5)  # Cap at 1.5x for long tenures
        job_keyword_score = 0.0

        for keyword, weight in CAREER_KEYWORDS_TIER1.items():
            if keyword in desc:
                job_keyword_score += weight
        for keyword, weight in CAREER_KEYWORDS_TIER2.items():
            if keyword in desc:
                job_keyword_score += weight
        for keyword, weight in CAREER_KEYWORDS_DATA.items():
            if keyword in desc:
                job_keyword_score += weight

        total_keyword_score += job_keyword_score * duration_weight

        # Production experience scoring
        for keyword, weight in CAREER_KEYWORDS_PRODUCTION.items():
            if keyword in desc:
                total_production_score += weight

    # Normalize keyword score (empirical max ~30 for a perfect candidate)
    max_keyword_score = 30.0
    keyword_density = min(total_keyword_score / max_keyword_score, 1.0)

    # Production experience (empirical max ~10)
    production_score = min(total_production_score / 10.0, 1.0)

    # Consulting-only flag
    if total_months > 0:
        consulting_ratio = consulting_months / total_months
        consulting_only = 1.0 if consulting_ratio > 0.95 else 0.0
    else:
        consulting_only = 0.0

    # Title-chaser detection: avg tenure < 18 months across 3+ jobs
    if len(job_tenures) >= 3:
        avg_tenure = sum(job_tenures) / len(job_tenures)
        title_chaser = 1.0 if avg_tenure < 18 else 0.0
    else:
        title_chaser = 0.0

    # Combined career relevance
    relevance = (
        0.65 * keyword_density +
        0.35 * production_score
    )

    return {
        "relevance": relevance,
        "production": production_score,
        "consulting_only": consulting_only,
        "title_chaser": title_chaser,
        "keyword_density": keyword_density,
    }


# =====================================================================
# 3. SKILLS MATCH
# =====================================================================

def _compute_skills_score(skills: list, signals: dict, profile: dict) -> dict:
    """Score skills based on must-have/nice-to-have match, proficiency depth,
    and trust validation (to catch keyword stuffers)."""

    must_have_count = 0
    nice_to_have_count = 0
    total_trust = 0.0
    skill_count = 0

    assessment_scores = signals.get("skill_assessment_scores", {})

    proficiency_weights = {
        "beginner": 0.2,
        "intermediate": 0.5,
        "advanced": 0.8,
        "expert": 1.0,
    }

    for sk in skills:
        name_lower = sk.get("name", "").lower()
        proficiency = sk.get("proficiency", "beginner")
        duration = sk.get("duration_months", 0)
        endorsements = sk.get("endorsements", 0)

        # Check must-have and nice-to-have matches
        if name_lower in MUST_HAVE_SKILLS or any(mh in name_lower for mh in MUST_HAVE_SKILLS):
            must_have_count += 1
        elif name_lower in NICE_TO_HAVE_SKILLS or any(nh in name_lower for nh in NICE_TO_HAVE_SKILLS):
            nice_to_have_count += 1

        # Trust score: proficiency should be backed by duration and endorsements
        prof_weight = proficiency_weights.get(proficiency, 0.2)
        duration_weight = min(duration / 24.0, 1.0) if duration > 0 else 0.05
        endorse_weight = min(endorsements / 15.0, 1.0) if endorsements > 0 else 0.1

        # If there's a platform assessment score, factor it in
        if sk.get("name", "") in assessment_scores:
            assessment = assessment_scores[sk["name"]]
            assessment_weight = assessment / 100.0
            trust = (prof_weight * 0.25 + duration_weight * 0.30 +
                     endorse_weight * 0.15 + assessment_weight * 0.30)
        else:
            trust = (prof_weight * 0.30 + duration_weight * 0.45 +
                     endorse_weight * 0.25)

        total_trust += trust
        skill_count += 1

    # Normalize must-have (out of ~16 possible)
    must_have_score = min(must_have_count / 6.0, 1.0)

    # Normalize nice-to-have (out of ~30 possible)
    nice_to_have_score = min(nice_to_have_count / 5.0, 1.0)

    # Combined match score
    match_score = 0.70 * must_have_score + 0.30 * nice_to_have_score

    # Average trust across all skills
    avg_trust = total_trust / max(skill_count, 1)

    # Cross-validate: if title is non-tech but has many AI skills → reduce trust
    title = profile.get("current_title", "")
    title_score = TITLE_SCORES.get(title, DEFAULT_TITLE_SCORE)
    if title_score <= 0.02:
        # Non-tech title → AI skills are suspicious, reduce match score
        match_score *= 0.15
        avg_trust *= 0.3

    return {
        "match_score": match_score,
        "trust_score": avg_trust,
        "must_have_count": must_have_count,
        "nice_to_have_count": nice_to_have_count,
    }


# =====================================================================
# 4. EXPERIENCE FIT
# =====================================================================

def _compute_experience_score(profile: dict) -> float:
    """Gaussian scoring centered on ideal experience years."""
    yoe = profile.get("years_of_experience", 0)

    if yoe < MIN_RELEVANT_YEARS * 0.5:
        return 0.05  # Way too junior

    # Gaussian centered at ideal years
    deviation = (yoe - IDEAL_EXPERIENCE_YEARS) / EXPERIENCE_SIGMA
    score = math.exp(-0.5 * deviation * deviation)

    # Small penalty for being way under or over
    if yoe < MIN_RELEVANT_YEARS:
        score *= 0.5
    elif yoe > MAX_RELEVANT_YEARS:
        score *= 0.7

    return score


# =====================================================================
# 5. EDUCATION
# =====================================================================

def _compute_education_score(education: list) -> float:
    """Score based on institution tier and field relevance."""
    if not education:
        return 0.2  # No education listed

    best_score = 0.0
    for ed in education:
        tier = ed.get("tier", "unknown")
        tier_score = EDUCATION_TIER_SCORES.get(tier, 0.2)

        field = (ed.get("field_of_study", "") or "").lower()
        field_relevant = any(rf in field for rf in RELEVANT_FIELDS)

        # Relevant field gets a bonus
        ed_score = tier_score
        if field_relevant:
            ed_score = min(ed_score * 1.3, 1.0)

        # Higher degree bonus
        degree = (ed.get("degree", "") or "").lower()
        if any(d in degree for d in ["ph.d", "phd", "doctorate"]):
            ed_score = min(ed_score * 1.15, 1.0)
        elif any(d in degree for d in ["m.tech", "m.e.", "m.sc", "mba", "m.s."]):
            ed_score = min(ed_score * 1.05, 1.0)

        best_score = max(best_score, ed_score)

    return best_score


# =====================================================================
# 6. LOCATION
# =====================================================================

def _compute_location_score(profile: dict, signals: dict) -> float:
    """Score based on geographic proximity to preferred locations."""
    country = (profile.get("country", "") or "").strip()
    location = (profile.get("location", "") or "").lower().strip()
    willing_to_relocate = signals.get("willing_to_relocate", False)
    work_mode = signals.get("preferred_work_mode", "")

    score = 0.0

    if country == PREFERRED_COUNTRY:
        score = 0.7

        # City bonus
        for city in TIER1_CITIES:
            if city in location:
                score = 1.0
                break
        else:
            for city in PREFERRED_CITIES:
                if city in location:
                    score = 0.85
                    break
    else:
        # Non-India candidates
        if willing_to_relocate:
            score = 0.45
        else:
            score = 0.25

    # Work mode compatibility (JD is hybrid)
    if work_mode == "remote" and country != PREFERRED_COUNTRY:
        score *= 0.7
    elif work_mode in ("hybrid", "flexible"):
        score = min(score * 1.05, 1.0)
    elif work_mode == "onsite" and country == PREFERRED_COUNTRY:
        score = min(score * 1.02, 1.0)

    return score


# =====================================================================
# 7. BEHAVIORAL SIGNALS
# =====================================================================

def _compute_behavioral_score(signals: dict) -> float:
    """Score based on availability and engagement signals.

    A perfect-on-paper candidate who hasn't logged in for 6 months
    and has a 5% response rate is not actually available.
    """
    components = []

    # --- Recruiter response rate (most important behavioral signal) ---
    response_rate = signals.get("recruiter_response_rate", 0.0)
    if response_rate < MIN_RESPONSE_RATE:
        resp_score = 0.05
    elif response_rate >= IDEAL_RESPONSE_RATE:
        resp_score = 1.0
    else:
        # Linear scale between min and ideal
        resp_score = (response_rate - MIN_RESPONSE_RATE) / (IDEAL_RESPONSE_RATE - MIN_RESPONSE_RATE)
    components.append(("response_rate", resp_score, 0.25))

    # --- Recency of activity ---
    last_active = signals.get("last_active_date", "")
    if last_active:
        try:
            last_active_date = date.fromisoformat(last_active)
            days_inactive = (REFERENCE_DATE - last_active_date).days
            if days_inactive <= 0:
                activity_score = 1.0
            elif days_inactive <= 30:
                activity_score = 0.95
            elif days_inactive <= 90:
                activity_score = 0.80
            elif days_inactive <= ACTIVITY_DECAY_DAYS:
                activity_score = 0.50
            else:
                # Exponential decay beyond threshold
                excess = days_inactive - ACTIVITY_DECAY_DAYS
                activity_score = max(0.1, 0.50 * math.exp(-excess / 180.0))
        except (ValueError, TypeError):
            activity_score = 0.3
    else:
        activity_score = 0.3
    components.append(("activity", activity_score, 0.18))

    # --- Open to work flag ---
    open_to_work = signals.get("open_to_work_flag", False)
    otw_score = 1.0 if open_to_work else 0.40
    components.append(("open_to_work", otw_score, 0.12))

    # --- Notice period ---
    notice_days = signals.get("notice_period_days", 60)
    if notice_days <= IDEAL_NOTICE_DAYS:
        notice_score = 1.0
    elif notice_days <= MAX_ACCEPTABLE_NOTICE:
        # Linear decay from ideal to max
        notice_score = 1.0 - 0.5 * (notice_days - IDEAL_NOTICE_DAYS) / (MAX_ACCEPTABLE_NOTICE - IDEAL_NOTICE_DAYS)
    else:
        notice_score = max(0.15, 0.5 - 0.3 * (notice_days - MAX_ACCEPTABLE_NOTICE) / 90.0)
    components.append(("notice_period", notice_score, 0.10))

    # --- Interview completion rate ---
    interview_rate = signals.get("interview_completion_rate", 0.5)
    interview_score = min(interview_rate / 0.8, 1.0)
    components.append(("interview_rate", interview_score, 0.10))

    # --- Profile completeness ---
    completeness = signals.get("profile_completeness_score", 50.0)
    if completeness >= 80:
        complete_score = 1.0
    elif completeness >= MIN_PROFILE_COMPLETE:
        complete_score = 0.5 + 0.5 * (completeness - MIN_PROFILE_COMPLETE) / (80 - MIN_PROFILE_COMPLETE)
    else:
        complete_score = max(0.1, completeness / 100.0)
    components.append(("completeness", complete_score, 0.08))

    # --- GitHub activity ---
    github = signals.get("github_activity_score", -1)
    if github < 0:
        github_score = 0.3  # No GitHub linked — not a dealbreaker but not great
    elif github >= 50:
        github_score = 1.0
    else:
        github_score = 0.3 + 0.7 * (github / 50.0)
    components.append(("github", github_score, 0.07))

    # --- Offer acceptance rate ---
    offer_rate = signals.get("offer_acceptance_rate", -1)
    if offer_rate < 0:
        offer_score = 0.5  # No offer history
    else:
        offer_score = min(offer_rate / 0.7, 1.0)
    components.append(("offer_rate", offer_score, 0.05))

    # --- Verification signals ---
    verified_email = signals.get("verified_email", False)
    verified_phone = signals.get("verified_phone", False)
    linkedin = signals.get("linkedin_connected", False)
    verify_score = (
        (0.4 if verified_email else 0.0) +
        (0.3 if verified_phone else 0.0) +
        (0.3 if linkedin else 0.0)
    )
    components.append(("verification", verify_score, 0.05))

    # Weighted sum
    total_weight = sum(w for _, _, w in components)
    score = sum(s * w for _, s, w in components) / total_weight

    return score
