import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import path from 'path';

// Setup deterministic mocks for Institution Portal end-to-end tests
const setupInstitutionMocks = async (page: any) => {
  const apiPattern = (subpath: string) => new RegExp(`http://(localhost|127\\.0\\.0\\.1):8000${subpath}`);

  // Institutions endpoint
  await page.route(apiPattern('/institutions'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 1,
          name: 'Apex Institute of Technology',
          state: 'Maharashtra',
          trust_name: 'Apex Educational Foundation',
          created_at: '2026-01-01',
        },
        {
          id: 2,
          name: 'Horizon Institute of Engineering',
          state: 'Karnataka',
          trust_name: 'Horizon Global Trust',
          created_at: '2026-01-01',
        },
        {
          id: 5,
          name: 'Vanguard Academy of Technical Studies',
          state: 'Gujarat',
          trust_name: 'Vanguard Educational Trust',
          created_at: '2026-01-01',
        },
      ]),
    });
  });

  // Config endpoint
  await page.route(apiPattern('/admin/config'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application_types: {
          new_institute: {
            name: 'New Technical Institution (Establishment)',
            required_documents: ['fire_safety_certificate', 'land_document', 'trust_registration'],
            description: 'Establishment of new technical institution under Chapter 1.',
          },
          extension_of_approval: {
            name: 'Extension of Approval (EoA - Annual Continuation)',
            required_documents: ['fire_safety_certificate', 'building_plan'],
            description: 'Annual continuation of approval.',
          },
        },
        document_types: ['fire_safety_certificate', 'land_document', 'trust_registration', 'building_plan'],
        total_rules: 14,
      }),
    });
  });

  // Applications list and creation
  await page.route(apiPattern('/applications(\\?.*)?$'), async (route: any) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 99,
          institution_id: 2,
          application_type: 'new_institute',
          status: 'draft',
          submission_date: '2026-04-01',
          created_at: '2026-04-01T10:00:00Z',
          documents: [],
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 2,
          institution_id: 2,
          institution_name: 'Horizon Institute of Engineering',
          application_type: 'new_institute',
          status: 'draft',
          submission_date: null,
          label: 'needs_verification',
          reasons: { MISSING_TRUST: 'Trust registration deed missing.' },
          created_at: '2026-03-12T10:00:00Z',
        },
        {
          id: 5,
          institution_id: 5,
          institution_name: 'Vanguard Academy of Technical Studies',
          application_type: 'new_institute',
          status: 'deficiency_sent',
          submission_date: '2026-03-15',
          label: 'inconsistent',
          reasons: { OWNER_MISMATCH: 'Land owner does not match sponsoring trust.' },
          created_at: '2026-03-15T10:00:00Z',
        },
      ]),
    });
  });

  // Application #2 (A02: Missing Trust Registration)
  await page.route(apiPattern('/applications/2$'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 2,
        institution_id: 2,
        institution_name: 'Horizon Institute of Engineering',
        application_type: 'new_institute',
        status: 'draft',
        submission_date: null,
        label: 'needs_verification',
        documents: [
          {
            id: 201,
            application_id: 2,
            doc_type: 'fire_safety_certificate',
            file_path: 'storage/uploads/2/fire_cert.png',
            language: 'en',
            ocr_confidence: 0.94,
            label: 'verified',
            extracted_fields: [
              { name: 'institution_name', value_original: 'Horizon Institute of Engineering', value_normalized: 'Horizon Institute of Engineering', confidence: 0.96, needs_verification: false },
              { name: 'valid_until', value_original: '2027-03-31', value_normalized: '2027-03-31', confidence: 0.92, needs_verification: false },
            ],
          },
          {
            id: 202,
            application_id: 2,
            doc_type: 'land_document',
            file_path: 'storage/uploads/2/land_deed.png',
            language: 'en',
            ocr_confidence: 0.89,
            label: 'needs_verification',
            extracted_fields: [
              { name: 'owner_name', value_original: 'Horizon Global Trust', value_normalized: 'Horizon Global Trust', confidence: 0.88, needs_verification: false },
              { name: 'total_area_sqm', value_original: '12500', value_normalized: '12500', confidence: 0.91, needs_verification: false },
            ],
          },
        ],
      }),
    });
  });

  // Completeness check for #2 (shows missing trust_registration)
  await page.route(apiPattern('/applications/2/completeness'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application_id: 2,
        application_type: 'new_institute',
        is_complete: false,
        required: ['fire_safety_certificate', 'land_document', 'trust_registration'],
        present: ['fire_safety_certificate', 'land_document'],
        missing: ['trust_registration'],
        unrecognized: [],
        duplicates_of_type: [],
        missing_findings: [
          {
            rule_id: 'MISSING:trust_registration',
            description: 'Mandatory document trust_registration is missing.',
            missing_doc_type: 'trust_registration',
            severity: 'high',
          },
        ],
      }),
    });
  });

  // Pre-submission validation for #2
  await page.route(apiPattern('/applications/2/validate'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application_id: 2,
        status: 'completed',
        is_valid: false,
        summary: { passed: 2, failed: 1, not_evaluable: 1 },
        findings: [
          {
            rule_id: 'MISSING:trust_registration',
            description: 'Missing Mandatory Document: Trust Registration',
            message: "Mandatory document 'trust_registration' is missing from dossier.",
            severity: 'high',
            clause: 'Handbook Chapter 1 Mandatory Documents',
            category: 'completeness',
          },
        ],
        consistency: [],
        consistency_summary: { match: 1, partial: 0, conflict: 0, total: 1 },
        label: 'needs_verification',
      }),
    });
  });

  // Consistency check for #2
  await page.route(apiPattern('/applications/2/consistency'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        summary: { match: 1, partial: 0, conflict: 0, total: 1 },
        comparisons: [],
      }),
    });
  });

  // Application #5 (A05: Deficiency Sent with Owner Mismatch)
  await page.route(apiPattern('/applications/5$'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 5,
        institution_id: 5,
        institution_name: 'Vanguard Academy of Technical Studies',
        application_type: 'new_institute',
        status: 'deficiency_sent',
        submission_date: '2026-03-15',
        label: 'inconsistent',
        documents: [
          {
            id: 501,
            application_id: 5,
            doc_type: 'fire_safety_certificate',
            file_path: 'storage/uploads/5/fire_cert.png',
            language: 'en',
            ocr_confidence: 0.95,
            label: 'verified',
          },
          {
            id: 502,
            application_id: 5,
            doc_type: 'land_document',
            file_path: 'storage/uploads/5/land_deed.png',
            language: 'en',
            ocr_confidence: 0.92,
            label: 'inconsistent',
          },
          {
            id: 503,
            application_id: 5,
            doc_type: 'trust_registration',
            file_path: 'storage/uploads/5/trust_deed.png',
            language: 'en',
            ocr_confidence: 0.93,
            label: 'verified',
          },
        ],
      }),
    });
  });

  await page.route(apiPattern('/applications/5/completeness'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application_id: 5,
        application_type: 'new_institute',
        is_complete: true,
        required: ['fire_safety_certificate', 'land_document', 'trust_registration'],
        present: ['fire_safety_certificate', 'land_document', 'trust_registration'],
        missing: [],
        unrecognized: [],
        duplicates_of_type: [],
      }),
    });
  });

  await page.route(apiPattern('/applications/5/consistency'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        summary: { match: 2, partial: 0, conflict: 1, total: 3 },
        comparisons: [
          {
            rule_id: 'XDOC-OWNER-TRUST',
            description: 'Land Owner vs Sponsoring Trust Entity Continuity',
            left: { document_type: 'land_document', field: 'owner_name', original: 'Rameshwar Prasad Sharma', normalized: 'Rameshwar Prasad Sharma' },
            right: { document_type: 'trust_registration', field: 'trust_name', original: 'Vanguard Educational Trust', normalized: 'Vanguard Educational Trust' },
            status: 'conflict',
            score: 60.1,
            evidence: {
              steps: [
                { step: 'Entity Token Comparison', description: 'Name Rameshwar Prasad Sharma has zero token overlap with Vanguard Educational Trust.' },
              ],
            },
          },
        ],
      }),
    });
  });

  // Deficiency Report for #5
  await page.route(apiPattern('/applications/5/deficiency-report'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 55,
        application_id: 5,
        status: 'sent',
        approved_by: 'Dr. S. K. Verma (Scrutiny Officer)',
        content: {
          summary_text: 'Land ownership entity does not align with sponsoring educational trust.',
          items: [
            {
              item_id: 'DEF-XDOC-OWNER-TRUST',
              title: 'Land Ownership Entity Conflict (XDOC-OWNER-TRUST)',
              what_failed: 'The land title deed specifies individual owner Rameshwar Prasad Sharma instead of sponsoring Vanguard Educational Trust.',
              why: "Land owner 'Rameshwar Prasad Sharma' does not match sponsoring trust or any trustee in 'Dr. Arvind Sharma, Meena K. Patel, Suresh Rao'.",
              clause: 'AICTE Approval Process Handbook — Title Continuity Clause 2.1',
              what_to_resubmit: 'Please obtain and upload a registered supplementary deed or corrected land title in the draft copy.',
              severity: 'high',
            },
          ],
        },
        created_at: '2026-03-18T10:00:00Z',
      }),
    });
  });

  // Create Draft Copy from #5
  await page.route(apiPattern('/applications/5/drafts'), async (route: any) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 505,
        institution_id: 5,
        institution_name: 'Vanguard Academy of Technical Studies',
        application_type: 'new_institute',
        status: 'draft',
        parent_application_id: 5,
        submission_date: null,
        created_at: '2026-03-20T10:00:00Z',
        documents: [],
      }),
    });
  });

  // Upload draft document
  await page.route(apiPattern('/drafts/[0-9]+/documents'), async (route: any) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 901,
        application_id: 505,
        doc_type: 'land_document',
        file_path: 'storage/uploads/draft_505/A05_corrected_land.png',
        language: 'en',
        ocr_confidence: 0.96,
        label: 'verified',
      }),
    });
  });

  // Recheck draft
  await page.route(apiPattern('/drafts/[0-9]+/recheck'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application_id: 505,
        status: 'completed',
        is_valid: true,
        summary: { passed: 3, failed: 0, not_evaluable: 0 },
        findings: [],
        consistency: [],
        label: 'verified',
      }),
    });
  });

  // Draft comparison (Shows Before/After with 1 issue resolved)
  await page.route(apiPattern('/drafts/[0-9]+/comparison'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        parent_application_id: 5,
        draft_application_id: 505,
        summary_sentence: '1 issue before, 0 remaining',
        counts: { resolved: 1, remaining: 0, new: 0, total_before: 1, total_remaining: 0 },
        resolved_issues: [
          {
            id: 'DEF-XDOC-OWNER-TRUST',
            category: 'consistency',
            title: 'Land Ownership Entity Conflict (XDOC-OWNER-TRUST)',
            status: 'resolved',
            before_message: "Land owner 'Rameshwar Prasad Sharma' did not match sponsoring trust.",
            after_message: 'Corrected land deed registered to Vanguard Educational Trust verified successfully.',
            clause: 'Handbook Title Continuity Clause 2.1',
            severity: 'high',
          },
        ],
        remaining_issues: [],
        new_issues: [],
        label_changes: [
          { doc_type: 'land_document', before_label: 'inconsistent', after_label: 'verified' },
        ],
        risk_changes: { before_score: 75, after_score: 15, score_delta: -60 },
      }),
    });
  });

  // Transparent mock images for file viewers
  await page.route(apiPattern('/documents/[0-9]+/file'), async (route: any) => {
    const pngBuffer = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64');
    await route.fulfill({ status: 200, contentType: 'image/png', body: pngBuffer });
  });
};

test.describe('Institution Portal - Verification & Accessibility Suite', () => {
  test('1. Landing Screen & Role Chooser', async ({ page }) => {
    await setupInstitutionMocks(page);

    await page.goto('/');
    await expect(page.locator('h1')).toContainText('DocValidate Workstation');

    // Verify Persistent Prototype Disclaimer Banner
    await expect(page.locator('role=note')).toContainText('Prototype using synthetic data');

    // Choose Institution Persona
    await page.locator('[role="button"]:has-text("Institution Applicant")').click();
    await page.selectOption('#landing-inst', '2'); // Horizon Institute

    // Save screenshot
    await page.screenshot({ path: 'screenshots/institution/01_landing_role_chooser.png' });

    // Accessibility test
    const axeResult = await new AxeBuilder({ page }).analyze();
    const criticalViolations = axeResult.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalViolations).toHaveLength(0);
  });

  test('2. My Applications List & New Application Modal', async ({ page }) => {
    await setupInstitutionMocks(page);

    await page.goto('/institution/applications');
    await expect(page.locator('h1')).toContainText('Approval Applications');

    // Table Columns Verification
    await expect(page.locator('th:has-text("Application ID")')).toBeVisible();
    await expect(page.locator('th:has-text("Status")')).toBeVisible();
    await expect(page.locator('th:has-text("Issue Count")')).toBeVisible();
    await expect(page.locator('th:has-text("Last Updated")')).toBeVisible();

    // Verify Status Chips with Icon + Text
    await expect(page.locator('text=Draft').first()).toBeVisible();

    await page.screenshot({ path: 'screenshots/institution/02_applications_list.png' });

    // Open New Application Modal
    await page.locator('button:has-text("New Application")').click();
    await expect(page.locator('text=Create New Approval Application')).toBeVisible();

    await page.screenshot({ path: 'screenshots/institution/03_new_application_modal.png' });

    // Accessibility on Applications List & Modal
    const axeResult = await new AxeBuilder({ page }).analyze();
    const criticalViolations = axeResult.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalViolations).toHaveLength(0);
  });

  test('3. Checklist Shows Missing Document (A02 Trust Registration)', async ({ page }) => {
    await setupInstitutionMocks(page);

    await page.goto('/institution/applications/2');
    await expect(page.locator('h1')).toContainText('Horizon Institute of Engineering');

    // Verify Stepper is at Step 1 Documents
    await expect(page.locator('text=Mandatory Approval Documents')).toBeVisible();

    // Checklist must show 'State: Missing' for trust_registration
    await expect(page.locator('h4:has-text("Trust Registration")')).toBeVisible();
    await expect(page.locator('text=State: Missing')).toBeVisible();

    // Take screenshot of Step 1 Checklist
    await page.screenshot({ path: 'screenshots/institution/04_checklist_missing_document.png' });

    // Accessibility check on Checklist
    const axeResult = await new AxeBuilder({ page }).analyze();
    const criticalViolations = axeResult.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalViolations).toHaveLength(0);
  });

  test('4. Pre-submission Check Shows Labels with Icon + Text', async ({ page }) => {
    await setupInstitutionMocks(page);

    await page.goto('/institution/applications/2');

    // Click Stepper Step 2: Pre-submission check
    await page.locator('button:has-text("2. Pre-submission check")').click();
    await expect(page.locator('h2:has-text("Pre-Submission Validation Check")')).toBeVisible();

    // Verify Prominent Text: "This check does not submit your application."
    await expect(
      page.locator('text=This check does not submit your application')
    ).toBeVisible();

    // Run Pre-check
    await page.locator('button:has-text("Run Pre-Submission Check")').click();

    // Verify summary strip counts per label (Verified, Needs Verification, Inconsistent, Possible Tampering)
    await expect(page.locator('span:has-text("Verified")').first()).toBeVisible();
    await expect(page.locator('span:has-text("Needs Verification")').first()).toBeVisible();
    await expect(page.locator('span:has-text("Inconsistent")').first()).toBeVisible();
    await expect(page.locator('span:has-text("Possible Tampering")').first()).toBeVisible();

    // Screenshot of Pre-Submission Check Results
    await page.screenshot({ path: 'screenshots/institution/05_pre_submission_check_labels.png' });
  });

  test('5. Submit Summary and Confirmation Dialog', async ({ page }) => {
    await setupInstitutionMocks(page);

    await page.goto('/institution/applications/2');

    // Step 3: Submit
    await page.locator('button:has-text("3. Submit")').click();
    await expect(page.locator('h2:has-text("Official Application Submission")')).toBeVisible();

    // Click Submit CTA to trigger confirm dialog
    await page.locator('button:has-text("Submit Application Officially")').click();
    await expect(page.locator('text=Confirm Official Application Submission')).toBeVisible();

    await page.screenshot({ path: 'screenshots/institution/06_submit_summary_confirm.png' });
  });

  test('6. Open A05 Deficiency Report, Create Draft, Recheck, and Before/After Panel', async ({ page }) => {
    await setupInstitutionMocks(page);

    // Open Application #5 (Vanguard)
    await page.goto('/institution/applications/5');
    await expect(page.locator('h1')).toContainText('Vanguard Academy of Technical Studies');

    // Step 4: Feedback (Deficiency Report)
    await page.locator('button:has-text("4. Feedback")').click();
    await expect(page.locator('text=Official Deficiency & Scrutiny Report')).toBeVisible();

    // Verify numbered item and owner mismatch
    await expect(page.locator('text=Land Ownership Entity Conflict')).toBeVisible();
    await expect(page.locator('text=What Failed:')).toBeVisible();
    await expect(page.locator('text=What to Resubmit:')).toBeVisible();

    await page.screenshot({ path: 'screenshots/institution/07_deficiency_report.png' });

    // Click "Create Draft and Fix"
    await page.locator('button:has-text("Create Draft & Fix")').first().click();

    // Navigates to Step 5: Fix and recheck
    await expect(page.locator('h2:has-text("Fix Deficiencies & Run Recheck")')).toBeVisible();
    await expect(page.locator('text=Your original submission stays unchanged').first()).toBeVisible();

    // Run recheck on draft
    await page.locator('button:has-text("Run Recheck on Draft")').click();

    // Verify Before/After Panel appears after recheck
    await expect(page.locator('text=1 issue before, 0 remaining')).toBeVisible();
    await expect(page.locator('span:has-text("Resolved")')).toBeVisible();
    await expect(page.locator('span:has-text("Remaining")')).toBeVisible();
    await expect(page.locator('span:has-text("New Defects")')).toBeVisible();

    // Verify per-document label change (Inconsistent to Verified)
    await page.locator('text=Document Label Evolution').scrollIntoViewIfNeeded();
    await expect(page.locator('text=Land Document')).toBeVisible();

    // Verify "Submit as Resubmission" button is now enabled
    const resubmitBtn = page.locator('button:has-text("Submit as Resubmission")');
    await expect(resubmitBtn).toBeEnabled();

    await page.screenshot({ path: 'screenshots/institution/08_fix_and_recheck_before_after.png' });

    // Accessibility check on Before/After
    const axeResult = await new AxeBuilder({ page }).analyze();
    const criticalViolations = axeResult.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalViolations).toHaveLength(0);
  });

  test('7. Help & Handbook Page', async ({ page }) => {
    await setupInstitutionMocks(page);

    await page.goto('/help');
    await expect(page.locator('h1')).toContainText('Validation System Help & Standards');

    // Verify statutory disclaimer note
    await expect(page.locator('text=Results are system-assisted. The officer makes the final decision.')).toBeVisible();

    // Verify 4 labels in simple words
    await expect(page.locator('h3:has-text("Verified (Green)")')).toBeVisible();
    await expect(page.locator('h3:has-text("Needs Verification (Amber)")')).toBeVisible();
    await expect(page.locator('h3:has-text("Inconsistent (Red)")')).toBeVisible();
    await expect(page.locator('h3:has-text("Possible Tampering (Deep Magenta)")')).toBeVisible();

    // Verify Required Documents by Category
    await expect(page.locator('h2:has-text("Required Documents by Application Type")')).toBeVisible();

    await page.screenshot({ path: 'screenshots/institution/09_help_handbook_page.png' });

    const axeResult = await new AxeBuilder({ page }).analyze();
    const criticalViolations = axeResult.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalViolations).toHaveLength(0);
  });
});
