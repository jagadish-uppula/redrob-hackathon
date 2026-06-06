"""
Configuration module — all weights, thresholds, and keyword dictionaries.

This is the single source of truth for tuning the ranking system.
Changing these values lets you adapt the ranker to different JDs without
touching the scoring logic.
"""

# =============================================================================
# Scoring Weights (must sum to 1.0)
# =============================================================================
SCORING_WEIGHTS = {
    "title_match":       0.28,   # Title is the strongest anti-trap signal
    "career_relevance":  0.24,   # Career history > skill keywords
    "skills_match":      0.12,   # Skills matter but are trap-prone
    "experience_fit":    0.08,   # Years of experience band
    "education":         0.05,   # Education tier + field relevance
    "location":          0.05,   # Geographic fit
    "behavioral":        0.18,   # Availability and engagement signals
}

# =============================================================================
# Multiplicative Penalties (applied after base score)
# =============================================================================
HONEYPOT_PENALTY        = 0.01   # Effectively kill honeypot candidates
CONSULTING_ONLY_PENALTY = 0.25   # Career entirely at consulting/services firms
TITLE_CHASER_PENALTY    = 0.70   # Average tenure < 18 months across 3+ jobs
CV_ONLY_PENALTY         = 0.50   # Computer vision only, no NLP/IR exposure
RESEARCH_ONLY_PENALTY   = 0.40   # Pure research, no production deployment

# =============================================================================
# Title Scoring Tiers
# Maps current_title → base relevance score for a Senior AI Engineer role.
# This is the primary defense against keyword-stuffer traps.
# =============================================================================
TITLE_SCORES = {
    # Tier 1: Direct match (1.0)
    "Senior AI Engineer":               1.00,
    "AI Engineer":                      1.00,
    "Lead AI Engineer":                 1.00,

    # Tier 2: Very close (0.95)
    "ML Engineer":                      0.95,
    "Machine Learning Engineer":        0.95,
    "Applied ML Engineer":              0.95,
    "Senior Machine Learning Engineer": 0.95,
    "Staff Machine Learning Engineer":  0.95,

    # Tier 3: Strong adjacent (0.85)
    "AI Research Engineer":             0.82,  # Slightly lower — JD warns about pure research
    "AI Specialist":                    0.82,
    "Senior NLP Engineer":              0.85,
    "NLP Engineer":                     0.85,
    "Recommendation Systems Engineer":  0.88,
    "Search Engineer":                  0.88,
    "Senior Software Engineer (ML)":    0.85,

    # Tier 4: Relevant (0.70)
    "Data Scientist":                   0.72,
    "Senior Data Scientist":            0.72,
    "Senior Applied Scientist":         0.72,
    "Computer Vision Engineer":         0.60,  # JD warns about CV-only
    "Junior ML Engineer":               0.78,  # ML but junior flag

    # Tier 5: Adjacent (0.50–0.55)
    "Data Engineer":                    0.52,
    "Senior Data Engineer":             0.55,
    "Analytics Engineer":               0.45,
    "Data Analyst":                     0.40,
    "Backend Engineer":                 0.50,

    # Tier 6: General tech (0.30–0.40)
    "Software Engineer":                0.35,
    "Senior Software Engineer":         0.40,
    "Full Stack Developer":             0.25,
    "DevOps Engineer":                  0.20,
    "Cloud Engineer":                   0.22,
    "Java Developer":                   0.18,

    # Tier 7: Marginal tech (0.10–0.15)
    "Frontend Engineer":                0.12,
    ".NET Developer":                   0.10,
    "Mobile Developer":                 0.10,
    "QA Engineer":                      0.08,

    # Tier 8: Non-tech roles — THE TRAPS (0.0)
    "Business Analyst":                 0.02,
    "HR Manager":                       0.00,
    "Mechanical Engineer":              0.00,
    "Accountant":                       0.00,
    "Project Manager":                  0.02,
    "Customer Support":                 0.00,
    "Operations Manager":               0.00,
    "Content Writer":                   0.00,
    "Sales Executive":                  0.00,
    "Civil Engineer":                   0.00,
    "Graphic Designer":                 0.00,
    "Marketing Manager":                0.00,
}

# Default score for titles not in the map
DEFAULT_TITLE_SCORE = 0.15

# =============================================================================
# Career Description Keywords — weighted by relevance to JD
# =============================================================================

# High-value: retrieval, search, ranking, recommendation systems
CAREER_KEYWORDS_TIER1 = {
    "retrieval": 3.0,
    "search engine": 3.0,
    "ranking system": 3.0,
    "recommendation system": 3.0,
    "recommendation engine": 3.0,
    "re-ranking": 3.0,
    "reranking": 3.0,
    "candidate generation": 2.5,
    "embeddings": 2.8,
    "vector search": 3.0,
    "vector database": 3.0,
    "semantic search": 3.0,
    "hybrid search": 3.0,
    "hybrid retrieval": 3.0,
    "dense retrieval": 2.5,
    "faiss": 2.5,
    "elasticsearch": 2.0,
    "opensearch": 2.0,
    "pinecone": 2.5,
    "weaviate": 2.5,
    "qdrant": 2.5,
    "milvus": 2.5,
    "similarity search": 2.5,
    "information retrieval": 2.5,
    "bm25": 2.0,
    "tf-idf": 1.5,
    "ndcg": 2.5,
    "mrr": 2.0,
    "mean average precision": 2.0,
    # JD-specific: operational production signals for retrieval systems
    "embedding drift": 3.5,
    "index refresh": 3.0,
    "retrieval quality": 3.0,
    "retrieval-quality regression": 3.5,
    "candidate-jd matching": 3.0,
    "recruiter engagement": 2.5,
    "talent intelligence": 2.5,
    "talent matching": 2.5,
}

# Medium-value: general ML/NLP production
CAREER_KEYWORDS_TIER2 = {
    "machine learning": 1.8,
    "deep learning": 1.8,
    "nlp": 2.0,
    "natural language": 2.0,
    "language model": 2.0,
    "transformer": 1.8,
    "bert": 1.5,
    "fine-tuning": 1.5,
    "fine tuning": 1.5,
    "model training": 1.5,
    "model serving": 2.0,
    "model deployment": 2.0,
    "inference": 1.5,
    "feature engineering": 1.2,
    "classification": 1.0,
    "neural network": 1.5,
    "xgboost": 1.2,
    "learning to rank": 2.5,
    "learning-to-rank": 2.5,
}

# Production/deployment signals — the "shipper" archetype the JD wants
# JD explicitly says: "we'd rather you tilt slightly toward shipper than toward researcher"
CAREER_KEYWORDS_PRODUCTION = {
    "production": 1.5,
    "deployed": 1.5,
    "shipped": 2.0,       # JD uses "shipped" repeatedly
    "real users": 2.0,
    "live system": 1.5,
    "a/b test": 2.5,       # JD explicitly requires A/B testing experience
    "ab test": 2.0,
    "a/b testing": 2.5,
    "scaled": 1.2,
    "latency": 1.0,
    "throughput": 1.0,
    "sla": 0.8,
    "monitoring": 1.0,
    "real-time": 1.0,
    "end-to-end": 1.2,
    # Shipper-specific signals
    "working but not great": 1.5,  # Iterative improvement mindset
    "offline benchmark": 2.5,
    "online evaluation": 2.5,
    "feedback loop": 2.0,
    "recruiter-feedback": 2.5,
    "recruiter feedback": 2.5,
    "user feedback": 1.5,
    "iterated": 1.0,
    "improved metrics": 1.5,
    "engagement metrics": 2.0,
    "meaningful scale": 2.0,
}

# Data engineering (moderate relevance)
CAREER_KEYWORDS_DATA = {
    "data pipeline": 1.0,
    "pipeline": 0.6,
    "etl": 0.8,
    "spark": 0.8,
    "airflow": 0.7,
    "kafka": 0.6,
    "streaming": 0.6,
    "batch processing": 0.5,
    "warehouse": 0.5,
    "dbt": 0.5,
    "snowflake": 0.5,
    "bigquery": 0.5,
}

# =============================================================================
# Skills — Must-Have and Nice-to-Have for this JD
# =============================================================================

# Skills that the JD explicitly requires
MUST_HAVE_SKILLS = {
    # Embeddings/retrieval
    "sentence-transformers", "sentence transformers", "embeddings",
    "openai embeddings", "bge", "e5",
    # Vector databases
    "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
    "elasticsearch", "faiss", "vector database",
    # Core
    "python",
    # Evaluation
    "ndcg", "mrr", "map", "evaluation",
    # Search/retrieval/ranking
    "retrieval", "ranking", "search", "information retrieval",
    "nlp", "natural language processing",
}

# Skills the JD lists as nice-to-have
NICE_TO_HAVE_SKILLS = {
    "lora", "qlora", "peft", "fine-tuning llms", "fine tuning",
    "xgboost", "learning-to-rank", "learning to rank", "lambdamart",
    "hr-tech", "recruiting", "marketplace",
    "distributed systems", "kubernetes", "docker",
    "open-source", "github",
    "pytorch", "tensorflow", "huggingface", "transformers",
    "bert", "gpt", "llm", "large language model",
    "rag", "retrieval augmented generation",
    "langchain", "llamaindex",
    "deep learning", "machine learning",
    "spark", "airflow", "kafka",
    "aws", "gcp", "azure",
}

# Skills that are AI/ML-relevant (for counting purposes)
AI_RELEVANT_SKILLS = {
    "nlp", "natural language processing",
    "machine learning", "deep learning",
    "pytorch", "tensorflow", "keras",
    "transformers", "huggingface",
    "bert", "gpt", "llm",
    "fine-tuning llms", "lora", "qlora", "peft",
    "rag", "retrieval augmented generation",
    "embeddings", "sentence-transformers",
    "faiss", "pinecone", "weaviate", "milvus", "qdrant",
    "xgboost", "lightgbm", "catboost",
    "feature engineering", "statistical modeling",
    "image classification", "object detection", "computer vision",
    "speech recognition", "tts",
    "gans", "reinforcement learning",
    "recommendation systems",
    "langchain", "llamaindex",
    "weights & biases", "mlflow", "bentoml",
    "data science", "data analysis",
    "scikit-learn", "sklearn",
    "neural network", "cnn", "rnn", "lstm",
    "a/b testing",
}

# =============================================================================
# Consulting / Services Companies (disqualifier if career-only)
# =============================================================================
CONSULTING_COMPANIES = {
    "tcs", "tata consultancy services", "tata consultancy",
    "infosys",
    "wipro",
    "accenture",
    "cognizant", "cognizant technology solutions",
    "capgemini",
    "hcl technologies", "hcl",
    "tech mahindra",
    "ltimindtree", "mindtree", "l&t infotech",
    "mphasis",
    "hexaware",
    "zensar",
    "persistent systems",
    "niit technologies",
    "cyient",
    "birlasoft",
    "coforge",
    "mastek",
    "sonata software",
}

# IT Services industry flag — combined with large company size → likely consulting
IT_SERVICES_INDUSTRY = "IT Services"

# =============================================================================
# Experience Configuration
# =============================================================================
IDEAL_EXPERIENCE_YEARS = 7.0     # Center of the Gaussian
EXPERIENCE_SIGMA       = 2.5     # Standard deviation
MIN_RELEVANT_YEARS     = 3.0     # Below this, very low score
MAX_RELEVANT_YEARS     = 15.0    # Above this, diminishing returns

# =============================================================================
# Location Configuration
# =============================================================================
PREFERRED_COUNTRY = "India"
PREFERRED_CITIES = {
    "pune", "noida", "hyderabad", "mumbai", "delhi",
    "delhi ncr", "gurgaon", "gurugram", "bengaluru", "bangalore",
    "chennai", "kolkata",
}
TIER1_CITIES = {"pune", "noida"}  # Highest preference from JD

# =============================================================================
# Education Configuration
# =============================================================================
EDUCATION_TIER_SCORES = {
    "tier_1": 1.0,
    "tier_2": 0.7,
    "tier_3": 0.4,
    "tier_4": 0.2,
    "unknown": 0.2,
}

RELEVANT_FIELDS = {
    "computer science", "cs", "artificial intelligence", "ai",
    "machine learning", "data science", "information technology",
    "it", "software engineering", "electronics",
    "electrical engineering", "mathematics", "statistics",
    "computational linguistics",
}

# =============================================================================
# Behavioral Signal Thresholds
# =============================================================================
ACTIVITY_DECAY_DAYS     = 180    # Inactive > 6 months → heavy penalty
IDEAL_NOTICE_DAYS       = 30     # JD prefers sub-30
MAX_ACCEPTABLE_NOTICE   = 90     # Beyond this, increasing penalty
MIN_RESPONSE_RATE       = 0.10   # Below 10% → practically unavailable
IDEAL_RESPONSE_RATE     = 0.60   # Above this → great
MIN_PROFILE_COMPLETE    = 50.0   # Below 50% → low-quality signal

# =============================================================================
# Honeypot Detection Thresholds
# =============================================================================
MAX_EXPERT_SKILLS           = 8    # Having 8+ expert skills is suspicious
EXPERT_MIN_DURATION_MONTHS  = 6    # Expert skill with < 6 months → red flag
SKILL_ASSESSMENT_MIN        = 25   # Expert proficiency but assessment < 25 → flag
MAX_CAREER_EXPERIENCE_GAP   = 5    # years_of_experience vs sum(career durations) gap
