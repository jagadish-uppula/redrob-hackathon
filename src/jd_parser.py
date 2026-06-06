"""
JD Parser — Converts any job description into structured requirements.

Supports two modes:
1. Hardcoded: build_senior_ai_engineer_jd() for the hackathon
2. Dynamic: parse_jd_text(text) parses any raw JD text using
   keyword extraction, regex, and category inference.
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class JDRequirements:
    """Structured representation of a job description's requirements.

    This is the interface between the JD and the scoring engine.
    The scoring engine only sees this object — it never reads raw JD text.
    """

    # --- Role identification ---
    role_title: str = ""
    company: str = ""
    employment_type: str = "Full-time"

    # --- Title matching ---
    target_titles: List[str] = field(default_factory=list)
    adjacent_titles: List[str] = field(default_factory=list)
    negative_titles: List[str] = field(default_factory=list)

    # --- Skills ---
    must_have_skills: List[str] = field(default_factory=list)
    nice_to_have_skills: List[str] = field(default_factory=list)
    negative_skill_contexts: List[str] = field(default_factory=list)

    # --- Experience ---
    min_years: float = 0.0
    max_years: float = 50.0
    ideal_years: float = 7.0

    # --- Location ---
    preferred_countries: List[str] = field(default_factory=list)
    preferred_cities: List[str] = field(default_factory=list)
    accepts_remote: bool = False

    # --- Company preferences ---
    negative_companies: List[str] = field(default_factory=list)
    preferred_company_type: str = "product"

    # --- Industry ---
    preferred_industries: List[str] = field(default_factory=list)

    # --- Work mode ---
    preferred_work_mode: str = "hybrid"

    # --- Notice period ---
    ideal_notice_days: int = 30
    max_notice_days: int = 90

    # --- Career keywords ---
    high_value_keywords: List[str] = field(default_factory=list)
    production_keywords: List[str] = field(default_factory=list)

    # --- Role category (for dynamic title scoring) ---
    role_category: str = ""  # e.g., "ai_ml", "data", "software", "devops"


# =========================================================================
# Master Databases for JD Parsing
# =========================================================================

# Comprehensive skill dictionary — used to detect skills in raw JD text
MASTER_SKILLS = {
    # AI/ML Core
    "machine learning", "deep learning", "artificial intelligence",
    "neural networks", "natural language processing", "nlp",
    "computer vision", "reinforcement learning",
    # Embeddings & Retrieval
    "embeddings", "sentence-transformers", "sentence transformers",
    "openai embeddings", "bge", "e5", "word2vec", "glove",
    "vector search", "vector database", "semantic search",
    "information retrieval", "hybrid search", "dense retrieval",
    "embedding drift", "index refresh",
    # Vector DBs
    "pinecone", "weaviate", "qdrant", "milvus", "faiss",
    "elasticsearch", "opensearch", "chromadb",
    # LLM
    "llm", "large language model", "gpt", "bert", "transformer",
    "fine-tuning", "lora", "qlora", "peft", "rag",
    "retrieval augmented generation", "langchain", "llamaindex",
    "prompt engineering", "huggingface",
    # ML Frameworks
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn",
    "xgboost", "lightgbm", "catboost",
    # Languages
    "python", "java", "c++", "rust", "go", "javascript", "typescript",
    "sql", "scala",
    # Data
    "spark", "hadoop", "airflow", "kafka", "dbt",
    "snowflake", "bigquery", "redshift", "databricks",
    # Search/Ranking
    "ranking", "retrieval", "recommendation systems", "search",
    "learning-to-rank", "learning to rank", "bm25", "tf-idf",
    "re-ranking", "candidate generation",
    # Evaluation
    "ndcg", "mrr", "map", "a/b testing", "evaluation",
    "offline evaluation", "online evaluation",
    # Infrastructure
    "docker", "kubernetes", "aws", "gcp", "azure",
    "distributed systems", "microservices", "ci/cd",
    "mlflow", "wandb", "weights & biases",
    # Specific domains
    "hr-tech", "recruiting", "marketplace",
    "speech recognition", "object detection", "image classification",
}

# Cities for location detection
KNOWN_CITIES = {
    "pune", "noida", "hyderabad", "mumbai", "delhi",
    "delhi ncr", "gurgaon", "gurugram", "bengaluru", "bangalore",
    "chennai", "kolkata", "new york", "san francisco", "seattle",
    "london", "berlin", "singapore", "dubai", "toronto",
    "vancouver", "sydney", "melbourne", "austin", "boston",
}

# Countries for location detection
KNOWN_COUNTRIES = {
    "india", "usa", "united states", "uk", "united kingdom",
    "canada", "australia", "germany", "singapore", "uae",
    "france", "japan", "ireland",
}

# Consulting companies — referenced as negatives in JDs
KNOWN_CONSULTING = {
    "tcs", "tata consultancy", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "tech mahindra", "deloitte",
}

# Non-tech titles — always negative
NON_TECH_TITLES = [
    "HR Manager", "Accountant", "Marketing Manager",
    "Operations Manager", "Sales Executive", "Content Writer",
    "Graphic Designer", "Civil Engineer", "Mechanical Engineer",
    "Customer Support", "Business Analyst", "Project Manager",
]

# =========================================================================
# Role Category Definitions — for dynamic title scoring
# =========================================================================

# Maps role category → (target titles, adjacent titles)
ROLE_CATEGORY_TITLES = {
    "ai_ml": {
        "target": [
            "Senior AI Engineer", "AI Engineer", "Lead AI Engineer",
            "ML Engineer", "Machine Learning Engineer",
            "Applied ML Engineer", "Senior Machine Learning Engineer",
            "Staff Machine Learning Engineer", "Junior ML Engineer",
            "AI Research Engineer", "AI Specialist",
        ],
        "adjacent": [
            "NLP Engineer", "Senior NLP Engineer",
            "Recommendation Systems Engineer", "Search Engineer",
            "Senior Software Engineer (ML)",
            "Data Scientist", "Senior Data Scientist",
            "Senior Applied Scientist", "Computer Vision Engineer",
            "Data Engineer", "Senior Data Engineer",
            "Backend Engineer",
        ],
    },
    "data_engineering": {
        "target": [
            "Data Engineer", "Senior Data Engineer",
            "Analytics Engineer", "Data Analyst",
        ],
        "adjacent": [
            "Backend Engineer", "Software Engineer",
            "Senior Software Engineer", "Data Scientist",
            "Senior Data Scientist", "ML Engineer",
            "DevOps Engineer", "Cloud Engineer",
        ],
    },
    "software": {
        "target": [
            "Software Engineer", "Senior Software Engineer",
            "Backend Engineer", "Full Stack Developer",
            "Java Developer", ".NET Developer",
        ],
        "adjacent": [
            "Frontend Engineer", "Mobile Developer",
            "DevOps Engineer", "Cloud Engineer",
            "QA Engineer", "Data Engineer",
        ],
    },
    "devops_cloud": {
        "target": [
            "DevOps Engineer", "Cloud Engineer",
        ],
        "adjacent": [
            "Software Engineer", "Senior Software Engineer",
            "Backend Engineer", "Data Engineer",
        ],
    },
    "nlp_search": {
        "target": [
            "NLP Engineer", "Senior NLP Engineer",
            "Search Engineer", "Recommendation Systems Engineer",
        ],
        "adjacent": [
            "ML Engineer", "Machine Learning Engineer",
            "AI Engineer", "Senior AI Engineer",
            "Data Scientist", "Backend Engineer",
            "Senior Software Engineer (ML)",
        ],
    },
    "data_science": {
        "target": [
            "Data Scientist", "Senior Data Scientist",
            "Senior Applied Scientist",
        ],
        "adjacent": [
            "ML Engineer", "Machine Learning Engineer",
            "AI Engineer", "Data Analyst", "Analytics Engineer",
            "Data Engineer", "Senior Data Engineer",
        ],
    },
}

# Category detection keywords — found in JD text
CATEGORY_KEYWORDS = {
    "ai_ml": ["ai engineer", "ml engineer", "machine learning", "artificial intelligence",
              "deep learning", "neural network", "embeddings", "ranking", "retrieval"],
    "data_engineering": ["data engineer", "data pipeline", "etl", "warehouse",
                         "spark", "airflow", "data infrastructure"],
    "software": ["software engineer", "backend", "full stack", "web development",
                 "api", "microservices", "system design"],
    "devops_cloud": ["devops", "cloud engineer", "infrastructure", "ci/cd",
                     "kubernetes", "terraform", "aws", "gcp"],
    "nlp_search": ["nlp", "search engineer", "information retrieval",
                   "natural language", "text mining", "search infrastructure"],
    "data_science": ["data scientist", "statistical", "analytics", "predictive",
                     "hypothesis testing", "experiment"],
}


# =========================================================================
# Dynamic JD Text Parser
# =========================================================================

def parse_jd_text(text: str) -> JDRequirements:
    """Parse raw JD text into structured requirements using keyword extraction.

    This enables the ranking system to work with ANY job description,
    not just the hardcoded hackathon JD. Uses regex, keyword matching,
    and category inference — no ML models required.

    Args:
        text: Raw JD text (from a .txt file, pasted text, etc.)

    Returns:
        JDRequirements object with extracted requirements.
    """
    text_lower = text.lower()

    # 1. Extract role title
    role_title = _extract_role_title(text)

    # 2. Detect role category
    role_category = _detect_role_category(text_lower)

    # 3. Extract experience range
    min_years, max_years, ideal_years = _extract_experience(text_lower)

    # 4. Extract skills from JD text
    must_have, nice_to_have = _extract_skills(text, text_lower)

    # 5. Extract location preferences
    countries, cities = _extract_locations(text_lower)

    # 6. Extract negative companies
    neg_companies = _extract_negative_companies(text_lower)

    # 7. Infer title tiers from role category
    target_titles, adjacent_titles = _infer_titles(role_category)

    # 8. Detect work mode
    work_mode = _extract_work_mode(text_lower)

    # 9. Extract career keywords from JD
    high_value_kw, production_kw = _extract_career_keywords(text_lower)

    return JDRequirements(
        role_title=role_title,
        role_category=role_category,
        target_titles=target_titles,
        adjacent_titles=adjacent_titles,
        negative_titles=NON_TECH_TITLES,
        must_have_skills=must_have,
        nice_to_have_skills=nice_to_have,
        min_years=min_years,
        max_years=max_years,
        ideal_years=ideal_years,
        preferred_countries=countries,
        preferred_cities=cities,
        accepts_remote="remote" in text_lower,
        negative_companies=neg_companies,
        preferred_company_type="product",
        preferred_work_mode=work_mode,
        ideal_notice_days=30,
        max_notice_days=90,
        high_value_keywords=high_value_kw,
        production_keywords=production_kw,
    )


def _extract_role_title(text: str) -> str:
    """Extract the job title from the first few lines of the JD."""
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if not line:
            continue
        # Look for patterns like "Job Title: X" or "Role: X"
        m = re.match(
            r"(?:job\s+(?:title|description)|role|position)\s*[:—–-]\s*(.+)",
            line, re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
        # Check if first non-empty line looks like a title
        # (contains "Engineer", "Developer", "Scientist", etc.)
        title_words = ["engineer", "developer", "scientist", "architect",
                        "analyst", "manager", "designer", "lead", "staff"]
        if any(tw in line.lower() for tw in title_words) and len(line) < 120:
            return line.strip()
    return lines[0].strip() if lines else "Unknown Role"


def _detect_role_category(text_lower: str) -> str:
    """Detect the primary role category from JD text."""
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[category] = score

    if not scores:
        return "software"  # Default

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "software"


def _extract_experience(text_lower: str) -> Tuple[float, float, float]:
    """Extract experience range from JD text using regex."""
    # Pattern: "5-9 years", "5–9 years", "5 to 9 years"
    m = re.search(r"(\d+)\s*[-–to]+\s*(\d+)\s*years?", text_lower)
    if m:
        min_y = float(m.group(1))
        max_y = float(m.group(2))
        ideal_y = (min_y + max_y) / 2
        return min_y, max_y, ideal_y

    # Pattern: "5+ years"
    m = re.search(r"(\d+)\+?\s*years?", text_lower)
    if m:
        min_y = float(m.group(1))
        return min_y, min_y + 5, min_y + 2.5

    return 3.0, 12.0, 7.0  # Defaults


def _extract_skills(text: str, text_lower: str) -> Tuple[List[str], List[str]]:
    """Extract must-have and nice-to-have skills from JD text."""
    detected = []
    for skill in MASTER_SKILLS:
        if skill in text_lower:
            detected.append(skill)

    # Heuristic: skills mentioned in "required" sections → must-have
    # Skills mentioned in "nice to have" / "preferred" → nice-to-have
    must_have = []
    nice_to_have = []

    # Split text into sections
    sections = re.split(
        r"(?:things you.*?need|must.?have|required|requirements|absolutely need)",
        text_lower, flags=re.IGNORECASE,
    )
    nice_sections = re.split(
        r"(?:nice.?to.?have|preferred|bonus|we.?d like|optional)",
        text_lower, flags=re.IGNORECASE,
    )

    # If we found sections, classify skills
    required_text = sections[1] if len(sections) > 1 else ""
    optional_text = nice_sections[1] if len(nice_sections) > 1 else ""

    for skill in detected:
        if skill in required_text:
            must_have.append(skill)
        elif skill in optional_text:
            nice_to_have.append(skill)
        else:
            # Default: first mention in JD → must_have if < 10, else nice_to_have
            if len(must_have) < 15:
                must_have.append(skill)
            else:
                nice_to_have.append(skill)

    return must_have, nice_to_have


def _extract_locations(text_lower: str) -> Tuple[List[str], List[str]]:
    """Extract preferred countries and cities from JD text."""
    countries = []
    for c in KNOWN_COUNTRIES:
        if c in text_lower:
            # Map to standard name
            mapping = {
                "united states": "USA", "usa": "USA",
                "united kingdom": "UK", "uk": "UK",
                "india": "India", "canada": "Canada",
                "australia": "Australia", "germany": "Germany",
                "singapore": "Singapore", "uae": "UAE",
                "france": "France", "japan": "Japan",
                "ireland": "Ireland",
            }
            countries.append(mapping.get(c, c.title()))

    cities = []
    for c in KNOWN_CITIES:
        if c in text_lower:
            cities.append(c.title())

    # Deduplicate
    countries = list(dict.fromkeys(countries))
    cities = list(dict.fromkeys(cities))

    return countries or ["India"], cities


def _extract_negative_companies(text_lower: str) -> List[str]:
    """Detect consulting companies mentioned negatively in the JD."""
    found = []
    for company in KNOWN_CONSULTING:
        if company in text_lower:
            found.append(company.title())
    return found


def _infer_titles(role_category: str) -> Tuple[List[str], List[str]]:
    """Get target and adjacent titles based on detected role category."""
    cat_data = ROLE_CATEGORY_TITLES.get(role_category, {})
    target = cat_data.get("target", [])
    adjacent = cat_data.get("adjacent", [])
    return target, adjacent


def _extract_work_mode(text_lower: str) -> str:
    """Detect preferred work mode from JD text."""
    if "remote" in text_lower and "hybrid" not in text_lower:
        return "remote"
    if "hybrid" in text_lower:
        return "hybrid"
    if "on-site" in text_lower or "onsite" in text_lower or "in-office" in text_lower:
        return "onsite"
    return "hybrid"  # Default


def _extract_career_keywords(text_lower: str) -> Tuple[List[str], List[str]]:
    """Extract high-value and production keywords from JD text."""
    high_value = []
    production = []

    hv_candidates = [
        "retrieval", "search", "ranking", "recommendation",
        "embeddings", "vector", "similarity", "information retrieval",
        "semantic search", "hybrid search", "nlp", "natural language",
        "machine learning", "deep learning", "fine-tuning",
        "data pipeline", "etl", "warehouse",
    ]
    prod_candidates = [
        "production", "deployed", "shipped", "real users",
        "a/b test", "scaled", "live", "monitoring", "latency",
    ]

    for kw in hv_candidates:
        if kw in text_lower:
            high_value.append(kw)
    for kw in prod_candidates:
        if kw in text_lower:
            production.append(kw)

    return high_value, production


# =========================================================================
# Dynamic Title Scoring
# =========================================================================

def compute_dynamic_title_score(
    candidate_title: str,
    jd_req: JDRequirements,
) -> float:
    """Compute title relevance score dynamically based on JDRequirements.

    Returns a score between 0.0 and 1.0.
    """
    if candidate_title in jd_req.target_titles:
        return 1.0

    if candidate_title in jd_req.adjacent_titles:
        return 0.65

    if candidate_title in jd_req.negative_titles:
        return 0.0

    # Fallback: keyword overlap between candidate title and role title
    role_words = set(jd_req.role_title.lower().split())
    title_words = set(candidate_title.lower().split())

    # Remove common words
    stopwords = {"senior", "junior", "lead", "staff", "principal", "the", "a", "an", "—", "-"}
    role_words -= stopwords
    title_words -= stopwords

    if not role_words:
        return 0.15

    overlap = len(role_words & title_words)
    score = overlap / max(len(role_words), 1)
    return min(max(score * 0.7, 0.05), 0.5)


# =========================================================================
# Hardcoded Hackathon JD
# =========================================================================

def build_senior_ai_engineer_jd() -> JDRequirements:
    """Builds the JDRequirements for the Redrob hackathon JD:
    'Senior AI Engineer — Founding Team'

    This is derived from careful reading of the full job_description.docx.
    """
    return JDRequirements(
        role_title="Senior AI Engineer — Founding Team",
        company="Redrob AI",
        employment_type="Full-time",
        role_category="ai_ml",

        target_titles=[
            "Senior AI Engineer", "AI Engineer", "Lead AI Engineer",
            "ML Engineer", "Machine Learning Engineer",
            "Applied ML Engineer", "Senior Machine Learning Engineer",
            "Staff Machine Learning Engineer",
        ],
        adjacent_titles=[
            "AI Research Engineer", "AI Specialist",
            "NLP Engineer", "Senior NLP Engineer",
            "Recommendation Systems Engineer", "Search Engineer",
            "Senior Software Engineer (ML)",
            "Data Scientist", "Senior Data Scientist",
            "Senior Applied Scientist",
            "Data Engineer", "Senior Data Engineer",
            "Backend Engineer",
        ],
        negative_titles=[
            "HR Manager", "Accountant", "Marketing Manager",
            "Operations Manager", "Sales Executive", "Content Writer",
            "Graphic Designer", "Civil Engineer", "Mechanical Engineer",
            "Customer Support",
        ],

        must_have_skills=[
            "embeddings", "sentence-transformers", "retrieval", "ranking",
            "vector database", "pinecone", "weaviate", "qdrant", "milvus",
            "faiss", "elasticsearch", "opensearch",
            "python",
            "ndcg", "mrr", "evaluation",
            "nlp", "natural language processing",
        ],
        nice_to_have_skills=[
            "lora", "qlora", "peft", "fine-tuning",
            "xgboost", "learning-to-rank",
            "hr-tech", "recruiting",
            "distributed systems",
            "pytorch", "tensorflow", "transformers",
            "rag", "langchain",
        ],
        negative_skill_contexts=[
            "computer vision only",
            "speech only",
            "robotics only",
        ],

        min_years=4.0,
        max_years=12.0,
        ideal_years=7.0,

        preferred_countries=["India"],
        preferred_cities=[
            "Pune", "Noida", "Hyderabad", "Mumbai",
            "Delhi", "Delhi NCR", "Gurgaon", "Bengaluru", "Bangalore",
        ],
        accepts_remote=False,

        negative_companies=[
            "TCS", "Infosys", "Wipro", "Accenture",
            "Cognizant", "Capgemini",
        ],
        preferred_company_type="product",

        preferred_industries=["Software", "AI/ML", "Technology"],

        preferred_work_mode="hybrid",
        ideal_notice_days=30,
        max_notice_days=90,

        high_value_keywords=[
            "retrieval", "search", "ranking", "recommendation",
            "embeddings", "vector", "similarity", "information retrieval",
            "semantic search", "hybrid search", "embedding drift",
            "index refresh", "retrieval quality",
        ],
        production_keywords=[
            "production", "deployed", "shipped", "real users",
            "a/b test", "scaled", "live", "monitoring",
        ],
    )
