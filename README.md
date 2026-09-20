# B2B RFP Automation System

An AI-powered RFP (Request for Proposal) automation system for the electrical/cable components industry. The system uses a multi-agent pipeline to analyze RFP documents, extract requirements, match them with products from a catalog, and generate professional proposals.

## Features

- **Document Upload & Extraction** - Upload PDF/DOCX RFP documents and extract text
- **AI Agent Pipeline** - 5-stage analysis pipeline (Parser → Analyzer → Matcher → Scorer → Response)
- **Component Matching** - Automatically match RFP requirements to product catalog
- **Proposal Generation** - Generate technical and commercial proposal responses

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python) |
| Database | PostgreSQL + SQLAlchemy ORM |
| AI/LLM | OpenRouter API (supports multiple models) |
| Default Model | x-ai/grok-4.1-fast:free |
| Workflow | LangGraph (StateGraph) |
| Document Processing | pdfplumber, python-docx |
| Frontend | HTML, CSS, JavaScript |

## Project Structure

```
B2B-RFP/
├── app/
│   ├── agents/              # AI Agent Pipeline
│   │   ├── graph.py         # LangGraph workflow orchestration
│   │   ├── state.py         # Pipeline state definitions
│   │   ├── llm.py           # OpenRouter LLM configuration
│   │   ├── logger.py        # Terminal logging utilities (colored output)
│   │   ├── json_utils.py    # Robust JSON extraction from LLM responses
│   │   ├── parser_agent.py  # Extracts sections from RFP
│   │   ├── analyzer_agent.py # Extracts requirements & specs
│   │   ├── matcher_agent.py # Matches requirements to products
│   │   ├── scorer_agent.py  # Scores match coverage
│   │   └── response_agent.py # Generates proposal
│   ├── db/
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── base.py          # Database engine & session
│   │   └── crud.py          # Database operations
│   ├── services/
│   │   └── extractor.py     # PDF/DOCX text extraction
│   ├── v1/
│   │   └── routes.py        # API endpoints
│   ├── config.py            # App configuration
│   └── main.py              # FastAPI application
├── static/
│   ├── dashboard.html       # Main dashboard page
│   ├── css/
│   │   └── dashboard.css    # Dashboard styles
│   └── js/
│       └── dashboard.js     # Dashboard functionality
├── scripts/
│   └── seed_enhanced_data.py # Seeds database with components & tests
├── data/
│   ├── components_enhanced.csv # Product catalog (100+ cables/wires)
│   └── tests.csv              # Test procedures & pricing
├── uploads/                 # Uploaded RFP files
├── requirements.txt
├── .env                     # Environment variables
└── .env.example             # Example environment configuration
```

---

## Detailed Application Flow

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                         (static/dashboard.html)                              │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FASTAPI BACKEND                                   │
│                            (app/main.py)                                     │
│                                  │                                           │
│    ┌─────────────────────────────┼─────────────────────────────────────┐    │
│    │                    API ROUTES (app/v1/routes.py)                   │    │
│    │  POST /upload → POST /extract → POST /analyze/sync                 │    │
│    └─────────────────────────────┼─────────────────────────────────────┘    │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────────────────┐
        │                          │                                       │
        ▼                          ▼                                       ▼
┌───────────────┐    ┌─────────────────────────────┐    ┌─────────────────────┐
│   EXTRACTOR   │    │      LANGGRAPH PIPELINE     │    │      DATABASE       │
│   SERVICE     │    │     (app/agents/graph.py)   │    │     PostgreSQL      │
│               │    │                             │    │                     │
│ PDF → Text    │    │  Parser → Analyzer →        │    │ RFPs, OEMProducts,  │
│ DOCX → Text   │    │  Matcher → Scorer →         │    │ Pricing, Matches    │
│               │    │  Response                   │    │                     │
└───────────────┘    └─────────────────────────────┘    └─────────────────────┘
                                   │
                                   ▼
                     ┌─────────────────────────────┐
                     │      OPENROUTER API         │
                     │   (x-ai/grok-4.1-fast:free) │
                     └─────────────────────────────┘
```

---

### Step-by-Step Flow

#### 1. Application Startup (`app/main.py`)

```
User starts server → uvicorn app.main:app --reload
                            │
                            ▼
                    FastAPI app initializes
                            │
                            ▼
              @app.on_event("startup")
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
    os.makedirs(UPLOAD_DIR)      init_db()
    (Create uploads folder)    (Create DB tables)
                            │
                            ▼
              Mount static files → /static
              Include router → /api/v1
                            │
                            ▼
              Serve dashboard.html at "/"
```

**What happens:**
- Creates `uploads/` directory for storing RFP files
- Initializes PostgreSQL database, creates all tables (RFP, OEMProduct, etc.)
- Mounts static files (CSS, JS) and routes
- Serves the main dashboard UI

---

#### 2. Document Upload Flow (`POST /api/v1/upload`)

```
User drags/drops PDF/DOCX file
           │
           ▼
    Dashboard.js sends file
           │
           ▼
POST /api/v1/upload (routes.py:18)
           │
           ▼
    Validate file extension
    (.pdf, .docx, .doc only)
           │
           ▼
    Generate unique RFP number
    (RFP-{uuid[:8]})
    Example: RFP-A1B2C3D4
           │
           ▼
    Save file to uploads/{RFP-number}.pdf
           │
           ▼
    crud.create_rfp()
    ┌──────────────────────────────┐
    │ INSERT INTO rfps             │
    │   rfp_number = "RFP-A1B2C3D4"│
    │   title = "original.pdf"     │
    │   document_path = "uploads/."│
    │   status = "uploaded"        │
    └──────────────────────────────┘
           │
           ▼
    Return: { rfp_id, rfp_number, filename }
```

**Database table affected:** `rfps`

---

#### 3. Text Extraction Flow (`POST /api/v1/extract`)

```
Frontend receives rfp_id
           │
           ▼
POST /api/v1/extract?rfp_id=1 (routes.py:52)
           │
           ▼
    crud.get_rfp_by_id(rfp_id)
    (Fetch RFP record from DB)
           │
           ▼
    extractor.extract_text_from_file(document_path)
           │
           ▼
┌──────────────────────────────────────────────────┐
│            EXTRACTOR SERVICE                      │
│           (services/extractor.py)                 │
│                                                   │
│  if .pdf:                                         │
│    ┌─────────────────────────────────────────┐   │
│    │ pdfplumber.open(path)                   │   │
│    │   └── for page in pdf.pages:            │   │
│    │         └── page.extract_text()         │   │
│    │                                          │   │
│    │ Post-processing:                        │   │
│    │   • _clean_line() - normalize whitespace│   │
│    │   • _is_noise_line() - remove headers   │   │
│    │   • _remove_repeated_headers() - dedup  │   │
│    └─────────────────────────────────────────┘   │
│                                                   │
│  if .docx:                                        │
│    ┌─────────────────────────────────────────┐   │
│    │ python-docx Document(path)              │   │
│    │   └── for p in doc.paragraphs:          │   │
│    │         └── p.text                      │   │
│    │   └── for table in doc.tables:          │   │
│    │         └── cell.text (joined with |)   │   │
│    └─────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
           │
           ▼
    Clean extracted text returned
           │
           ▼
    crud.update_rfp_extracted_text(rfp_id, text)
    ┌──────────────────────────────┐
    │ UPDATE rfps                  │
    │   SET extracted_text = "..." │
    │   WHERE id = rfp_id          │
    └──────────────────────────────┘
           │
           ▼
    Return: { rfp_id, text }
```

**Key cleaning operations:**
- Remove page numbers, headers/footers
- Normalize whitespace and special characters
- Filter noise lines (table of contents, indices)
- Extract table data with `|` separators

---

#### 4. AI Analysis Pipeline (`POST /api/v1/analyze/sync`)

This is the core of the application. The LangGraph pipeline processes the RFP through 5 sequential agents.

```
POST /api/v1/analyze/sync?rfp_id=1 (routes.py:163)
           │
           ▼
    crud.get_rfp_by_id(rfp_id)
    Get extracted_text from DB
           │
           ▼
    run_rfp_analysis(rfp_id, extracted_text)
    (agents/__init__.py → agents/graph.py)
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   LANGGRAPH PIPELINE                              │
│                   (agents/graph.py)                               │
│                                                                   │
│   Initialize RFPState:                                            │
│   {                                                               │
│     rfp_id, rfp_text,                                             │
│     sections: [], requirements: [],                               │
│     requirement_matches: [], overall_score: 0,                    │
│     proposal_summary: "", technical_response: "",                 │
│     commercial_response: "", errors: []                           │
│   }                                                               │
│                                                                   │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │              WORKFLOW GRAPH                              │    │
│   │                                                          │    │
│   │   [ENTRY]                                                │    │
│   │      │                                                   │    │
│   │      ▼                                                   │    │
│   │   ┌──────────┐                                           │    │
│   │   │  PARSER  │──────┐                                    │    │
│   │   └──────────┘      │                                    │    │
│   │        │            │ (if no sections)                   │    │
│   │        ▼            ▼                                    │    │
│   │   ┌──────────┐   [END]                                   │    │
│   │   │ ANALYZER │                                           │    │
│   │   └──────────┘                                           │    │
│   │        │                                                 │    │
│   │        ▼                                                 │    │
│   │   ┌──────────┐                                           │    │
│   │   │ MATCHER  │                                           │    │
│   │   └──────────┘                                           │    │
│   │        │                                                 │    │
│   │        ▼                                                 │    │
│   │   ┌──────────┐                                           │    │
│   │   │  SCORER  │                                           │    │
│   │   └──────────┘                                           │    │
│   │        │                                                 │    │
│   │        ▼                                                 │    │
│   │   ┌──────────┐                                           │    │
│   │   │ RESPONSE │                                           │    │
│   │   └──────────┘                                           │    │
│   │        │                                                 │    │
│   │        ▼                                                 │    │
│   │     [END]                                                │    │
│   └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

---

### Individual Agent Details

#### Agent 1: Parser (`agents/parser_agent.py`)

```
INPUT: RFPState.rfp_text (raw extracted text)
           │
           ▼
    ┌─────────────────────────────────────────────────────────┐
    │                    PARSER AGENT                          │
    │                                                          │
    │  LLM: get_parser_llm() → OpenRouter (temp=0.0)           │
    │                                                          │
    │  System Prompt instructs to find:                        │
    │    • Scope of Work                                       │
    │    • Technical Specifications                            │
    │    • Quantity Schedule                                   │
    │    • Delivery Terms                                      │
    │    • Commercial Terms                                    │
    │    • Compliance/Standards                                │
    │    • Testing Requirements                                │
    │    • Documentation                                       │
    │    • Warranty/Guarantee                                  │
    │    • Eligibility/Qualification                           │
    │                                                          │
    │  LLM Returns JSON:                                       │
    │  {                                                       │
    │    "sections": [                                         │
    │      { "name": "Technical Specifications",               │
    │        "content": "...",                                 │
    │        "page_number": 3 }                                │
    │    ],                                                    │
    │    "document_type": "RFP",                               │
    │    "issuing_authority": "State Electricity Board"        │
    │  }                                                       │
    └─────────────────────────────────────────────────────────┘
           │
           ▼
OUTPUT: RFPState.sections = [{ name, content, page_number }, ...]
```

**Purpose:** Structure raw text into logical sections for targeted analysis.

---

#### Agent 2: Analyzer (`agents/analyzer_agent.py`)

```
INPUT: RFPState.sections
           │
           ▼
    ┌─────────────────────────────────────────────────────────┐
    │                   ANALYZER AGENT                         │
    │                                                          │
    │  LLM: get_analyzer_llm() → OpenRouter (temp=0.1)         │
    │                                                          │
    │  Combines all sections into single text:                 │
    │    "=== Section Name ===\n{content}\n\n..."              │
    │                                                          │
    │  Extracts SPECIFIC cable specifications:                 │
    │    • voltage_kv: 1.1, 11, 33 kV                          │
    │    • conductor: Copper, Aluminum                         │
    │    • cores: 1C, 2C, 3C, 4C, 3.5C                         │
    │    • cross_section_mm2: 25, 50, 95, 120 mm²              │
    │    • insulation: PVC, XLPE, EPR                          │
    │    • armour: SWA, AWA, Unarmoured                        │
    │    • standard: IS:1554, IS:7098, IEC, BS                 │
    │    • quantity & quantity_unit                            │
    │                                                          │
    │  LLM Returns JSON:                                       │
    │  {                                                       │
    │    "requirements": [                                     │
    │      {                                                   │
    │        "id": "REQ-001",                                  │
    │        "description": "3.5C x 95mm² XLPE Aluminium",     │
    │        "category": "technical",                          │
    │        "priority": "mandatory",                          │
    │        "specifications": {                               │
    │          "voltage_kv": 1.1,                              │
    │          "conductor": "Aluminum",                        │
    │          "cores": "3.5C",                                │
    │          "cross_section_mm2": 95,                        │
    │          "quantity": 5000,                               │
    │          "quantity_unit": "meters"                       │
    │        }                                                 │
    │      }                                                   │
    │    ],                                                    │
    │    "project_summary": "...",                             │
    │    "budget_info": "...",                                 │
    │    "timeline_info": "Delivery within 30 days"            │
    │  }                                                       │
    └─────────────────────────────────────────────────────────┘
           │
           ▼
OUTPUT:
  RFPState.requirements = [{ id, description, category, priority, specifications }, ...]
  RFPState.project_summary = "..."
  RFPState.budget_info = "..."
  RFPState.timeline_info = "..."
```

**Purpose:** Extract actionable line items with precise technical specifications.

---

#### Agent 3: Matcher (`agents/matcher_agent.py`)

```
INPUT: RFPState.requirements
           │
           ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │                        MATCHER AGENT                                  │
    │                                                                       │
    │  For EACH requirement:                                                │
    │                                                                       │
    │  STEP 1: Database Query (PostgreSQL)                                  │
    │  ┌────────────────────────────────────────────────────────────────┐  │
    │  │ query_oem_products_for_requirement(session, specs)             │  │
    │  │                                                                 │  │
    │  │ SELECT * FROM oem_products                                      │  │
    │  │ JOIN oem_manufacturers ON ...                                   │  │
    │  │ JOIN product_pricing ON ...                                     │  │
    │  │ WHERE:                                                          │  │
    │  │   • voltage_kv <= 1.1 → product_category = "LT Cable"           │  │
    │  │   • voltage_kv <= 33  → product_category = "HT Cable"           │  │
    │  │   • voltage_kv > 33   → product_category = "EHV Cable"          │  │
    │  │                                                                 │  │
    │  │ Then filter by JSON specs:                                      │  │
    │  │   • specifications->>'voltage_kv' >= requirement                │  │
    │  │   • specifications->>'conductor' ILIKE requirement              │  │
    │  │   • specifications->>'cores' = requirement                      │  │
    │  │   • specifications->>'cross_section_mm2' = requirement          │  │
    │  │   • specifications->>'insulation' ILIKE requirement             │  │
    │  │                                                                 │  │
    │  │ Returns: Top 10 candidate products with preliminary scores      │  │
    │  └────────────────────────────────────────────────────────────────┘  │
    │                                                                       │
    │  STEP 2: LLM Scoring (if candidates exist)                            │
    │  ┌────────────────────────────────────────────────────────────────┐  │
    │  │ score_matches_with_llm(requirement, candidates)                │  │
    │  │                                                                 │  │
    │  │ LLM: get_analyzer_llm() → Gemini (temp=0.1)                     │  │
    │  │                                                                 │  │
    │  │ Scoring weights (0-100 total):                                  │  │
    │  │   • Voltage Rating: 25 pts (must match or exceed)               │  │
    │  │   • Cross Section: 25 pts (exact match preferred)               │  │
    │  │   • Conductor Type: 15 pts (Copper vs Aluminum)                 │  │
    │  │   • Insulation Type: 15 pts (XLPE, PVC)                         │  │
    │  │   • Cores: 10 pts (configuration match)                         │  │
    │  │   • Armour Type: 10 pts (SWA, AWA, Unarmoured)                  │  │
    │  │                                                                 │  │
    │  │ Returns: { scored_matches, best_match_id, coverage_score }      │  │
    │  └────────────────────────────────────────────────────────────────┘  │
    │                                                                       │
    │  FALLBACK: simple_score_matches() if LLM fails                        │
    │    (Uses same scoring logic without LLM)                              │
    └──────────────────────────────────────────────────────────────────────┘
           │
           ▼
OUTPUT: RFPState.requirement_matches = [
  {
    "requirement_id": "REQ-001",
    "requirement_description": "...",
    "matches": [
      {
        "product_id": 123,
        "sku": "POLYCAB-XLPE-3.5Cx95",
        "name": "3.5C x 95 sq.mm XLPE Cable",
        "category": "LT Cable",
        "manufacturer": "Polycab",
        "score": 85,
        "matched_specs": { "voltage_kv": true, "conductor": true, ... },
        "price_per_meter": 450.00,
        "in_stock": true,
        "lead_time_days": 7
      }
    ],
    "best_match": { ... top match ... },
    "coverage_score": 85
  }
]
```

**Purpose:** Find best matching products from OEM catalog for each requirement.

**Database tables queried:**
- `oem_products` - Product specifications
- `oem_manufacturers` - Manufacturer info
- `product_pricing` - Price data

---

#### Agent 4: Scorer (`agents/scorer_agent.py`)

```
INPUT: RFPState.requirement_matches, RFPState.requirements
           │
           ▼
    ┌─────────────────────────────────────────────────────────┐
    │                    SCORER AGENT                          │
    │                                                          │
    │  Calculate basic statistics:                             │
    │    • total_reqs = count of requirements                  │
    │    • matched_reqs = count with best_match                │
    │    • avg_coverage = mean of coverage_scores              │
    │    • in_stock_count = items available                    │
    │                                                          │
    │  LLM: get_analyzer_llm() → Gemini (temp=0.1)             │
    │                                                          │
    │  Scoring breakdown (weighted total = 100):               │
    │    • Technical Coverage: 40%                             │
    │    • Price Competitiveness: 25%                          │
    │    • Availability: 20%                                   │
    │    • Compliance: 15%                                     │
    │                                                          │
    │  LLM Returns:                                            │
    │  {                                                       │
    │    "overall_score": 75,                                  │
    │    "scoring_breakdown": {                                │
    │      "technical_coverage": {                             │
    │        "score": 80, "max": 40,                           │
    │        "weighted_score": 32,                             │
    │        "notes": "Strong match on specs"                  │
    │      },                                                  │
    │      "price_competitiveness": { ... },                   │
    │      "availability": { ... },                            │
    │      "compliance": { ... }                               │
    │    },                                                    │
    │    "recommendations": [                                  │
    │      "PURSUE: Good overall match with 75% coverage",     │
    │      "GAP: Missing 185mm² cable - source from partner",  │
    │      "RISK: Item 4 lead time exceeds deadline"           │
    │    ],                                                    │
    │    "go_no_go": "GO",                                     │
    │    "confidence_level": "MEDIUM"                          │
    │  }                                                       │
    └─────────────────────────────────────────────────────────┘
           │
           ▼
OUTPUT:
  RFPState.overall_score = 75
  RFPState.scoring_breakdown = { ... }
  RFPState.recommendations = ["PURSUE: ...", "GAP: ...", ...]
```

**Purpose:** Evaluate bid viability and provide actionable recommendations.

---

#### Agent 5: Response Builder (`agents/response_agent.py`)

```
INPUT: All previous state (matches, scores, recommendations)
           │
           ▼
    ┌─────────────────────────────────────────────────────────┐
    │                  RESPONSE AGENT                          │
    │                                                          │
    │  Calculate total estimated value:                        │
    │    For each matched requirement:                         │
    │      line_total = quantity × price_per_meter             │
    │      total_value += line_total                           │
    │                                                          │
    │  Build line_items array:                                 │
    │    [{ requirement_id, product, sku, quantity,            │
    │       unit_price, line_total, in_stock, lead_time }]     │
    │                                                          │
    │  LLM: get_response_llm() → Gemini (temp=0.3, creative)   │
    │                                                          │
    │  Generates 3 sections:                                   │
    │                                                          │
    │  1. PROPOSAL SUMMARY (2-3 paragraphs)                    │
    │     • Company introduction                               │
    │     • Capability overview                                │
    │     • Key strengths                                      │
    │                                                          │
    │  2. TECHNICAL RESPONSE                                   │
    │     • Compliance matrix (requirement vs offering)        │
    │     • Technical specifications                           │
    │     • Quality certifications (IS/IEC)                    │
    │     • Delivery capability                                │
    │                                                          │
    │  3. COMMERCIAL RESPONSE                                  │
    │     • Pricing schedule table                             │
    │     • Payment terms (30% advance, 70% delivery)          │
    │     • Validity period (90 days)                          │
    │     • Warranty (12 months)                               │
    │     • GST terms                                          │
    │                                                          │
    │  FALLBACK: generate_fallback_*() functions if LLM fails  │
    │    (Template-based response generation)                  │
    └─────────────────────────────────────────────────────────┘
           │
           ▼
OUTPUT:
  RFPState.proposal_summary = "## Proposal Summary\n..."
  RFPState.technical_response = "## Technical Response\n..."
  RFPState.commercial_response = "## Commercial Response\n..."
```

**Purpose:** Generate professional, submission-ready proposal documents.

---

### Final Response Assembly (`graph.py:run_rfp_analysis`)

```
After all agents complete:
           │
           ▼
    Format final_state into API response:
    {
      "rfp_id": "1",
      "status": "completed",
      "analysis": {
        "sections_found": 8,
        "requirements_extracted": 15,
        "requirements_matched": 12,
        "overall_score": 75,
        "project_summary": "...",
        "timeline": "30 days",
        "budget": "₹50 lakhs"
      },
      "matches": [ ... requirement_matches ... ],
      "scoring": {
        "overall_score": 75,
        "breakdown": { ... },
        "recommendations": [ ... ]
      },
      "proposal": {
        "summary": "## Proposal Summary...",
        "technical": "## Technical Response...",
        "commercial": "## Commercial Response..."
      },
      "errors": []
    }
```

---

### State Schema (`agents/state.py`)

```python
class RFPState(TypedDict):
    # Input
    rfp_id: str
    rfp_text: str

    # Parser Agent output
    sections: List[RFPSection]        # { name, content, page_number }

    # Analyzer Agent output
    requirements: List[Requirement]    # { id, description, category, priority, specifications }
    project_summary: str
    budget_info: Optional[str]
    timeline_info: Optional[str]

    # Matcher Agent output
    requirement_matches: List[RequirementMatch]  # { requirement_id, matches[], best_match, coverage_score }

    # Scorer Agent output
    overall_score: float
    scoring_breakdown: dict
    recommendations: List[str]

    # Response Builder output
    proposal_summary: str
    technical_response: str
    commercial_response: str

    # Metadata
    errors: List[str]                  # Accumulated errors from all agents
    current_agent: str
```

---

## Data Flow & Storage

This section details exactly what information is extracted at each stage and where it gets stored.

### Data Extraction & Storage Map

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           WHAT GETS EXTRACTED & WHERE IT GOES                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

STAGE 1: UPLOAD
───────────────
  Extracted:
    • Original filename
    • File extension (.pdf/.docx)
    • File binary content

  Stored In:
    ┌─────────────────────────────────────────────────────────┐
    │  TABLE: rfps                                            │
    │  ├── rfp_number = "RFP-A1B2C3D4" (auto-generated UUID)  │
    │  ├── title = "original_filename.pdf"                    │
    │  ├── document_path = "uploads/RFP-A1B2C3D4.pdf"         │
    │  ├── status = "uploaded"                                │
    │  └── created_at = timestamp                             │
    └─────────────────────────────────────────────────────────┘

    FILE SYSTEM:
    └── uploads/RFP-A1B2C3D4.pdf (binary file)

────────────────────────────────────────────────────────────────────────────────────────

STAGE 2: EXTRACTION
───────────────────
  Extracted from PDF/DOCX:
    • All text content (paragraphs)
    • Table data (cells joined with "|")
    • Cleaned of headers/footers/page numbers

  Stored In:
    ┌─────────────────────────────────────────────────────────┐
    │  TABLE: rfps (UPDATE)                                   │
    │  └── extracted_text = "Full cleaned text content..."    │
    └─────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────────────────────────

STAGE 3: PARSER AGENT
─────────────────────
  Extracted (by LLM):
    • Document sections with names:
      - Scope of Work
      - Technical Specifications
      - Quantity Schedule
      - Delivery Terms
      - Commercial Terms
      - Compliance/Standards
      - Testing Requirements
      - Documentation Requirements
      - Warranty/Guarantee
      - Eligibility/Qualification
    • Document type (RFP/Tender/EOI)
    • Issuing authority name

  Stored In:
    ┌─────────────────────────────────────────────────────────┐
    │  IN-MEMORY: RFPState.sections                           │
    │  [                                                      │
    │    {                                                    │
    │      "name": "Technical Specifications",                │
    │      "content": "1.1kV XLPE cables as per IS:7098...",  │
    │      "page_number": 3                                   │
    │    },                                                   │
    │    { "name": "Quantity Schedule", "content": "...", ... }│
    │  ]                                                      │
    └─────────────────────────────────────────────────────────┘

    NOTE: Sections are NOT persisted to database - they flow
          through the pipeline in memory only.

────────────────────────────────────────────────────────────────────────────────────────

STAGE 4: ANALYZER AGENT
───────────────────────
  Extracted (by LLM):
    • Individual line-item REQUIREMENTS with:
      - Requirement ID (REQ-001, REQ-002, ...)
      - Description ("Supply 3.5C x 95mm² XLPE Cable")
      - Category (technical/commercial/compliance/delivery)
      - Priority (mandatory/preferred/optional)
      - Technical Specifications:
        ┌────────────────────────────────────────────────┐
        │  CABLE SPECIFICATIONS EXTRACTED:               │
        │  • voltage_kv: 1.1, 11, 33 (kV rating)         │
        │  • conductor: "Copper" or "Aluminum"           │
        │  • cores: "1C", "2C", "3C", "3.5C", "4C"       │
        │  • cross_section_mm2: 25, 50, 95, 120, 185...  │
        │  • insulation: "PVC", "XLPE", "EPR"            │
        │  • armour: "SWA", "AWA", "Unarmoured"          │
        │  • sheath: "PVC", "PE"                         │
        │  • standard: "IS:1554", "IS:7098", "IEC"       │
        │  • fire_rating: "FR", "FRLS", "FRLSH"          │
        │  • application: "Indoor", "Outdoor", "UG"      │
        │  • quantity: 5000                              │
        │  • quantity_unit: "meters", "km", "coils"      │
        └────────────────────────────────────────────────┘
    • Project summary
    • Budget information
    • Timeline/delivery requirements

  Stored In:
    ┌─────────────────────────────────────────────────────────┐
    │  IN-MEMORY: RFPState.requirements                       │
    │  [                                                      │
    │    {                                                    │
    │      "id": "REQ-001",                                   │
    │      "description": "3.5C x 95 sq.mm XLPE Aluminium",   │
    │      "category": "technical",                           │
    │      "priority": "mandatory",                           │
    │      "specifications": {                                │
    │        "voltage_kv": 1.1,                               │
    │        "conductor": "Aluminum",                         │
    │        "cores": "3.5C",                                 │
    │        "cross_section_mm2": 95,                         │
    │        "insulation": "XLPE",                            │
    │        "armour": "SWA",                                 │
    │        "quantity": 5000,                                │
    │        "quantity_unit": "meters"                        │
    │      }                                                  │
    │    }                                                    │
    │  ]                                                      │
    │                                                         │
    │  RFPState.project_summary = "Supply of LT cables..."    │
    │  RFPState.budget_info = "Estimated ₹50 lakhs"           │
    │  RFPState.timeline_info = "Delivery within 30 days"     │
    └─────────────────────────────────────────────────────────┘

    CAN BE PERSISTED TO (if enabled):
    ┌─────────────────────────────────────────────────────────┐
    │  TABLE: rfp_products                                    │
    │  ├── rfp_id (FK to rfps)                                │
    │  ├── product_name = "3.5C x 95 sq.mm XLPE Cable"        │
    │  ├── product_category = "LT Cable"                      │
    │  ├── quantity = 5000                                    │
    │  ├── unit = "meters"                                    │
    │  └── specifications = { JSON blob of specs }            │
    └─────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────────────────────────

STAGE 5: MATCHER AGENT
──────────────────────
  READS FROM DATABASE:
    ┌─────────────────────────────────────────────────────────┐
    │  TABLE: oem_products (Pre-seeded product catalog)       │
    │  ├── sku = "POLYCAB-XLPE-3.5Cx95"                       │
    │  ├── product_name = "3.5C x 95 sq.mm XLPE Cable"        │
    │  ├── product_category = "LT Cable"                      │
    │  ├── manufacturer_id → oem_manufacturers.id             │
    │  └── specifications = {                                 │
    │        "voltage_kv": 1.1,                               │
    │        "conductor": "Aluminum",                         │
    │        "cores": "3.5C",                                 │
    │        "cross_section_mm2": 95,                         │
    │        "insulation": "XLPE",                            │
    │        "armour": "SWA",                                 │
    │        "standard": "IS:7098"                            │
    │      }                                                  │
    ├─────────────────────────────────────────────────────────┤
    │  TABLE: oem_manufacturers                               │
    │  ├── name = "Polycab"                                   │
    │  └── website = "https://polycab.com"                    │
    ├─────────────────────────────────────────────────────────┤
    │  TABLE: product_pricing                                 │
    │  ├── oem_product_id → oem_products.id                   │
    │  ├── unit_price = 450.00                                │
    │  ├── currency = "INR"                                   │
    │  └── price_per = "meter"                                │
    └─────────────────────────────────────────────────────────┘

  Extracted/Calculated:
    • Matching products for each requirement
    • Match scores (0-100) based on:
      - Voltage match (25 pts)
      - Cross-section match (25 pts)
      - Conductor match (15 pts)
      - Insulation match (15 pts)
      - Cores match (10 pts)
      - Armour match (10 pts)
    • Best match per requirement
    • Coverage score per requirement

  Stored In:
    ┌─────────────────────────────────────────────────────────┐
    │  IN-MEMORY: RFPState.requirement_matches                │
    │  [                                                      │
    │    {                                                    │
    │      "requirement_id": "REQ-001",                       │
    │      "requirement_description": "3.5C x 95mm²...",      │
    │      "matches": [                                       │
    │        {                                                │
    │          "product_id": 123,                             │
    │          "sku": "POLYCAB-XLPE-3.5Cx95",                 │
    │          "name": "3.5C x 95 sq.mm XLPE Cable",          │
    │          "manufacturer": "Polycab",                     │
    │          "score": 95,                                   │
    │          "matched_specs": {                             │
    │            "voltage_kv": true,                          │
    │            "conductor": true,                           │
    │            "cross_section_mm2": true,                   │
    │            "insulation": true,                          │
    │            "cores": true,                               │
    │            "armour": true                               │
    │          },                                             │
    │          "price_per_meter": 450.00,                     │
    │          "in_stock": true,                              │
    │          "lead_time_days": 7                            │
    │        }                                                │
    │      ],                                                 │
    │      "best_match": { ... top scoring match ... },       │
    │      "coverage_score": 95                               │
    │    }                                                    │
    │  ]                                                      │
    └─────────────────────────────────────────────────────────┘

    CAN BE PERSISTED TO (if enabled):
    ┌─────────────────────────────────────────────────────────┐
    │  TABLE: product_matches                                 │
    │  ├── rfp_product_id → rfp_products.id                   │
    │  ├── oem_product_id → oem_products.id                   │
    │  ├── rank = 1 (1st, 2nd, 3rd best match)                │
    │  ├── spec_match_percentage = 95.0                       │
    │  ├── spec_comparison = { JSON of match details }        │
    │  └── is_selected = false (for final response)           │
    └─────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────────────────────────

STAGE 6: SCORER AGENT
─────────────────────
  Calculated:
    • Overall score (0-100) with weighted breakdown:
      - Technical Coverage: 40%
      - Price Competitiveness: 25%
      - Availability: 20%
      - Compliance: 15%
    • GO/NO-GO recommendation
    • Confidence level (HIGH/MEDIUM/LOW)
    • Actionable recommendations list

  Stored In:
    ┌─────────────────────────────────────────────────────────┐
    │  IN-MEMORY: RFPState                                    │
    │  ├── overall_score = 75                                 │
    │  ├── scoring_breakdown = {                              │
    │  │     "technical_coverage": {                          │
    │  │       "score": 80, "max": 40,                        │
    │  │       "weighted_score": 32,                          │
    │  │       "notes": "Strong match on voltage and specs"   │
    │  │     },                                               │
    │  │     "price_competitiveness": { ... },                │
    │  │     "availability": { ... },                         │
    │  │     "compliance": { ... }                            │
    │  │   }                                                  │
    │  └── recommendations = [                                │
    │        "PURSUE: Good overall match with 75% coverage",  │
    │        "GAP: Missing 185mm² cable - source elsewhere",  │
    │        "RISK: Item 4 lead time exceeds deadline"        │
    │      ]                                                  │
    └─────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────────────────────────

STAGE 7: RESPONSE AGENT
───────────────────────
  Generated:
    • Proposal Summary (company intro, capabilities)
    • Technical Response (compliance matrix, specs, certs)
    • Commercial Response (pricing table, terms, warranty)
    • Total estimated value

  Stored In:
    ┌─────────────────────────────────────────────────────────┐
    │  IN-MEMORY: RFPState                                    │
    │  ├── proposal_summary = "## Proposal Summary\n..."      │
    │  ├── technical_response = "## Technical Response\n..."  │
    │  └── commercial_response = "## Commercial Response\n..."│
    └─────────────────────────────────────────────────────────┘

    CAN BE PERSISTED TO (if enabled):
    ┌─────────────────────────────────────────────────────────┐
    │  TABLE: rfp_responses                                   │
    │  ├── rfp_id → rfps.id                                   │
    │  ├── status = "draft"                                   │
    │  ├── total_material_cost = 2250000.00                   │
    │  ├── total_test_cost = 50000.00                         │
    │  ├── total_cost = 2300000.00                            │
    │  ├── currency = "INR"                                   │
    │  └── response_summary = "AI-generated summary..."       │
    ├─────────────────────────────────────────────────────────┤
    │  TABLE: response_line_items                             │
    │  ├── rfp_response_id → rfp_responses.id                 │
    │  ├── rfp_product_id → rfp_products.id                   │
    │  ├── oem_product_id → oem_products.id                   │
    │  ├── quantity = 5000                                    │
    │  ├── unit_price = 450.00                                │
    │  └── total_price = 2250000.00                           │
    ├─────────────────────────────────────────────────────────┤
    │  TABLE: response_tests                                  │
    │  ├── rfp_response_id → rfp_responses.id                 │
    │  ├── test_name = "Voltage Withstand Test"               │
    │  └── price = 15000.00                                   │
    └─────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────────────────────────

FINAL API RESPONSE (Returned to Frontend)
─────────────────────────────────────────
  {
    "rfp_id": "1",
    "status": "completed",
    "analysis": {
      "sections_found": 8,
      "requirements_extracted": 15,
      "requirements_matched": 12,
      "overall_score": 75,
      "project_summary": "...",
      "timeline": "30 days",
      "budget": "₹50 lakhs"
    },
    "matches": [ ... all requirement_matches ... ],
    "scoring": {
      "overall_score": 75,
      "breakdown": { ... },
      "recommendations": [ ... ]
    },
    "proposal": {
      "summary": "## Proposal Summary...",
      "technical": "## Technical Response...",
      "commercial": "## Commercial Response..."
    },
    "errors": []
  }
```

### Database Tables Summary

| Table | When Populated | Data Stored |
|-------|----------------|-------------|
| `rfps` | Upload & Extract | Document metadata, extracted text, status |
| `rfp_products` | After Analysis (optional) | Extracted requirements with specifications |
| `rfp_tests` | After Analysis (optional) | Testing requirements from RFP |
| `oem_products` | Pre-seeded | Product catalog with JSON specifications |
| `oem_manufacturers` | Pre-seeded | Manufacturer names (Polycab, Havells, KEI, etc.) |
| `product_pricing` | Pre-seeded | Unit prices for each product |
| `test_pricing` | Pre-seeded | Prices for tests (Routine, Type, Special) |
| `product_matches` | After Analysis (optional) | Requirement-to-product mappings with scores |
| `rfp_responses` | After Analysis (optional) | Final proposal with total costs |
| `response_line_items` | After Analysis (optional) | Individual priced items in response |
| `response_tests` | After Analysis (optional) | Tests included in response with pricing |

### Pre-Seeded Data (Product Catalog)

The following tables must be seeded before analysis can work:

```bash
python scripts/seed_enhanced_data.py
```

This populates:
- **oem_manufacturers**: Polycab, Havells, KEI, Finolex, etc.
- **oem_products**: 100+ cable/wire products with specifications
- **product_pricing**: Prices per meter/unit for all products
- **test_pricing**: Standard test prices (Routine tests, Type tests, etc.)

---

## Database Models

### Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│      RFP        │       │   RFPProduct    │       │   ProductMatch  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │──┐    │ id (PK)         │
│ rfp_number      │  │    │ rfp_id (FK)     │◄─┤    │ rfp_product_id  │◄─┘
│ title           │  │    │ product_name    │  │    │ oem_product_id  │◄─┐
│ status          │  │    │ specifications  │  │    │ rank            │  │
│ extracted_text  │  │    │ quantity        │  │    │ spec_match_%    │  │
│ document_path   │  │    └─────────────────┘  │    └─────────────────┘  │
└─────────────────┘  │                         │                         │
        │            │    ┌─────────────────┐  │                         │
        │            └───►│    RFPTest      │  │                         │
        │                 ├─────────────────┤  │                         │
        │                 │ id (PK)         │  │                         │
        │                 │ rfp_id (FK)     │◄─┘                         │
        │                 │ test_name       │                            │
        │                 └─────────────────┘                            │
        │                                                                │
        ▼                                                                │
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐ │
│   RFPResponse   │       │ResponseLineItem │       │   OEMProduct    │ │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤ │
│ id (PK)         │──┐    │ id (PK)         │       │ id (PK)         │─┘
│ rfp_id (FK)     │◄─┤    │ rfp_response_id │◄──────│ manufacturer_id │◄─┐
│ total_cost      │  │    │ oem_product_id  │       │ sku             │  │
│ response_summary│  │    │ quantity        │       │ product_name    │  │
└─────────────────┘  │    │ unit_price      │       │ specifications  │  │
                     │    └─────────────────┘       │ (JSON)          │  │
                     │                              └─────────────────┘  │
                     │    ┌─────────────────┐                            │
                     │    │  ResponseTest   │       ┌─────────────────┐  │
                     │    ├─────────────────┤       │ OEMManufacturer │  │
                     └───►│ id (PK)         │       ├─────────────────┤  │
                          │ rfp_response_id │       │ id (PK)         │──┘
                          │ test_name       │       │ name            │
                          │ price           │       │ website         │
                          └─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│ ProductPricing  │       │   TestPricing   │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ oem_product_id  │◄──────│ test_name       │
│ unit_price      │       │ test_category   │
│ currency        │       │ price           │
│ price_per       │       │ standard_ref    │
└─────────────────┘       └─────────────────┘
```

### Key Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `RFP` | Uploaded RFP documents | rfp_number, extracted_text, status |
| `RFPProduct` | Requirements extracted from RFP | specifications (JSON), quantity |
| `OEMProduct` | Product catalog | sku, specifications (JSON), category |
| `OEMManufacturer` | Manufacturer registry | name, website |
| `ProductPricing` | Product prices | unit_price, price_per, currency |
| `ProductMatch` | Requirement-to-product mappings | spec_match_percentage, rank |
| `RFPResponse` | Final proposals | total_cost, response_summary |
| `TestPricing` | Test/service pricing | test_name, price, standard_reference |

---

## Setup Instructions

### Prerequisites
- Python 3.8+
- PostgreSQL
- OpenRouter API key (get one at https://openrouter.ai/keys)

### 1. Clone & Setup Environment

```bash
git clone <repository-url>
cd B2B-RFP
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file (see `.env.example`):

```env
# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here

# Database Configuration
DATABASE_URL=postgresql+psycopg2://rfp_user:rfp_password@localhost:5432/rfp_db

# Optional: Override default model (default: x-ai/grok-4.1-fast:free)
# Other free models available:
# - google/gemini-2.0-flash-exp:free
# - meta-llama/llama-3.2-3b-instruct:free
# - mistralai/mistral-7b-instruct:free
# LLM_MODEL=x-ai/grok-4.1-fast:free
```

### 3. Initialize Database

```bash
# Tables are auto-created on first run
# Seed the database with components and tests:
python scripts/seed_enhanced_data.py
```

### 4. Start the Server

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` in your browser.

## Usage

### 1. Upload RFP
- Open the dashboard
- Drag & drop a PDF/DOCX file or click to browse
- Text is automatically extracted

### 2. Run Analysis
- Go to "AI Analysis" view
- Click "Start Analysis"
- Watch the agent pipeline process in real-time

### 3. View Results
- See overall match score
- Review extracted requirements
- Check component matches with coverage scores

### 4. Export Proposal
- View generated proposal summary
- Export technical & commercial responses as TXT

## API Endpoints

### Core RFP Workflow

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard (main UI) |
| POST | `/api/v1/upload` | Upload RFP document (PDF/DOCX) |
| POST | `/api/v1/extract` | Extract text from uploaded RFP |
| POST | `/api/v1/analyze/sync` | Run full AI analysis pipeline (blocking) |
| POST | `/api/v1/analyze` | Run analysis in background (async) |
| GET | `/api/v1/analyze/status` | Check analysis status |
| GET | `/api/v1/analyze/result` | Get full analysis results |

### RFP Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/rfps` | List all RFPs |
| GET | `/api/v1/rfps/{rfp_id}` | Get RFP with all related data |
| DELETE | `/api/v1/rfps/{rfp_id}` | Delete RFP and related data |

### Product & Test Catalog

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/oem-products` | List OEM products (filterable by category/search) |
| GET | `/api/v1/test-pricing` | List all test pricing entries |
| GET | `/api/v1/manufacturers` | List all OEM manufacturers |

### Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/docs` | Swagger/OpenAPI documentation |
| GET | `/redoc` | ReDoc API documentation |

## Color Theme

The UI uses a Halloween/dark space color palette:

| Color | Hex | Usage |
|-------|-----|-------|
| Orange | `#ff6500` | Primary accent, buttons |
| Blue | `#1e3e62` | Secondary backgrounds |
| Navy | `#0b192c` | Cards, containers |
| Black | `#000000` | Main background |

---

## LangGraph Architecture Deep Dive

This section explains how LangGraph orchestrates the AI agent pipeline in detail.

### What is LangGraph?

LangGraph is a library built on top of LangChain for building **stateful, multi-agent workflows**. It models workflows as **directed graphs** where:
- **Nodes** = Individual agents or processing steps
- **Edges** = Transitions between agents (can be conditional)
- **State** = Shared data object that flows through all nodes

### Why LangGraph for RFP Analysis?

| Feature | Benefit for RFP Processing |
|---------|---------------------------|
| **Sequential Pipeline** | Each agent builds on the previous agent's output |
| **Conditional Routing** | Skip agents if previous step fails (e.g., no sections found) |
| **Shared State** | All agents can access/modify the same RFPState object |
| **Error Accumulation** | Errors from any agent are collected without stopping the pipeline |
| **Compiled Graph** | Workflow is validated at startup, not runtime |

### Graph Definition (`app/agents/graph.py`)

```python
from langgraph.graph import StateGraph, END
from .state import RFPState

# 1. Create graph with state schema
workflow = StateGraph(RFPState)

# 2. Add nodes (each agent is a function)
workflow.add_node("parser", parser_agent)      # Stage 1
workflow.add_node("analyzer", analyzer_agent)  # Stage 2
workflow.add_node("matcher", matcher_agent)    # Stage 3
workflow.add_node("scorer", scorer_agent)      # Stage 4
workflow.add_node("response", response_agent)  # Stage 5

# 3. Set entry point
workflow.set_entry_point("parser")

# 4. Add edges (transitions between nodes)
workflow.add_conditional_edges(
    "parser",                        # From node
    should_continue_after_parser,    # Decision function
    {
        "analyzer": "analyzer",      # If sections found → continue
        "end": END                   # If no sections → stop
    }
)

workflow.add_edge("matcher", "scorer")   # Always: matcher → scorer
workflow.add_edge("scorer", "response")  # Always: scorer → response
workflow.add_edge("response", END)       # Always: response → end

# 5. Compile the graph
rfp_analysis_graph = workflow.compile()
```

### Visual Graph Representation

**Interactive Diagram:** Open `/static/langgraph-diagram.html` in your browser for an interactive visualization.

**GitHub Mermaid Diagram:**

```mermaid
flowchart TD
    subgraph LangGraph["LangGraph RFP Analysis Pipeline"]
        START((START)) --> PARSER

        subgraph PARSER_BOX["1. Parser Agent"]
            PARSER[/"📄 Parser Agent\n―――――――――\nExtract Sections"/]
        end

        PARSER -->|"sections.length > 0"| ANALYZER
        PARSER -->|"no sections"| END_EARLY((END))

        subgraph ANALYZER_BOX["2. Analyzer Agent"]
            ANALYZER[/"🔍 Analyzer Agent\n―――――――――\nExtract Requirements"/]
        end

        ANALYZER -->|"requirements.length > 0"| MATCHER
        ANALYZER -->|"no requirements"| SCORER

        subgraph MATCHER_BOX["3. Matcher Agent"]
            MATCHER[/"🔗 Matcher Agent\n―――――――――\nMatch Products\n(DB + LLM)"/]
        end

        MATCHER --> SCORER

        subgraph SCORER_BOX["4. Scorer Agent"]
            SCORER[/"📊 Scorer Agent\n―――――――――\nCalculate Score\n(0-100)"/]
        end

        SCORER --> RESPONSE

        subgraph RESPONSE_BOX["5. Response Agent"]
            RESPONSE[/"📝 Response Agent\n―――――――――\nGenerate Proposal"/]
        end

        RESPONSE --> END_SUCCESS((END))
    end

    style START fill:#00c853,stroke:#00c853,color:#000
    style END_EARLY fill:#ff1744,stroke:#ff1744,color:#fff
    style END_SUCCESS fill:#00c853,stroke:#00c853,color:#000
    style PARSER fill:#1e3e62,stroke:#ff6500,color:#fff
    style ANALYZER fill:#1e3e62,stroke:#ff6500,color:#fff
    style MATCHER fill:#1e3e62,stroke:#ff6500,color:#fff
    style SCORER fill:#1e3e62,stroke:#ff6500,color:#fff
    style RESPONSE fill:#1e3e62,stroke:#ff6500,color:#fff
```

**ASCII Diagram:**

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                    LANGGRAPH WORKFLOW                        │
                    │                                                              │
                    │    ┌──────────┐                                              │
                    │    │  START   │                                              │
                    │    └────┬─────┘                                              │
                    │         │                                                    │
                    │         ▼                                                    │
                    │    ┌──────────┐     sections=[]      ┌───────┐              │
                    │    │  PARSER  │─────────────────────►│  END  │              │
                    │    │  Agent   │                      └───────┘              │
                    │    └────┬─────┘                                              │
                    │         │ sections=[...]                                     │
                    │         ▼                                                    │
                    │    ┌──────────┐     requirements=[]   ┌──────────┐          │
                    │    │ ANALYZER │──────────────────────►│  SCORER  │──┐       │
                    │    │  Agent   │                       └──────────┘  │       │
                    │    └────┬─────┘                                      │       │
                    │         │ requirements=[...]                         │       │
                    │         ▼                                            │       │
                    │    ┌──────────┐                                      │       │
                    │    │ MATCHER  │                                      │       │
                    │    │  Agent   │                                      │       │
                    │    └────┬─────┘                                      │       │
                    │         │                                            │       │
                    │         ▼                                            │       │
                    │    ┌──────────┐◄─────────────────────────────────────┘       │
                    │    │  SCORER  │                                              │
                    │    │  Agent   │                                              │
                    │    └────┬─────┘                                              │
                    │         │                                                    │
                    │         ▼                                                    │
                    │    ┌──────────┐                                              │
                    │    │ RESPONSE │                                              │
                    │    │  Agent   │                                              │
                    │    └────┬─────┘                                              │
                    │         │                                                    │
                    │         ▼                                                    │
                    │    ┌───────┐                                                 │
                    │    │  END  │                                                 │
                    │    └───────┘                                                 │
                    └─────────────────────────────────────────────────────────────┘
```

### State Schema (`app/agents/state.py`)

The `RFPState` is a TypedDict that flows through all agents:

```python
class RFPState(TypedDict):
    # ═══════════════════════════════════════════════════════════════
    # INPUT (Set at the start)
    # ═══════════════════════════════════════════════════════════════
    rfp_id: str                    # Unique identifier
    rfp_text: str                  # Raw extracted text from PDF/DOCX

    # ═══════════════════════════════════════════════════════════════
    # PARSER AGENT OUTPUT
    # ═══════════════════════════════════════════════════════════════
    sections: List[RFPSection]     # Extracted document sections
    # Example: [{"name": "Technical Specs", "content": "...", "page_number": 3}]

    # ═══════════════════════════════════════════════════════════════
    # ANALYZER AGENT OUTPUT
    # ═══════════════════════════════════════════════════════════════
    requirements: List[Requirement]  # Line-item requirements
    # Example: [{"id": "REQ-001", "description": "95mm² XLPE Cable",
    #            "specifications": {"voltage_kv": 1.1, "conductor": "Copper"}}]
    project_summary: str           # Brief project description
    budget_info: Optional[str]     # Budget constraints if mentioned
    timeline_info: Optional[str]   # Delivery timeline

    # ═══════════════════════════════════════════════════════════════
    # MATCHER AGENT OUTPUT
    # ═══════════════════════════════════════════════════════════════
    requirement_matches: List[RequirementMatch]  # Products matched to requirements
    # Example: [{"requirement_id": "REQ-001", "best_match": {...}, "coverage_score": 85}]

    # ═══════════════════════════════════════════════════════════════
    # SCORER AGENT OUTPUT
    # ═══════════════════════════════════════════════════════════════
    overall_score: float           # 0-100 overall match score
    scoring_breakdown: dict        # Detailed scoring by category
    recommendations: List[str]     # Actionable recommendations

    # ═══════════════════════════════════════════════════════════════
    # RESPONSE AGENT OUTPUT
    # ═══════════════════════════════════════════════════════════════
    proposal_summary: str          # Executive summary
    technical_response: str        # Technical compliance response
    commercial_response: str       # Pricing and terms

    # ═══════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════
    errors: Annotated[List[str], add]  # Accumulates errors (special annotation)
    current_agent: str             # Currently executing agent name
```

### Agent Function Pattern

Each agent follows this pattern:

```python
def agent_name(state: RFPState) -> dict:
    """
    Agent receives full state, returns ONLY the fields it modifies.
    LangGraph automatically merges the returned dict into state.
    """
    # 1. Read inputs from state
    input_data = state.get("previous_output", [])

    # 2. Process with LLM
    try:
        llm = get_llm()
        response = llm.invoke([
            SystemMessage(content="System prompt here"),
            HumanMessage(content=f"Process this: {input_data}")
        ])
        result = parse_json(response.content)
    except Exception as e:
        # 3. Handle errors gracefully
        return {
            "errors": [f"Agent failed: {str(e)}"],
            "current_agent": "agent_name"
        }

    # 4. Return ONLY modified fields
    return {
        "output_field": result,
        "current_agent": "agent_name"
    }
```

### Conditional Routing Functions

```python
def should_continue_after_parser(state: RFPState) -> str:
    """
    Decision function: called after parser completes.
    Returns the NAME of the next node to execute.
    """
    if state.get("sections") and len(state["sections"]) > 0:
        return "analyzer"  # Continue to analyzer
    return "end"           # Stop pipeline (no sections found)

def should_continue_after_analyzer(state: RFPState) -> str:
    """
    Decision function: called after analyzer completes.
    """
    if state.get("requirements") and len(state["requirements"]) > 0:
        return "matcher"   # Continue to matcher
    return "scorer"        # Skip matcher, go to scorer (will report issue)
```

### How State Flows Through Agents

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           STATE FLOW DIAGRAM                                    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  INITIAL STATE                                                                  │
│  {                                                                              │
│    rfp_id: "1",                                                                 │
│    rfp_text: "Full RFP document text...",                                       │
│    sections: [],              ← Empty                                           │
│    requirements: [],          ← Empty                                           │
│    requirement_matches: [],   ← Empty                                           │
│    overall_score: 0,          ← Zero                                            │
│    errors: []                 ← Empty                                           │
│  }                                                                              │
│       │                                                                         │
│       ▼                                                                         │
│  ┌─────────────┐                                                                │
│  │   PARSER    │ Reads: rfp_text                                                │
│  │   AGENT     │ Returns: { sections: [...], current_agent: "parser" }          │
│  └─────────────┘                                                                │
│       │                                                                         │
│       ▼                                                                         │
│  STATE AFTER PARSER                                                             │
│  {                                                                              │
│    ...                                                                          │
│    sections: [                 ← NOW POPULATED                                  │
│      { name: "Technical Specs", content: "...", page_number: 3 },               │
│      { name: "Quantity Schedule", content: "...", page_number: 5 }              │
│    ],                                                                           │
│    requirements: [],           ← Still empty                                    │
│  }                                                                              │
│       │                                                                         │
│       ▼                                                                         │
│  ┌─────────────┐                                                                │
│  │  ANALYZER   │ Reads: sections                                                │
│  │   AGENT     │ Returns: { requirements: [...], project_summary: "..." }       │
│  └─────────────┘                                                                │
│       │                                                                         │
│       ▼                                                                         │
│  STATE AFTER ANALYZER                                                           │
│  {                                                                              │
│    ...                                                                          │
│    sections: [...],            ← Unchanged                                      │
│    requirements: [             ← NOW POPULATED                                  │
│      { id: "REQ-001", description: "95mm² Cable", specifications: {...} }       │
│    ],                                                                           │
│    project_summary: "Supply of LT cables for...",                               │
│  }                                                                              │
│       │                                                                         │
│       ▼                                                                         │
│  ┌─────────────┐                                                                │
│  │   MATCHER   │ Reads: requirements                                            │
│  │   AGENT     │ Queries: PostgreSQL (oem_products table)                       │
│  │             │ Returns: { requirement_matches: [...] }                        │
│  └─────────────┘                                                                │
│       │                                                                         │
│       ▼                                                                         │
│  ... continues through SCORER and RESPONSE agents ...                           │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Error Handling with `Annotated[List[str], add]`

The `errors` field uses a special LangGraph annotation:

```python
errors: Annotated[List[str], add]
```

This means:
- When any agent returns `{"errors": ["Some error"]}`, it **appends** to the list
- Errors accumulate across all agents instead of being overwritten
- The pipeline continues even if one agent fails

Example:
```python
# Parser returns:
{"errors": ["Failed to parse JSON"]}

# Matcher returns:
{"errors": ["No products found"]}

# Final state has BOTH errors:
state["errors"] = ["Failed to parse JSON", "No products found"]
```

### Running the Graph

```python
async def run_rfp_analysis(rfp_id: str, rfp_text: str) -> dict:
    # 1. Initialize state with all required fields
    initial_state: RFPState = {
        "rfp_id": rfp_id,
        "rfp_text": rfp_text,
        "sections": [],
        "requirements": [],
        # ... all other fields initialized
    }

    # 2. Invoke the compiled graph
    # This runs all agents in sequence according to the edges
    final_state = rfp_analysis_graph.invoke(initial_state)

    # 3. Format and return results
    return {
        "status": "completed",
        "analysis": {...},
        "matches": final_state["requirement_matches"],
        "proposal": {...}
    }
```

### LLM Configuration per Agent

Different agents use different LLM settings:

| Agent | Temperature | Reasoning |
|-------|-------------|-----------|
| Parser | 0.0 | Must be deterministic for consistent section extraction |
| Analyzer | 0.1 | Mostly deterministic, slight flexibility for spec interpretation |
| Matcher | 0.1 | Consistent scoring with minor flexibility |
| Scorer | 0.1 | Balanced for numerical scoring |
| Response | 0.3 | More creative for professional writing |

```python
# In app/agents/llm.py (using OpenRouter)
def get_parser_llm():
    return OpenRouterLLM(model="x-ai/grok-4.1-fast:free", temperature=0.0)

def get_analyzer_llm():
    return OpenRouterLLM(model="x-ai/grok-4.1-fast:free", temperature=0.1)

def get_response_llm():
    return OpenRouterLLM(model="x-ai/grok-4.1-fast:free", temperature=0.3)
```

### Debugging Agent Outputs

To inspect what each agent produces, use the debug endpoint:

```bash
# Run analysis with debug mode
POST /api/v1/analyze/debug?rfp_id=1

# Response includes intermediate states:
{
  "stages": {
    "parser": {
      "input": { "rfp_text": "..." },
      "output": { "sections": [...] },
      "duration_ms": 1234
    },
    "analyzer": {
      "input": { "sections": [...] },
      "output": { "requirements": [...] },
      "duration_ms": 2345
    },
    ...
  }
}
```

### Terminal Logging

The application includes comprehensive terminal logging for debugging and monitoring the agent pipeline. When running analysis, you'll see colored output showing:

```
############################################################
#  RFP ANALYSIS WORKFLOW STARTED
#  RFP ID: rfp-123
#  Time: 14:30:45
############################################################

============================================================
[14:30:45] ▶ PARSER AGENT STARTED
============================================================
    Input RFP text length: 15420 characters
  → Initializing LLM...
  📡 Calling LLM: x-ai/grok-4.1-fast:free
  📥 LLM Response received (2340 chars)
  → Parsing JSON response...
  ✓ Extracted 8 sections
    #   | Section Name                   | Content Length
    -------------------------------------------------
    1   | Scope of Work                  | 1234
    2   | Technical Specifications       | 3456
    ...

[14:30:52] ◼ PARSER AGENT ✓ COMPLETED
------------------------------------------------------------

... (continues through all agents) ...

############################################################
#  ✓ WORKFLOW COMPLETED SUCCESSFULLY
#  RFP ID: rfp-123
#  Duration: 45.23 seconds
############################################################
```

**Logging Features:**
- Color-coded output (green=success, red=error, yellow=warning, blue=steps)
- Agent start/end markers with timestamps
- LLM call tracking with model name
- Summary tables for sections, requirements, and matches
- Total duration tracking

### Robust JSON Parsing

The application includes a robust JSON extraction utility (`json_utils.py`) that handles common LLM response issues:

- Extracts JSON from markdown code blocks
- Fixes trailing commas
- Escapes unescaped newlines/tabs in strings
- Repairs truncated JSON responses
- Multiple fallback strategies

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Pipeline stops at parser | No sections extracted | Check if RFP text is too short or malformed |
| Empty requirement_matches | No products match specs | Verify OEM products are seeded, check spec format |
| Low overall_score | Poor requirement coverage | Review matcher scoring weights |
| LLM JSON parse errors | LLM returning malformed JSON | Robust parser handles most cases; check terminal logs for raw response |
| "Unterminated string" error | Unescaped newlines in JSON | Fixed by `json_utils.py` - escapes strings automatically |

---

## Agent Logic & Algorithms

This section details the internal logic, algorithms, and decision-making processes used by each agent in the pipeline.

### 1. Parser Agent Logic

**File:** `app/agents/parser_agent.py`

**Purpose:** Extract structured sections from raw RFP document text.

**Algorithm:**
```
1. INPUT: Raw RFP text (extracted from PDF/DOCX)
2. PROCESS:
   a. Send text to LLM with system prompt containing section patterns
   b. LLM identifies sections using pattern matching for:
      - Headers (e.g., "SECTION A:", "1.0 SCOPE", "TECHNICAL SPECIFICATIONS")
      - Keywords (e.g., "shall supply", "specifications", "delivery")
      - Document structure (numbered lists, tables)
   c. Extract JSON response with robust parser (handles malformed JSON)
3. OUTPUT: Array of sections [{name, content, page_number}]
```

**Key Features:**
- Temperature: 0.0 (deterministic output)
- Looks for 10 common RFP section types
- Summarizes long sections to prevent token overflow
- Falls back gracefully if parsing fails

---

### 2. Analyzer Agent Logic

**File:** `app/agents/analyzer_agent.py`

**Purpose:** Extract specific, actionable requirements with technical specifications.

**Algorithm:**
```
1. INPUT: Parsed sections from Parser Agent
2. PROCESS:
   a. Concatenate all sections: "=== Section Name ===\n{content}"
   b. LLM analyzes with cable-specific extraction prompt
   c. For each requirement found:
      - Assign unique ID (REQ-001, REQ-002, ...)
      - Classify category: technical | commercial | compliance | delivery
      - Classify priority: mandatory | preferred | optional
      - Extract specifications object with typed fields
3. OUTPUT: Requirements array + project metadata
```

**Specification Extraction Schema:**
| Field | Type | Example | Description |
|-------|------|---------|-------------|
| voltage_kv | float | 1.1, 11, 33 | Voltage rating in kV |
| conductor | string | "Copper", "Aluminum" | Conductor material |
| cores | string | "3C", "3.5C", "4C" | Core configuration |
| cross_section_mm2 | int | 25, 50, 95, 120 | Cross-sectional area |
| insulation | string | "XLPE", "PVC", "EPR" | Insulation type |
| armour | string | "SWA", "AWA", "Unarmoured" | Armour type |
| standard | string | "IS:7098", "IEC 60502" | Applicable standard |
| quantity | int | 5000 | Required quantity |
| quantity_unit | string | "meters", "km" | Unit of measurement |

---

### 3. Matcher Agent Logic

**File:** `app/agents/matcher_agent.py`

**Purpose:** Match requirements to OEM products in database using hybrid approach.

**Algorithm (Two-Stage Matching):**

```
STAGE 1: Database Query (Preliminary Filtering)
┌─────────────────────────────────────────────────────────────┐
│ For each requirement:                                        │
│   1. Determine product category from voltage:                │
│      - voltage ≤ 1.1 kV → "LT Cable"                        │
│      - voltage ≤ 33 kV  → "HT Cable"                        │
│      - voltage > 33 kV  → "EHV Cable"                       │
│                                                              │
│   2. Query OEMProduct table with category filter             │
│                                                              │
│   3. Calculate preliminary score for each product:           │
│      - Check voltage match (must meet or exceed)             │
│      - Check conductor type match                            │
│      - Check cores configuration match                       │
│      - Check cross-section match                             │
│      - Check insulation type match                           │
│      preliminary_score = matches / total_checks × 100        │
│                                                              │
│   4. Return top 10 candidates sorted by preliminary score    │
└─────────────────────────────────────────────────────────────┘

STAGE 2: LLM Scoring (Intelligent Ranking)
┌─────────────────────────────────────────────────────────────┐
│ For each requirement + candidates:                           │
│   1. Send to LLM with scoring rubric:                       │
│      - Voltage Rating:    25 points (must match/exceed)     │
│      - Cross Section:     25 points (exact match preferred) │
│      - Conductor Type:    15 points (must match)            │
│      - Insulation Type:   15 points (should match)          │
│      - Cores:             10 points (must match)            │
│      - Armour Type:       10 points (should match)          │
│      ─────────────────────────────────                      │
│      Total:              100 points                          │
│                                                              │
│   2. LLM returns scored_matches with:                       │
│      - product_id, score (0-100)                            │
│      - matched_specs: {voltage: true, conductor: false...}  │
│      - notes: "Good match, insulation differs"              │
│                                                              │
│   3. Select best_match (highest score)                      │
└─────────────────────────────────────────────────────────────┘
```

**Fallback Logic:**
If LLM fails, uses `simple_score_matches()` function with same point weights.

---

### 4. Scorer Agent Logic

**File:** `app/agents/scorer_agent.py`

**Purpose:** Evaluate overall RFP fulfillment capability and generate recommendations.

**Scoring Algorithm:**

```
┌─────────────────────────────────────────────────────────────┐
│                    SCORING BREAKDOWN                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Technical Coverage (40% weight)                             │
│  ├── Do our products meet the specifications?               │
│  ├── Score = avg(all requirement coverage scores)           │
│  └── weighted_score = score × 0.40                          │
│                                                              │
│  Price Competitiveness (25% weight)                         │
│  ├── Are prices market-competitive?                         │
│  ├── Evaluated by LLM based on product pricing              │
│  └── weighted_score = score × 0.25                          │
│                                                              │
│  Availability (20% weight)                                   │
│  ├── in_stock_count / matched_requirements                  │
│  ├── Lead time vs delivery deadline                         │
│  └── weighted_score = score × 0.20                          │
│                                                              │
│  Compliance (15% weight)                                     │
│  ├── Standards certification match                          │
│  ├── IS/IEC/BS compliance                                   │
│  └── weighted_score = score × 0.15                          │
│                                                              │
│  OVERALL_SCORE = Σ(weighted_scores)                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Recommendation Generation:**
LLM generates actionable recommendations in categories:
- **PURSUE:** Opportunities to bid aggressively
- **GAP:** Missing products that need sourcing
- **ACTION:** Required steps before submission
- **RISK:** Potential issues (lead time, compliance)

**Go/No-Go Decision:**
- Score ≥ 70%: **GO** - Strong candidate
- Score 40-69%: **CONDITIONAL GO** - Needs gap filling
- Score < 40%: **NO GO** - Too many gaps

---

### 5. Response Agent Logic

**File:** `app/agents/response_agent.py`

**Purpose:** Generate professional proposal document with all sections.

**Algorithm:**

```
1. INPUT: All state data (matches, scores, recommendations)

2. CALCULATE PRICING:
   for each matched requirement:
       quantity = specs.quantity OR default 1000 meters
       unit_price = best_match.price_per_meter
       line_total = quantity × unit_price
       total_value += line_total

3. PREPARE CONTEXT:
   - Sanitize all strings (remove control characters)
   - Truncate long strings (>1000 chars)
   - Build line_items array with pricing

4. GENERATE PROPOSAL via LLM:
   ┌─────────────────────────────────────────────────────────┐
   │ Proposal Summary (2-3 paragraphs)                       │
   │ ├── Company introduction                                │
   │ ├── Capability overview with match %                    │
   │ └── Key strengths                                       │
   │                                                         │
   │ Technical Response (markdown)                           │
   │ ├── Compliance matrix table                             │
   │ ├── Product specifications                              │
   │ ├── Quality certifications                              │
   │ └── Delivery capability                                 │
   │                                                         │
   │ Commercial Response (markdown)                          │
   │ ├── Pricing schedule table                              │
   │ ├── Total estimated value                               │
   │ ├── Payment terms (30% advance, 70% delivery)           │
   │ ├── Validity (90 days)                                  │
   │ └── Warranty (12 months)                                │
   └─────────────────────────────────────────────────────────┘

5. FALLBACK TEMPLATES:
   If LLM fails, uses template functions:
   - generate_fallback_summary()
   - generate_fallback_technical()
   - generate_fallback_commercial()
```

---

### State Flow Between Agents

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           RFPState (TypedDict)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PARSER adds:                                                           │
│  └── sections: [{name, content, page_number}, ...]                     │
│                                                                         │
│  ANALYZER adds:                                                         │
│  ├── requirements: [{id, description, category, priority, specs}, ...] │
│  ├── project_summary: "Brief description of tender"                    │
│  ├── budget_info: "Budget constraints if mentioned"                    │
│  └── timeline_info: "Delivery timeline requirements"                   │
│                                                                         │
│  MATCHER adds:                                                          │
│  └── requirement_matches: [{                                           │
│        requirement_id, requirement_description,                         │
│        matches: [{product_id, name, score, matched_specs, price}],     │
│        best_match: {product details},                                  │
│        coverage_score                                                   │
│      }, ...]                                                           │
│                                                                         │
│  SCORER adds:                                                           │
│  ├── overall_score: 0-100                                              │
│  ├── scoring_breakdown: {category: {score, max, weighted_score, notes}}│
│  └── recommendations: ["PURSUE: ...", "GAP: ...", ...]                │
│                                                                         │
│  RESPONSE adds:                                                         │
│  ├── proposal_summary: "Markdown formatted summary"                    │
│  ├── technical_response: "Markdown with compliance matrix"             │
│  └── commercial_response: "Markdown with pricing table"                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Error Handling & Fallbacks

Each agent implements a consistent error handling pattern:

```python
try:
    # LLM call
    response = llm.invoke(messages)
    parsed = extract_json_from_response(response.content)
    return success_state

except json.JSONDecodeError as e:
    # JSON parsing failed - log raw response for debugging
    log_error(f"JSON Parse Error: {e}")
    log_warning("Raw LLM response (first 500 chars):")
    return fallback_state

except Exception as e:
    # Other errors
    log_error(f"Error: {e}")
    return error_state
```

**Robust JSON Extraction (`json_utils.py`):**
1. Extract from markdown code blocks (\`\`\`json)
2. Fix trailing commas
3. Escape unescaped newlines in strings
4. Repair truncated JSON (add missing brackets)
5. Multiple fallback strategies

---


  