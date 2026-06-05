"""
Honeypot Detector — identifies candidates with subtly impossible profiles.

The dataset contains ~80 honeypot candidates that are forced to relevance
tier 0 in the ground truth. Ranking them in the top 100 will hurt our score,
and having >10% honeypot rate in top 100 causes disqualification.

Detection strategies:
1. Expert skills with zero or near-zero duration
2. Skill assessment scores contradicting proficiency level
3. Unrealistic experience claims
4. Too many expert-level skills (stuffer pattern)
5. Title-skill extreme mismatch patterns
"""

from src.config import (
    MAX_EXPERT_SKILLS,
    EXPERT_MIN_DURATION_MONTHS,
    SKILL_ASSESSMENT_MIN,
    MAX_CAREER_EXPERIENCE_GAP,
    TITLE_SCORES,
    AI_RELEVANT_SKILLS,
)


def detect_honeypot(candidate: dict) -> tuple[bool, list[str]]:
    """Detect if a candidate has a subtly impossible profile.

    Returns:
        (is_honeypot: bool, reasons: list[str])
    """
    flags = []
    score = 0.0  # Honeypot suspicion score

    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    education = candidate.get("education", [])
    signals = candidate.get("redrob_signals", {})

    # -------------------------------------------------------------------------
    # Check 1: Expert skills with 0 or very low duration
    # A genuine expert wouldn't have 0 months of experience with a skill.
    # -------------------------------------------------------------------------
    expert_zero_duration = 0
    for sk in skills:
        if sk.get("proficiency") == "expert":
            duration = sk.get("duration_months", 0)
            if duration < EXPERT_MIN_DURATION_MONTHS:
                expert_zero_duration += 1
                score += 2.0

    if expert_zero_duration >= 2:
        flags.append(
            f"{expert_zero_duration} expert skills with <{EXPERT_MIN_DURATION_MONTHS} months duration"
        )

    # -------------------------------------------------------------------------
    # Check 2: Too many expert-level skills
    # Having 8+ expert skills is statistically very unlikely and signals
    # keyword stuffing or fabrication.
    # -------------------------------------------------------------------------
    expert_count = sum(1 for sk in skills if sk.get("proficiency") == "expert")
    if expert_count >= MAX_EXPERT_SKILLS:
        score += 2.0
        flags.append(f"{expert_count} expert-level skills (threshold: {MAX_EXPERT_SKILLS})")

    # -------------------------------------------------------------------------
    # Check 3: Skill assessment scores contradicting proficiency
    # If a candidate claims "expert" proficiency but their platform assessment
    # score is very low, that's suspicious.
    # -------------------------------------------------------------------------
    assessment_scores = signals.get("skill_assessment_scores", {})
    for sk in skills:
        skill_name = sk.get("name", "")
        proficiency = sk.get("proficiency", "")
        if proficiency in ("expert", "advanced") and skill_name in assessment_scores:
            if assessment_scores[skill_name] < SKILL_ASSESSMENT_MIN:
                score += 1.5
                flags.append(
                    f"Skill '{skill_name}': claims {proficiency} but assessment={assessment_scores[skill_name]}"
                )

    # -------------------------------------------------------------------------
    # Check 4: Career duration vs years_of_experience mismatch
    # If total career months sum to much more than years_of_experience,
    # or if years_of_experience > (current_year - earliest education start),
    # the profile may be fabricated.
    # -------------------------------------------------------------------------
    yoe = profile.get("years_of_experience", 0)
    total_career_months = sum(job.get("duration_months", 0) for job in career)
    total_career_years = total_career_months / 12.0

    # Career months should roughly align with years_of_experience
    if total_career_years > 0 and abs(total_career_years - yoe) > MAX_CAREER_EXPERIENCE_GAP:
        score += 1.0
        flags.append(
            f"Career total={total_career_years:.1f}y vs stated experience={yoe}y "
            f"(gap={abs(total_career_years - yoe):.1f}y)"
        )

    # Experience vs education timeline
    if education:
        earliest_edu_start = min(ed.get("start_year", 2030) for ed in education)
        # Reference year for the dataset
        reference_year = 2026
        max_possible_years = reference_year - earliest_edu_start
        if yoe > max_possible_years + 2:  # small tolerance
            score += 2.5
            flags.append(
                f"Claims {yoe}y experience but education started in {earliest_edu_start} "
                f"(max possible ~{max_possible_years}y)"
            )

    # -------------------------------------------------------------------------
    # Check 5: Title-skill extreme mismatch
    # A non-tech title (score=0) with 10+ AI skills is a keyword stuffer.
    # -------------------------------------------------------------------------
    title = profile.get("current_title", "")
    title_score = TITLE_SCORES.get(title, 0.15)

    ai_skill_count = sum(
        1 for sk in skills
        if sk.get("name", "").lower() in AI_RELEVANT_SKILLS
    )

    if title_score <= 0.02 and ai_skill_count >= 7:
        score += 3.0
        flags.append(
            f"Non-tech title '{title}' but {ai_skill_count} AI-relevant skills (keyword stuffer)"
        )

    # -------------------------------------------------------------------------
    # Check 6: Impossible company tenure
    # e.g., 8 years at a company that was founded 3 years ago.
    # We can't check real founding dates, but we can check if duration_months
    # at a single company exceeds years_of_experience converted to months by
    # a large margin.
    # -------------------------------------------------------------------------
    for job in career:
        job_duration = job.get("duration_months", 0)
        if job_duration > (yoe * 12) + 24:  # tolerance of 2 years
            score += 2.0
            flags.append(
                f"Job at '{job.get('company','')}' duration={job_duration} months "
                f"but total experience={yoe}y ({yoe*12} months)"
            )

    # -------------------------------------------------------------------------
    # Decision: Is this a honeypot?
    # Score >= 4.0 → likely honeypot
    # Score >= 2.5 → suspicious (will be heavily penalized)
    # -------------------------------------------------------------------------
    is_honeypot = score >= 4.0

    return is_honeypot, flags


def get_honeypot_penalty(candidate: dict) -> float:
    """Returns a multiplier (0.01 to 1.0) based on honeypot suspicion.

    1.0 = clean candidate
    0.01 = confirmed honeypot
    """
    is_honeypot, _ = detect_honeypot(candidate)
    if is_honeypot:
        return 0.01
    return 1.0
