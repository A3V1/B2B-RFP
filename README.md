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

