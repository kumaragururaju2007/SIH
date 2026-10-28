# Backend Integration & Gaps Report (BACKEND_GAPS.md)

This document tracks backend API characteristics, missing endpoints or parameter variations relative to the specification, and how the frontend API adapter mocks or adapts them.

---

### 1. Asynchronous Validation Progress Endpoint
- **Specification:**
  The frontend requires a live progress timeline displaying six validation stages:
  1. Preprocessing & Multilingual OCR (eng+hin)
  2. Document Classification
  3. Deterministic Compliance Rules (`simpleeval`)
  4. Cross-Document Consistency (phonetic, transliteration, Levenshtein token match)
  5. Authentication Forensics (ELA, copy-move, QR check, mock registry)
  6. Explainable Risk Scoring (0-100, risk bands, top contributing factors)
  The specification requests polling a status endpoint every 2 seconds or mocking it if missing.
- **Backend Current State:**
  `/applications/{id}/validate` and `/applications/{id}/submit` are synchronous FastAPI endpoints that execute the pipeline and return the complete payload upon completion.
- **Frontend Resolution:**
  The API adapter (`src/services/api.ts`) implements `simulateValidationProgress()`. It invokes the real backend validation endpoint while driving an asynchronous stage-by-stage progress observer with realistic stage transitions (180ms - 350ms per stage). This gives the user immediate visual feedback of each scrutiny engine phase while retaining 100% real backend output.

---

### 2. Application Creation with Planned Submission Date
- **Specification:**
  Institution "New Application" modal prompts for application type and planned submission date.
- **Backend Current State:**
  `ApplicationCreate` schema in `app/schemas.py` accepts `institution_id`, `application_type`, and optional `parent_application_id`. `submission_date` is stamped when officially submitted via `/applications/{id}/submit`.
- **Frontend Resolution:**
  The frontend accepts the user-selected submission date in the modal, persists it locally for pre-submission display, and passes `application_type` and `institution_id` to `POST /applications`. Upon clicking "Submit Officially", the backend sets the official submission date.

---

### 3. Deficiency Report Auto-Generation on Officer Detail
- **Specification:**
  Officer deficiency report tab allows generating, inline-editing wording, approving, and sending deficiency reports.
- **Backend Current State:**
  Backend provides `/officer/applications/{id}/deficiency/generate`, `PUT /officer/applications/{id}/deficiency`, `/approve`, and `/send`. However, when an application has not yet had a deficiency report created in the database, `get_officer_application_detail` returns `deficiency_report: null`.
- **Frontend Resolution:**
  The frontend checks if `deficiency_report` is null. If null, it derives a structured draft report from the application's active rule failures, missing document findings, and consistency conflicts, allowing the officer to immediately click "Generate Official Report" or edit inline.

---

### 4. Hindi Field Transliteration Rendering
- **Specification:**
  Hindi text must render with correct Devanagari font shaping in field values and deficiency reports.
- **Backend Current State:**
  Backend successfully extracts and normalizes Hindi fields (such as land deed entries in A09/A11).
- **Frontend Resolution:**
  The frontend loads `@fontsource/noto-sans-devanagari` locally and applies the `.lang-hi` CSS class and Devanagari font stack to ensure ligatures and vowel signs (matras) render crisply across modern browsers without relying on external CDNs.

---

### 5. Document Deletion in Draft Mode
- **Specification:**
  Applicant institutions can replace and remove uploaded documents while an application is in Draft mode.
- **Backend Current State:**
  Backend provides `POST /applications/{id}/documents` to upload, and replaces deeds during draft resubmissions, but does not expose an explicit `DELETE /documents/{id}` REST route.
- **Frontend Resolution:**
  The API adapter (`src/services/api.ts`) implements `deleteDocument(docId)`. It attempts the HTTP DELETE call and cleanly updates the client state and completeness checklist so the institution can remove uploaded files and return the document requirement to missing status before final submission.

---

### 6. Dynamic Application Type Listing
- **Specification:**
  The "New Application" modal reads available application types dynamically from the configuration list.
- **Backend Current State:**
  Backend provides `GET /admin/config` containing `application_types` configuration dictionary.
- **Frontend Resolution:**
  The frontend queries `api.getConfig()` to dynamically populate application types (e.g. `new_institute`, `extension_of_approval`, `increase_intake`, `closure`) with fallback to standard Approval Process Handbook types if config endpoint is unavailable.
