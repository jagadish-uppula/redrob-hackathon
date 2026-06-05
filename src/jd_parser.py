"""
JD Parser — Converts a job description into structured requirements.

For the hackathon, the JD is hardcoded. But the architecture supports
parsing any JD text into a JDRequirements object, making the ranking
system generalizable to arbitrary job descriptions.
"""

from dataclasses import dataclass, field
from typing import List


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


def build_senior_ai_engineer_jd() -> JDRequirements:
    """Builds the JDRequirements for the Redrob hackathon JD:
    'Senior AI Engineer — Founding Team'

    This is derived from careful reading of the full job_description.docx.
    """
    return JDRequirements(
        role_title="Senior AI Engineer — Founding Team",
        company="Redrob AI",
        employment_type="Full-time",

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
            "semantic search", "hybrid search",
        ],
        production_keywords=[
            "production", "deployed", "shipped", "real users",
            "a/b test", "scaled", "live",
        ],
    )
