"""
State schema for the RFP Analysis LangGraph workflow.
This defines the data that flows between agents.
"""
from typing import TypedDict, List, Optional, Annotated
from operator import add


class RFPSection(TypedDict):
    """Parsed section from the RFP document."""
    name: str
    content: str
    page_number: Optional[int]


class Requirement(TypedDict):
    """Extracted requirement from the RFP."""
    id: str
    description: str
    category: str  # technical, commercial, compliance, delivery
    priority: str  # mandatory, preferred, optional
    specifications: dict  # extracted specs like voltage, conductor, etc.


class ComponentMatch(TypedDict):
    """A matched component from the database."""
    component_id: int
    sku: str
    name: str
    category: str
    score: float  # 0-100 match score
    matched_specs: dict  # which specs matched
    price_per_meter: float
    in_stock: bool
    lead_time_days: int


class RequirementMatch(TypedDict):
    """A requirement with its matched components."""
    requirement_id: str
    requirement_description: str
    matches: List[ComponentMatch]
    best_match: Optional[ComponentMatch]
    coverage_score: float  # how well requirements are covered


class RFPState(TypedDict):
    """
    Main state object that flows through the LangGraph workflow.
    Each agent reads from and writes to this state.
    """
    # Input
    rfp_id: str
    rfp_text: str

    # Parser Agent output
    sections: List[RFPSection]

    # Analyzer Agent output
    requirements: List[Requirement]
    project_summary: str
    budget_info: Optional[str]
    timeline_info: Optional[str]

    # Matcher Agent output
    requirement_matches: List[RequirementMatch]

    # Scorer Agent output
    overall_score: float
    scoring_breakdown: dict
    recommendations: List[str]

    # Response Builder output
    proposal_summary: str
    technical_response: str
    commercial_response: str

    # Metadata
    errors: Annotated[List[str], add]  # Accumulates errors from all agents
    current_agent: str
