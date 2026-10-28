# DocValidate Frontend (Smart India Hackathon Prototype)

Institutional document validation, compliance checking, explainable risk-ranking, and deficiency remediation for AICTE statutory approvals.

---

## 🚀 Quick Start & Deployment Guide

### Environment Configuration
The frontend communicates with the AICTE Scrutiny Backend API exclusively via `VITE_API_URL`.

Create a `.env` file in the `frontend/` directory (or set the environment variable in your deployment dashboard):
```env
VITE_API_URL=http://localhost:8000
```

### Build & Run Commands
```bash
# 1. Install dependencies
npm install

# 2. Start local development server
npm run dev

# 3. Production build (TypeScript validation + Vite bundle)
npm run build

# 4. Preview production build locally
npm run preview
```

### Static Site Hosting (Render / Netlify / Vercel)
- **Build Command:** `npm install && npm run build`
- **Publish Directory:** `dist`
- **Single Page Application Rewrite:** Handled automatically via `public/_redirects` (`/* /index.html 200`).

---

## 🏛 Design System & Specimen Notice
- **Design Tokens:** Strict government digital service standard: light theme, generous whitespace, high-contrast typography (IBM Plex Sans, IBM Plex Mono, Noto Sans Devanagari), ink-blue `#1E3A5F` and reserved saffron `#C77700` primary CTA.
- **Prototype Authorization Notice:** Real authentication (DigiLocker, e-Pramaan) is planned for future scope. The prototype uses client-side demo account credentials (`demo123`) with role enforcement (`institution`, `officer`, `admin`, `audit`), session timeouts, and route guards.
- **Explainability:** Risk scores are illustrative; forensic signals represent algorithmic probabilities; final verdicts are strictly reserved for human scrutiny officers.
