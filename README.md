# AICTE Document Validation System (Prototype Skeleton)

An AI-powered, multilingual system that validates institution approval applications, ranks them by risk, drafts deficiency reports, and allows institutions to fix and recheck.

This prototype is designed for rapid hackathon demonstration with synthetic data and a modular pipeline architecture.

---

## Project Structure

```
aicte-validator/
  backend/
    app/
      __init__.py
      main.py              # FastAPI application, CORS middleware, /health endpoint
      config.py            # Configuration loader using pydantic-settings & .env
      database.py          # SQLAlchemy 2.x engine, SessionLocal, Base, get_db dependency
      models.py            # SQLAlchemy database models & relationships
      schemas.py           # Pydantic v2 validation and response schemas
      audit.py             # log_action() helper writing to audit_logs
      routers/
        __init__.py
        applications.py    # POST /applications, GET /applications/{id}
        officer.py         # GET /officer/queue (stub returning [])
      services/            # Pipeline services package (OCR, rules, scoring)
        __init__.py
    configs/
      document_types/      # YAML document type specs (populated in upcoming steps)
      rules/               # YAML approval rules (populated in upcoming steps)
    storage/
      uploads/             # Uploaded PDF and image files (gitignored)
    tests/
      __init__.py
      test_health.py       # Health check, application creation, and audit logging tests
    seed.py                # Database seeder (3 sample institutions with simulated history)
    requirements.txt       # Pinned compatible backend dependencies
    .env.example           # Sample environment variables
  data/
    synthetic/             # Synthetic documents and test datasets (gitignored)
  README.md
```

---

## Getting Started

### 1. Prerequisites
- **Python 3.11+** (Python 3.11 or 3.12 recommended)
- `pip` package manager

### 2. Set Up a Virtual Environment

Navigate to the `backend` directory:

```bash
cd aicte-validator/backend
```

Create and activate a virtual environment:

**On Windows (PowerShell):**
```powershell
py -3.11 -m venv .venv
# or: python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
# On Windows PowerShell:
Copy-Item .env.example .env

# On Linux / macOS:
cp .env.example .env
```

Settings in `.env`:
- `DATABASE_URL`: Connection string (defaults to SQLite at `./storage/aicte.db`, supports PostgreSQL: `postgresql+psycopg2://user:password@localhost:5432/aicte_db`).
- `UPLOAD_DIR`: Path to upload directory (defaults to `./storage/uploads`).
- `CONFIG_DIR`: Path to rules and configuration directory (defaults to `./configs`).

---

## Database Seeding

Populate the database with sample institutions and simulated inspection histories:

```bash
python seed.py
```

This creates:
1. **Apex Institute of Technology** (Maharashtra) - Clean record with 3 consecutive approved years.
2. **Horizon Institute of Engineering** (Karnataka) - Past rejections, deficiencies, and risk flags.
3. **National Polytechnic College** (Tamil Nadu) - Newly registered institution with no prior history.
4. An initial entry in `audit_logs` logging the database initialization.

---

## Running the Server

Start the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running:
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Running Tests

Run the test suite with `pytest`:

```bash
pytest
```

To run with verbose output:

```bash
pytest -v
```

The test suite validates:
- `GET /health` returns `{"status": "ok"}`
- `POST /applications` registers an application and generates an audit log entry in `AuditLog`
- `GET /applications/{id}` fetches application details by ID
- `GET /officer/queue` returns an empty review queue
- `tests/test_synthetic.py` validates the synthetic data generator: 13 applications, A02 2-document count, A08 duplicate hash check, A06/A07 tampering detection, and Pydantic manifest schema validation.

---

## Synthetic Test Data Generator

The prototype includes a deterministic synthetic dataset generator for simulating approval applications across 13 distinct testing scenarios. All generated documents are strictly fictional and carry the mandatory footer:
`*** SPECIMEN - SYNTHETIC DATA - NOT A VALID OFFICIAL DOCUMENT - FOR PROTOTYPE USE ONLY ***`

### 1. Generating the Dataset

From the `backend` directory, run:

```bash
python -m scripts.generate_synthetic --seed 42
```

Optional arguments:
- `--seed <int>`: Sets random seed for deterministic output (default: `42`).
- `--output-dir <path>`: Destination path (default: `../data/synthetic`).

### 2. Generated Outputs

The generator outputs into `data/synthetic/`:
- `data/synthetic/<app_id>/<doc_type>.png`: High-resolution 1240x1754 px official document image.
- `data/synthetic/<app_id>/<doc_type>.pdf`: Companion PDF copy rendered directly via Pillow.
- `data/synthetic/manifest.json`: Ground truth metadata and expected labels/issues per application.
- `data/synthetic/registry_mock.json`: Simulated government registry of authentic records for verification.
- `data/synthetic/contact_sheet.png`: Master visual grid displaying thumbnails of all 38 documents with colored status badges.

### 3. Application Scenarios (A01 - A13)

| App ID | Scenario | Expected Documents | Expected Labels | Expected Issues |
| :--- | :--- | :--- | :--- | :--- |
| **A01** | Clean baseline application | Fire, Land, Trust (3) | Verified | None |
| **A02** | Missing trust registration | Fire, Land (2) | Verified | `MISSING:trust_registration` |
| **A03** | Fire certificate expired prior to submission | Fire, Land, Trust (3) | Needs Verification | `FIRE-EXPIRY` |
| **A04** | Land area below minimum (6,500 sqm < 10,000 sqm norm) | Fire, Land, Trust (3) | Needs Verification | `LAND-AREA-MIN` |
| **A05** | Owner name mismatch (individual vs educational trust) | Fire, Land, Trust (3) | Inconsistent | `XDOC-OWNER-TRUST` |
| **A06** | Tampered fire certificate (`valid_until` date edited) | Fire, Land, Trust (3) | Possible Tampering | `TAMPERED:valid_until` |
| **A07** | Tampered land document (`area_sqm` edited upward) | Fire, Land, Trust (3) | Possible Tampering | `TAMPERED:area_sqm` |
| **A08** | Duplicate document (reuses exact A01 fire certificate) | Fire, Land, Trust (3) | Inconsistent | `DUPLICATE_OF:A01/fire_safety_certificate` |
| **A09** | Clean application with Hindi (Devanagari) land document | Fire, Land, Trust (3) | Verified | None |
| **A10** | Degraded scan on all documents (rotation, blur, noise, shadow) | Fire, Land, Trust (3) | Needs Verification | `POOR_SCAN:*` |
| **A11** | Multiple high-risk defects (mismatch + expired + tampered) | Fire, Land, Trust (3) | Possible Tampering | `XDOC-OWNER-TRUST`, `FIRE-EXPIRY`, `TAMPERED:area_sqm` |
| **A12** | Benign name variation (e.g. "Shri Sai" vs "Sri Sai" vs "Shree Sai") | Fire, Land, Trust (3) | Verified | None |
| **A13** | Missing QR code and omitted from registry mock | Fire, Land, Trust (3) | Needs Verification | `MISSING_QR:*`, `REGISTRY_UNAVAILABLE:*` |

### 4. Font Support (English & Hindi)
- **English**: Uses Arial or system sans-serif fonts.
- **Hindi (Devanagari)**: The generator checks system font paths first (e.g. `Nirmala.ttc`, `mangal.ttf`) or loads `NotoSansDevanagari-Regular.ttf` from `backend/assets/fonts/`. If unavailable, it falls back gracefully with a warning to standard Latin rendering.

---

## Document Ingestion & Extraction Pipeline

The document validation pipeline processes uploaded files (PDF, PNG, JPG) through six sequential stages:

```
[Uploaded File]
       │
       ▼
1. Preprocessing (OpenCV: Grayscale, Deskew, Denoise, CLAHE Adaptive Contrast)
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
2. Dual-Engine OCR (eng+hin)      3. QR Code Decoding
   - Native C++ Tesseract (tesserocr)  - Multi-scale detection
   - Fallback: PaddleOCR               - Sharpened ROI parsing
   - Script detection (en, hi, mixed)
       │                                 │
       └────────────────┬────────────────┘
                        ▼
4. Document Classification (Keyword density + Filename hints)
   - fire_safety_certificate | land_document | trust_registration
                        │
                        ▼
5. Field Extraction (Provider Strategy Pattern)
   - RulesExtractor (Default, zero-cost, rapidfuzz fuzzy regex)
   - ApiLlmExtractor (OpenAI, DeepSeek, vLLM via chat completions)
   - LocalLlmExtractor (Local Ollama / LM Studio instances)
                        │
                        ▼
6. Normalization & Standardization
   - Dates -> ISO-8601 (YYYY-MM-DD)
   - Quantities -> Metric (sqm, acres, hectares converted with unit preserved)
   - Names -> Honorific stripping & Indic transliteration (sanscript ITRANS)
   - IDs -> Uppercase alphanumerics
                        │
                        ▼
[Database Persistence & Audit Trail] (Documents, ExtractedFields, AuditLogs)
```

---

## OCR Engine & Multilingual Setup

The system prioritizes fast native C++ Tesseract bindings (`tesserocr`), falls back to `pytesseract`, and finally to `PaddleOCR` if Tesseract is not available.

### Installing Tesseract OCR & Hindi Language Data

#### Windows
1. **Option A (Pre-packaged Python Wheel - Recommended)**:
   The project dependencies include `tesserocr` with pre-compiled Tesseract 5.5 DLLs. Simply ensure language files (`eng.traineddata`, `hin.traineddata`, `osd.traineddata`) are located in `backend/tessdata/` or set `TESSDATA_PREFIX`:
   ```powershell
   $env:TESSDATA_PREFIX = "c:\Users\...\aicte-validator\backend\tessdata"
   ```
2. **Option B (UB-Mannheim Installer)**:
   - Download the Windows installer from [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
   - During setup, check **Additional script data -> Devanagari script** and **Additional language data -> Hindi**.
   - Add Tesseract to your PATH or set `TESSERACT_CMD` in `.env`:
     ```env
     TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
     ```

#### Linux (Ubuntu / Debian)
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-hin libtesseract-dev libleptonica-dev pkg-config
```

#### macOS (Homebrew)
```bash
brew install tesseract tesseract-lang
```

---

## Field Extraction Providers

Configure the extractor in `backend/.env` using the `EXTRACTOR` variable:

```env
# Available choices: rules, llm_api, llm_local
EXTRACTOR=rules

# Optional LLM settings (for llm_api or llm_local)
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1

# Verification threshold
CONFIDENCE_THRESHOLD=0.70
```

- **`rules` (Default)**: Rapid, deterministic rule-based extractor using YAML field definitions (`backend/configs/document_types/*.yaml`), fuzzy keyword matching with `rapidfuzz`, and strict type validation.
- **`llm_api`**: Calls OpenAI-compatible REST APIs. Prompts treat OCR output strictly as **untrusted data**, immune to prompt injection, returning structured JSON with an automatic fallback to `RulesExtractor` on network/parsing failure.
- **`llm_local`**: Connects to locally running LLM engines such as Ollama (`http://localhost:11434/v1`) or LM Studio.

---

## Document REST Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/applications/{id}/documents` | Upload a document (multipart/form-data: `file`, optional `document_type`) |
| `POST` | `/documents/{id}/process` | Trigger OCR, QR decoding, classification, and field extraction for a document |
| `GET` | `/documents/{id}` | Retrieve document metadata, OCR confidence, detected language, QR text, and all extracted fields |
| `POST` | `/applications/{id}/process-all` | Run end-to-end ingestion and extraction for every document in an application |
| `GET` | `/applications/{id}/completeness` | Pre-submission completeness check returning present, missing, and duplicate documents |
| `POST` | `/applications/{id}/validate` | Process pending documents, run completeness check, and execute all deterministic rules |
| `GET` | `/applications/{id}/results` | Return documents with extracted fields, completeness report, and rule results sorted by severity |
| `GET` | `/admin/config` | List all loaded document types, application types, rules, and versions |
| `POST` | `/admin/config/reload` | Reload all YAML configurations dynamically without server restart |

---

## Completeness Check & Deterministic Rules Engine

The system validates institutional approval applications using a safe, deterministic, per-document rules engine powered by `simpleeval`. Pass/fail outcomes are determined strictly by deterministic logic—never by an LLM.

> [!IMPORTANT]
> **Prototype Disclaimer:** All thresholds (e.g. `min_area_sqm: 10000.0`), norms, and clause references (e.g., `Handbook clause: <to be mapped to the current handbook edition>`) are strictly **illustrative prototype values** for hackathon demonstration, not official AICTE Approval Process regulations.

### 1. Safety & The `not_evaluable` Outcome
- **No Python Internals:** The expression evaluator restricts all execution to a tiny set of helper functions (`present(x)`, `days_between(a, b)`, `len(x)`). Imports, attribute walking (`__class__`), file access, and `eval()` are blocked at the syntax parser level.
- **Handling Bad OCR:** If a field required by a rule is missing, null, or flagged `needs_verification` (due to low OCR confidence or scan noise), the outcome is marked **`not_evaluable`** (not fail, not pass) with a specific explanation. This prevents bad scans from falsely rejecting compliant institutions.

---

## Rule Configuration Format & Adding Rules

Rules are defined in YAML files located in `backend/configs/rules/<document_type>.yaml`.

### Complete Rule File Example (`backend/configs/rules/land_document.yaml`)

```yaml
# ==============================================================================
# AICTE Rule Specifications: Land Document (PROTOTYPE SPECIFICATION)
# IMPORTANT: All thresholds, norms, and clauses are strictly ILLUSTRATIVE prototype
# values for hackathon demonstration, not official AICTE Approval Process norms.
# ==============================================================================

rules:
  - id: LAND-AREA-MIN
    document_type: land_document
    description: "Total land area must meet or exceed minimum AICTE norm for institution type"
    condition: "area_sqm >= app.min_area_sqm"
    severity: high
    message: "Total land area {area_sqm} sq.m is below the required norm of {app.min_area_sqm} sq.m."
    clause: "Handbook clause: <to be mapped to the current handbook edition>"
    required_fields:
      - area_sqm
    version: "1.0.0"
    applies_to:          # Optional: list of application types this rule applies to
      - new_institution

  - id: LAND-REG-DATE-NOT-FUTURE
    document_type: land_document
    description: "Land deed registration date cannot be in the future relative to application submission date"
    condition: "registration_date <= app.submission_date"
    severity: medium
    message: "Land registration date {registration_date} is after application submission date {app.submission_date}."
    clause: "Handbook clause: <to be mapped to the current handbook edition>"
    required_fields:
      - registration_date
    version: "1.0.0"
```

### How to Add a New Rule
1. Open or create `backend/configs/rules/<doc_type>.yaml`.
2. Add an entry under `rules:` with:
   - `id`: Unique identifier (e.g. `FIRE-EXPIRY`).
   - `document_type`: Must match a known document type in `backend/configs/document_types/`.
   - `description`: Plain-English explanation.
   - `condition`: Expression string evaluating to boolean. Available context includes field names, `app` parameters (e.g. `app.submission_date`), and helper functions (`present()`, `days_between()`, `len()`).
   - `severity`: `"low"`, `"medium"`, or `"high"`.
   - `message`: Template string formatting actual values (e.g. `"{area_sqm}"`).
   - `clause`: Clause placeholder reference.
   - `required_fields`: List of fields that must be present and verified for the rule to evaluate.
   - `version`: Version string (e.g. `"1.0.0"`).
   - `applies_to` (optional): Filter to specific application types.
3. Validate the rule using the CLI validator:
   ```bash
   python -m scripts.validate_configs
   ```

---

## Adding a New Application Type (Configuration-Only)

Adding application types requires zero code changes. Edit `backend/configs/application_types.yaml`:

```yaml
application_types:
  extension_of_approval:
    name: "Extension of Approval (EoA)"
    code: "extension_of_approval"
    description: "Annual continuation of approval for existing operational institutions."
    required_documents:
      - fire_safety_certificate
      - trust_registration
    parameters:
      certificate_min_validity_days: 0
```

---

## Cross-Document Consistency Checker (Core Feature 1)

The Cross-Document Consistency Checker performs deterministic, cross-referencing validation between independent documents (and application metadata) submitted by an applicant institution.

Outcomes are generated strictly by deterministic algorithms (string normalization, phonetic collapsing, edit-distance bounds, and fuzzy token matching)—**never by an LLM**. Every finding displays the compared values side by side with source documents and full transformation steps so an officer can audit exactly how a score was reached.

### 1. Matching Score Computation & Pipeline

The matching engine (`backend/app/services/matching.py`) executes a multi-stage normalization and scoring pipeline:

1. **Base Transliteration & Cleaning:**
   - Devanagari Hindi characters are transliterated to Latin script via ITRANS (`indic-transliteration`).
   - English and Hindi honorifics (`Dr.`, `Prof.`, `Shri`, `Smt.`, `श्री`, `श्रीमती`) are stripped.
   - Punctuation, multiple whitespace, and OCR misreads (e.g. `¢` -> `c`, stray digit tokens like `00`) are cleaned.
2. **Legal Suffix Stripping:**
   - Configurable legal entity words (`registered`, `regd`, `ltd`, `pvt`, `limited`, `inc`, `llc`) are stripped.
3. **Phonetic & Romanization Collapsing:**
   - Collapses common Indian English prefix variants (`shri`/`shree`/`sree` -> `sri`).
   - Collapses phonetic spelling variations (`w` -> `v`, `ph` -> `f`, doubled vowels `ee` -> `i`, `oo` -> `u`, `aa` -> `a`).
   - Resolves transliterated aliases (`vaniyaka` / `vinayaka` -> `vinayak`).
4. **Synonym & Stem Canonicalization:**
   - Stems are canonicalized using configurable groups in `name_normalization.yaml` (e.g. `educational` / `ejukeshana` -> `education`; `samiti` / `sabha` / `sanstha` -> `society`; `nyas` / `trasta` / `foundation` -> `trust`; `academy` / `sansthan` / `samsthana` -> `institution`).
5. **RapidFuzz Scoring Formula:**
   ```python
   token_score = max(fuzz.token_set_ratio(n1, n2), fuzz.token_sort_ratio(n1, n2))
   char_score  = fuzz.ratio(n1.replace(' ', ''), n2.replace(' ', ''))
   base_score  = round(0.65 * token_score + 0.35 * char_score, 2)
   ```
6. **False-Match Guardrail (Distinct Personal Names):**
   - When comparing name fields, if the two token sets differ by a non-synonym token (e.g., `Ramesh Kumar` vs `Suresh Kumar`), standard `token_set_ratio` could artificially inflate the score.
   - The engine checks the Levenshtein distance between differing tokens. If differing tokens exceed `max_typo_dist` (1), the score is strictly capped at `partial_min - 1.0` (e.g. 69.0), guaranteeing a **conflict** outcome.
7. **Status Determination:**
   - `score >= match_min` (default: 85.0) -> `match`
   - `partial_min <= score < match_min` (default: 70.0) -> `partial`
   - `score < partial_min` -> `conflict`
   - If either side is missing or flagged `needs_verification` (confidence < 0.60) -> `not_evaluable` (avoids false conflicts from OCR limitations).

### 2. Consistency Rules Schema (`consistency_rules.yaml`)

Comparisons are defined strictly as configuration in `backend/configs/consistency/consistency_rules.yaml`:

```yaml
consistency_rules:
  - id: XDOC-OWNER-TRUST
    description: "Land document owner name must match trust name or any governing trustee"
    kind: name                                   # name | id | date_order | address
    left: land_document.owner_name               # doc_type.field or application.institution_name
    right:                                       # single target or list of targets (for any_of)
      - trust_registration.trust_name
      - trust_registration.trustee_names
    relation: any_of                             # equals | any_of | date_before_or_equal
    thresholds:
      match_min: 85
      partial_min: 70
    severity_on_conflict: high
    severity_on_partial: medium
    message_templates:
      match: "Land owner '{left_value}' matches sponsoring trust entity '{right_value}' (score: {score:.1f})."
      partial: "Land owner '{left_value}' partially matches sponsoring trust entity '{right_value}' (score: {score:.1f}). Officer review recommended."
      conflict: "Land owner '{left_value}' does not match sponsoring trust or any trustee in '{right_value}' (score: {score:.1f}). Land title must vest with sponsoring trust."
    clause: "Handbook clause: <to be mapped to the current handbook edition>"
    version: "1.0.0"
```

### 3. Adding a New Consistency Rule (Configuration-Only)

To add a new cross-document rule (for example, verifying plot number across multiple certificates):
1. Open `backend/configs/consistency/consistency_rules.yaml`.
2. Add a new rule under `consistency_rules`:
   ```yaml
   - id: XDOC-PLOT-NUMBER
     description: "Land plot number must match fire safety site plot number"
     kind: id
     left: land_document.plot_number
     right: fire_safety_certificate.plot_number
     relation: equals
     severity_on_conflict: high
     severity_on_partial: medium
     message_templates:
       match: "Plot number '{left_value}' verified across documents."
       partial: "Plot number minor difference: '{left_value}' vs '{right_value}'."
       conflict: "Plot number discrepancy: '{left_value}' does not match '{right_value}'."
     clause: "Handbook clause: <to be mapped to the current handbook edition>"
     version: "1.0.0"
   ```
3. Run the config validator CLI:
   ```bash
   python -m scripts.validate_configs
   ```
   The validator will automatically verify that the target document types and field names exist and that the relation is supported.

---

## Validation & Evaluation CLI Scripts

### 1. Validate All YAML Configurations
Runs an automated consistency check across document types, application types, parameters, rules, and cross-document consistency configurations:

```bash
cd aicte-validator/backend
python -m scripts.validate_configs
```

### 2. Sweep & Tune Consistency Matching Thresholds
Performs an empirical grid sweep over `match_min` and `partial_min` on 43 hand-labelled name pairs in `data/name_pairs.csv` and outputs precision, recall, and error breakdown:

```bash
python -m scripts.tune_thresholds
```
*Output report saved to `backend/data/threshold_report.md`.*

### 3. Evaluate Cross-Document Consistency Against Ground Truth
Runs end-to-end OCR extraction, per-document rules, and cross-document consistency checks on all 13 synthetic applications from `manifest.json`:

```bash
python -m scripts.evaluate_consistency
```
*Output report saved to `data/synthetic/consistency_report.md`.*

### 4. Evaluate Extraction Benchmark
Runs OCR and field extraction across all 38 synthetic documents:

`ash
python -m scripts.evaluate_extraction
`

### 5. Evaluate Deterministic Rules & Completeness
Evaluates per-document rules and completeness findings against ground-truth manifest expectations:

`ash
python -m scripts.evaluate_rules
`
*Output report saved to data/synthetic/rules_report.md.*

### 6. Evaluate Document Authentication & Forensics
Evaluates all 5 authentication checks (duplicates, metadata, classical image forensics, QR verification, mock registry) against ground truth on all 13 synthetic applications:

```bash
python -m scripts.evaluate_authentication
```
*Output report saved to `data/synthetic/authentication_report.md`.*
*Annotated forensic imagery stored in `data/synthetic/tampered_annotated/`.*

---

## Document Authentication & Forensics (Core Feature 2)

> [!IMPORTANT]
> **PROBABILITY & SIGNALS DISCLAIMER**
> Image forensics (ELA, copy-move detection, noise inconsistency) and metadata checks yield **PROBABILITIES and SIGNALS, not legal proof of fraud**.
> Every metric is strictly named `tampering_score` or `signal`, never "confidence of fraud".
> A **human verification officer always decides** the final approval verdict.
> All application data is synthetic, the registry is a MOCK, and all thresholds are illustrative prototype values maintained in configuration files. Nothing here is decided by an LLM.

### 1. Authentication Checks Architecture

Every document submitted to an application undergoes five independent, deterministic checks orchestrated by `app.services.auth.run.run_authentication`:

| Check Type | Service Module | Primary Techniques & Signals | Status Outcomes |
| :--- | :--- | :--- | :--- |
| **Duplicates** | `app.services.auth.duplicates` | • SHA-256 exact match<br>• 256-bit body pHash Hamming distance (`imagehash`)<br>• Normalized certificate/registration ID reuse | `ok`, `suspicious` (carries references to earlier document) |
| **Metadata** | `app.services.auth.metadata` | • PyMuPDF & EXIF parser<br>• `ModDate` vs `CreationDate` gap (`metadata_max_gap_days`)<br>• Image editor signatures (`photoshop`, `gimp`, `canva`, etc.)<br>• Post-dated creation | `ok`, `suspicious`, `unavailable` |
| **Tampering Forensics** | `app.services.auth.forensics` | • Error Level Analysis (ELA) with robust baseline block spread<br>• ORB keypoint copy-move matching (excludes repetitive text rows/stamps)<br>• Local Laplacian noise inconsistency<br>• Degraded scan guard (`global_blur` + noise uniformity) | `ok`, `suspicious`, `high_suspicion`, `low_quality_scan` |
| **QR Verification** | `app.services.auth.qr_check` | • OpenCV multi-scale QR decoding<br>• Normalized payload ID vs extracted field ID comparison | `match`, `mismatch`, `absent` (`unavailable`), `unreadable` |
| **Mock Registry** | `app.services.auth.registry` | • Modular `RegistryClient` interface<br>• Queries government registry mock (`data/synthetic/registry_mock.json`)<br>• Compares `valid_until`, `area_sqm`, `owner_name`, `plot_number` | `match`, `mismatch`, `not_found`, `unavailable` |

### 2. Guardrails Against False Alarms

- **Resubmission & Parent Application Exemption:** Documents in applications linked via `parent_application_id` (drafts or corrected resubmissions) are never flagged as duplicate copies of the original, enabling institutions to fix deficiencies and recheck.
- **Earlier-Document Prioritization:** When an exact duplicate is found across separate institutions (e.g. A08 copying A01's fire safety certificate), the original earlier document is marked clean, while only the later submission is flagged with a pointer to the earlier record.
- **Poor-Scan Degradation Guard:** Low-quality scans (such as A10, which exhibit high blur and uniform sensor noise) are guarded against false forensic flags. The system calculates global Laplacian variance and suppresses forensic scores, reporting `low_quality_scan` instead of `suspicious`.
- **Repetitive Table & Stamp Exemption:** Copy-move keypoint matching filters out vertical column repeats common in standard legal document tables and masks official seal/stamp zones.
- **Graceful Absence Handling:** If a document lacks an embedded QR code (e.g. A13), the outcome is reported as `absent` with status `unavailable`, never as a system error or validation failure.

### 3. RegistryClient Interface

The system accesses government registries through an extensible abstract interface:

```python
class RegistryClient(ABC):
    @abstractmethod
    def lookup(self, doc_type: str, number: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Lookup an official record by document type and unique identifier.
        Returns: (record_dict or None, is_service_available)
        """
```

The current implementation (`MockRegistryClient`) loads `data/synthetic/registry_mock.json`. To integrate real production state or national databases (e.g. DigiLocker, e-District, Land Records API), a developer simply implements this interface and replaces the factory in `app.services.auth.registry`.

Registry connectivity can be toggled using `REGISTRY_ENABLED=true/false` in `.env`. When disabled, all registry lookups gracefully report status `unavailable` for simulation and offline testing.

### 4. Authentication Configuration (`auth_config.yaml`)

All thresholds and parameters are defined in `backend/configs/authentication/auth_config.yaml` as illustrative prototype values:

```yaml
# Error Level Analysis
ela_quality: 90
ela_block_size: 32
ela_region_score_suspicious: 0.35
ela_region_score_high: 0.65

# Copy-Move Detection
copy_move_min_matches: 10
copy_move_min_distance_px: 60

# Noise Inconsistency
noise_inconsistency_threshold: 0.40

# Perceptual Hashing
phash_hamming_near_duplicate: 1

# PDF Metadata
metadata_max_gap_days: 1
suspicious_producers:
  - "photoshop"
  - "gimp"
  - "canva"
  - "paint"
  - "image editor"
```
