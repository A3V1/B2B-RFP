# B2B RFP Automation System

This repository contains a FastAPI-based RFP (Request for Proposal) automation MVP that processes RFP documents, extracts requirements, and matches them with components from a product catalog.

## Project Status

**✅ Completed Components:**

### 1. Database Setup
- PostgreSQL database configured and connected
- SQLAlchemy ORM models for `RFP` and `Component` entities
- Database tables created with proper schema:
  - `rfps` table: stores uploaded RFP documents with extracted text
  - `components` table: stores product/service catalog (name, description, keywords, price)

### 2. Data Seeding
- Created `data/components.csv` with 100 sample components
- Implemented `scripts/seed_db.py` to populate the database
- Fixed schema mismatch (added `keywords` column) using `scripts/reset_components_table.py`
- Successfully seeded 100 components into PostgreSQL

### 3. Document Processing
- PDF and DOCX text extraction implemented in `app/services/extractor.py`
- Features:
  - Clean text extraction with noise filtering
  - Header/footer removal for PDFs
  - Table extraction from DOCX files
  - Smart line cleaning and formatting

### 4. Web Upload Interface
- Beautiful, modern HTML/CSS/JavaScript frontend (`static/index.html`)
- Features:
  - Drag-and-drop file upload
  - Click to browse files
  - Real-time file validation (PDF/DOCX only)
  - Automatic text extraction on upload
  - Preview extracted text (first 1000 characters)
  - Download full extracted text as `.txt` file
  - Loading indicators and error handling
  - Responsive design

### 5. API Endpoints
- FastAPI application structure in place
- Implemented endpoints:
  - `GET /` - Serves the web upload interface
  - `POST /api/v1/upload` - Upload RFP documents (PDF/DOCX)
  - `POST /api/v1/extract` - Extract text from uploaded RFPs
  - `GET /docs` - Interactive API documentation (Swagger UI)
  - `GET /redoc` - Alternative API documentation (ReDoc)

### 6. Project Structure
```
app/
├── db/               # Database models, CRUD operations
├── services/         # Business logic (text extraction)
├── v1/              # API routes (v1)
├── config.py        # Configuration management
└── main.py          # FastAPI application entry point

static/
└── index.html       # Web upload interface (HTML/CSS/JS)

data/
└── components.csv   # Product catalog seed data

scripts/
├── seed_db.py                    # Database seeding script
├── reset_components_table.py    # Schema migration helper
├── extract_sample.py            # Test extraction locally
└── create_db.sql               # Database creation SQL

samples/sample_rfps/  # Sample RFP documents for testing
uploads/              # Uploaded RFP files storage
proposals/            # Generated proposals storage
outputs/              # Extracted text outputs
```

## What's Missing (Next Steps)

1. **Component Matching Engine** - Core logic to match RFP requirements to components
2. **Proposal Generation** - Create proposals based on matched components
3. **Component Query Endpoints** - Search and retrieve components via API
4. **RFP Analysis Agent** - Parse extracted text to identify requirements
5. **LangGraph Workflow** - Orchestrate the end-to-end pipeline
6. **Background Job Processing** - Async processing with job queue
7. **HITL (Human-in-the-Loop)** - Review and intervention capabilities

## Running PDF/DOCX extraction locally

Quick steps to test extraction on the included sample RFP PDFs.

1. Create and activate a virtual environment (Windows cmd):

```cmd
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```cmd
pip install -r requirements.txt
```

3. Run the sample extraction script (will process PDFs in `samples/sample_rfps` and write `.txt` files to `outputs/extracted`):

```cmd
python scripts\extract_sample.py
```

You can change the input folder or output folder:

```cmd
python scripts\extract_sample.py --samples samples/sample_rfps --out outputs\extracted
```

4. (Optional) Run the FastAPI app and use the upload/extract endpoints:

```cmd
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then POST a file to `http://127.0.0.1:8000/api/v1/upload` and call `/api/v1/extract` with the returned `rfp_id`.

## Setup Instructions (Windows)

### Prerequisites
- Python 3.8+
- PostgreSQL installed and running
- `psql` available on PATH

### Step-by-Step Setup

**1. Create PostgreSQL Database**

Edit `scripts\create_db.sql` to set secure credentials, then run:

```cmd
psql -U postgres -f scripts\create_db.sql
```

This creates the `rfp_db` database and `rfp_user` user.

**2. Configure Database Connection**

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg2://rfp_user:rfp_password@localhost:5432/rfp_db
```

Or set as an environment variable:

```cmd
set DATABASE_URL=postgresql+psycopg2://rfp_user:rfp_password@localhost:5432/rfp_db
```

**3. Set Up Python Environment**

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**4. Initialize Database Schema**

If you have an existing `components` table without the `keywords` column, run:

```cmd
python scripts\reset_components_table.py
```

This drops and recreates the table with the correct schema.

**5. Seed the Database**

```cmd
python scripts\seed_db.py
```

This loads 100 components from `data/components.csv` into the database.

**6. Verify Database**

Check that the data was loaded:

```cmd
psql -U rfp_user -d rfp_db -c "SELECT COUNT(*) FROM components;"
```

You should see 100 rows.

**7. Start the API Server**

```cmd
uvicorn app.main:app --reload
```

The server will be available at `http://127.0.0.1:8000`

**8. Use the Web Interface**

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

You'll see a modern upload interface where you can:
- **Drag and drop** PDF or DOCX files, or **click to browse**
- Files are automatically uploaded and text is extracted
- View the **RFP ID** (unique identifier for the document)
- See a **preview** of the extracted text (first 1000 characters)
- **Download** the full extracted text as a `.txt` file
- Upload multiple documents (click "Upload Another")

### Alternative: API Testing via Command Line

**Upload an RFP:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/upload" \
  -F "file=@samples/sample_rfps/Sample-RFP.pdf"
```

**Extract text from RFP:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/extract?rfp_id=<rfp_id>"
```

### Alternative: API Testing via Swagger UI

Visit `http://127.0.0.1:8000/docs` for interactive API documentation where you can test all endpoints directly in your browser.

### Troubleshooting

**Issue: `column "keywords" does not exist`**
- Run: `python scripts\reset_components_table.py` then `python scripts\seed_db.py`

**Issue: Database connection failed**
- Verify PostgreSQL is running
- Check `.env` file has correct credentials
- Test connection: `psql -U rfp_user -d rfp_db`

### Notes

- The project defaults to SQLite if `DATABASE_URL` is not set
- Uploaded files are stored in `uploads/` (configurable in `app/config.py`)
- Sample RFP documents are available in `samples/sample_rfps/`

## Development Roadmap

### Phase 1: Foundation (✅ Completed)
- [x] Database setup with PostgreSQL
- [x] SQLAlchemy models for RFP and Component
- [x] Seed data (100 components)
- [x] Document text extraction (PDF/DOCX)
- [x] API endpoints (upload, extract)
- [x] Web upload interface with drag-and-drop
- [x] Automatic text extraction and preview
- [x] Download extracted text functionality

### Phase 2: Core Intelligence (🚧 In Progress)
- [ ] Requirement extraction agent (LLM-based)
- [ ] Component matching engine (TF-IDF → embeddings)
- [ ] Pricing calculation logic
- [ ] Proposal generation agent

### Phase 3: Workflow Orchestration
- [ ] LangGraph workflow integration
- [ ] State management for multi-step processing
- [ ] Error handling and retry logic
- [ ] Agent execution tracking

### Phase 4: Job Processing
- [ ] Background job queue
- [ ] Job status tracking (pending/running/completed/failed)
- [ ] Durable execution with DB persistence
- [ ] Pause/resume capability

### Phase 5: Human-in-the-Loop (HITL)
- [ ] Confidence scoring for agent outputs
- [ ] Review/approval workflow
- [ ] Override and intervention API
- [ ] Quality assurance checkpoints

### Phase 6: Advanced Features
- [ ] Vector embeddings with pgvector
- [ ] Semantic search for components
- [ ] LLM integration (OpenAI/Anthropic)
- [ ] Local LLM option (optional)

### Phase 7: Production Readiness
- [ ] Comprehensive unit tests
- [ ] Integration tests
- [ ] End-to-end test suite
- [ ] Logging and monitoring
- [ ] Performance optimization

## Technology Stack

- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Document Processing:** pdfplumber, python-docx
- **Workflow:** LangGraph (planned)
- **LLM:** OpenAI/Anthropic APIs (planned)
- **Embeddings:** sentence-transformers (planned)

## Contributing

This is an MVP project. Current focus is on building core functionality before adding features.

## License

[Add your license here]
