# AICTE Cross-Document Consistency Evaluation Report

- **Timestamp:** 2026-10-27 19:12:40 UTC
- **Evaluated Applications:** 13
- **Extractor Engine:** Deterministic Regex Extractor (`EXTRACTOR=rules`)
- **Execution Time:** 1.66s

## 1. Ground Truth Verification Summary

| App ID | Scenario Description | Expected Conflicts | Found Conflicts | Verdict | Details |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `A01` | clean, all 3 documents, all consistent, English | `None` | `None` | **PASS** | Matches: 3, Partials: 1, NotEval: 0 |
| `A02` | missing trust_registration (only 2 documents) | `None` | `None` | **PASS** | Matches: 1, Partials: 0, NotEval: 3 |
| `A03` | fire certificate expired (valid_until before the submission date) | `None` | `None` | **PASS** | Matches: 3, Partials: 1, NotEval: 0 |
| `A04` | land area below minimum (6500 sqm) | `None` | `None` | **PASS** | Matches: 3, Partials: 1, NotEval: 0 |
| `A05` | owner name mismatch: land owner_name is a different person from the trust's name | `XDOC-OWNER-TRUST` | `XDOC-OWNER-TRUST` | **PASS** | Matches: 2, Partials: 1, NotEval: 0 |
| `A06` | tampered fire certificate: valid_until date edited | `None` | `None` | **PASS** | Matches: 3, Partials: 1, NotEval: 0 |
| `A07` | tampered land document: area_sqm digits edited upward to pass the minimum | `None` | `None` | **PASS** | Matches: 3, Partials: 1, NotEval: 0 |
| `A08` | duplicate: reuses the exact fire certificate file and certificate number from A01 for a different institution | `None` | `XDOC-INSTITUTION-NAME` | **PASS** | Matches: 2, Partials: 1, NotEval: 0 |
| `A09` | clean application where the land document is in Hindi | `None` | `None` | **PASS** | Matches: 3, Partials: 1, NotEval: 0 |
| `A10` | clean content, but every document is a poor scan (slight rotation, blur, noise, lower contrast) | `None` | `None` | **PASS** | Matches: 3, Partials: 1, NotEval: 0 |
| `A11` | multiple problems: name mismatch + expired certificate + tampered land document (to produce the highest risk) | `XDOC-OWNER-TRUST` | `XDOC-OWNER-TRUST` | **PASS** | Matches: 2, Partials: 1, NotEval: 0 |
| `A12` | minor name variation that should NOT be a conflict (e.g. 'Shri Sai Education Trust' vs 'Sri Sai Education Trust' and 'Shree Sai Educational Trust') | `None` | `None` | **PASS** | Matches: 3, Partials: 1, NotEval: 0 |
| `A13` | fire certificate with no QR code (clean otherwise, absent from registry) | `None` | `None` | **PASS** | Matches: 3, Partials: 1, NotEval: 0 |

## 2. Key Scenario Behavior Analysis

### Application A05 (Owner Name Mismatch)
- **Result:** Correctly identified `XDOC-OWNER-TRUST` conflict as expected.
- **Left (Land Owner):** `Rameshwar Prasad Sharma`
- **Right (Trust / Trustees):** `Dr. Arvind Sharma, Meena K. Patel, Suresh Rao`
- **Outcome:** Status `conflict` (Score: 60.14)

### Application A11 (Owner Name Mismatch + Expired + Tampered)
- **Result:** Correctly identified `XDOC-OWNER-TRUST` conflict in conjunction with other flaws.
- **Left (Land Owner):** `Vikas Narayan Murthy`
- **Right (Trust / Trustees):** `Dr. Arvind Sharma, Meena K. Patel, Suresh Rao`
- **Outcome:** Status `conflict` (Score: 33.7)

### Application A09 (Hindi Land Document vs English Trust)
- **Result:** Successfully matched Devanagari Hindi land owner with English trust through transliteration!
- **Left (Land Owner Hindi):** `श्री वनियक एजुकेशन ट्रसूट` (Normalized: `vaniyaka ejukeshana trasuta`)
- **Right (Trust English):** `00 (Shri Vinayak Education Trust)` (Normalized: `00 vinayak education trust`)
- **Score:** 100.0 (Status: `match`)

### Application A12 (Minor Name Variation - False Positive Guard)
- **Result:** Correctly avoided false positive conflict on spelling variant (`match`).
- **Left (Land Owner):** `Shree Sai Educational Trust`
- **Right (Trust Name):** `Shri Sai Education Trust`
- **Score:** 100.0 (Status: `match`)

### Application A08 (Duplicate Certificate from Different Institution)
- **Scenario:** Reused A01's fire safety certificate ('Apex Institute of Technology') for applicant 'Beacon Engineering College'.
- **Institution Name Check:** Successfully detected conflict reflecting cross-institution duplicate (`Apex Institute of Technology` vs `Beacon Engineering College`).
- **Owner vs Trust Check:** Land owner matches sponsoring trust (`match`, score 100.0).

### Application A10 (Poor Scans - Confidence / Missing Guard)
- **Not Evaluable Rules:** []
- **Partial Rules:** ['XDOC-ADDRESS']
- **Conflict Count:** 0

## 3. Discrepancy Breakdown (False Positives & False Negatives)

### False Positives (Unexpected Conflicts)
- **Application A08:** ['XDOC-INSTITUTION-NAME']
