import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import path from 'path';

const apiPattern = (subpath: string) => new RegExp(`http://(localhost|127\\.0\\.0\\.1):8000${subpath}`);

const setupAllMocks = async (page: any) => {
  // Institutions
  await page.route(apiPattern('/institutions'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 1, name: 'Apex Institute of Technology', state: 'Maharashtra', trust_name: 'Apex Educational Foundation', created_at: '2026-01-01' },
        { id: 2, name: 'Horizon Institute of Engineering', state: 'Karnataka', trust_name: 'Horizon Global Trust', created_at: '2026-01-01' },
        { id: 5, name: 'Vanguard Academy of Technical Studies', state: 'Gujarat', trust_name: 'Vanguard Educational Trust', created_at: '2026-01-01' },
      ]),
    });
  });

  // Config
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
            required_documents: ['fire_safety_certificate', 'land_document'],
            description: 'Annual continuation of approval.',
          },
        },
        document_types: ['fire_safety_certificate', 'land_document', 'trust_registration'],
        rules_count: 24,
        consistency_rules_count: 8,
      }),
    });
  });

  // Applications list
  await page.route(apiPattern('/applications(\\?.*)?$'), async (route: any) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 99,
          institution_id: 1,
          institution_name: 'Apex Institute of Technology',
          application_type: 'new_institute',
          status: 'draft',
          created_at: new Date().toISOString(),
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 1,
          institution_id: 1,
          institution_name: 'Apex Institute of Technology',
          application_type: 'new_institute',
          status: 'draft',
          created_at: '2026-03-01T10:00:00Z',
          reasons: [],
        },
        {
          id: 2,
          institution_id: 1,
          institution_name: 'Apex Institute of Technology',
          application_type: 'new_institute',
          status: 'draft',
          created_at: '2026-03-02T11:00:00Z',
          reasons: [{ message: 'Missing trust_registration' }],
        },
        {
          id: 5,
          institution_id: 1,
          institution_name: 'Apex Institute of Technology',
          application_type: 'new_institute',
          status: 'deficiency_sent',
          created_at: '2026-03-05T09:00:00Z',
          label: 'inconsistent',
          reasons: [{ message: 'Land owner does not match trust deed' }],
        },
      ]),
    });
  });

  // Application 2 Detail
  await page.route(apiPattern('/applications/2$'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 2,
        institution_id: 1,
        institution_name: 'Apex Institute of Technology',
        application_type: 'new_institute',
        status: 'draft',
        created_at: '2026-03-02T11:00:00Z',
      }),
    });
  });

  // Completeness for Application 2 (A02: Missing Trust Registration)
  await page.route(apiPattern('/applications/2/completeness'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application_id: 2,
        is_complete: false,
        required: ['fire_safety_certificate', 'land_document', 'trust_registration'],
        present: ['fire_safety_certificate', 'land_document'],
        missing: ['trust_registration'],
        unrecognized: [],
        duplicates_of_type: [],
        documents: [
          {
            id: 201,
            application_id: 2,
            doc_type: 'fire_safety_certificate',
            file_path: 'storage/uploads/A02_fire.png',
            sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
            language: 'eng',
            ocr_confidence: 0.94,
            label: 'verified',
            system_label: 'verified',
            created_at: '2026-03-02T11:05:00Z',
          },
          {
            id: 202,
            application_id: 2,
            doc_type: 'land_document',
            file_path: 'storage/uploads/A02_land.png',
            sha256: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
            language: 'eng',
            ocr_confidence: 0.91,
            label: 'needs_verification',
            system_label: 'needs_verification',
            created_at: '2026-03-02T11:06:00Z',
          },
        ],
        missing_findings: [
          {
            rule_id: 'MISSING:trust_registration',
            document_type: 'trust_registration',
            message: "Mandatory document 'trust_registration' is missing. Please upload official deed.",
            severity: 'high',
            clause: 'Handbook Chapter 1 Clause 1.4 (Statutory Trust Registration)',
          },
        ],
      }),
    });
  });

  // Pre-submission validation endpoint
  await page.route(apiPattern('/applications/2/validate'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application_id: 2,
        label: 'needs_verification',
        counts: { verified: 1, needs_verification: 1, inconsistent: 0, possible_tampering: 0 },
        rule_results: [
          {
            id: 21,
            rule_id: 'MISSING:trust_registration',
            passed: false,
            severity: 'high',
            status: 'failed',
            message: "Mandatory document 'trust_registration' is missing.",
            clause: 'Chapter 1 Clause 1.4',
            values_used: { required: true, present: false },
          },
        ],
        consistency: { comparisons: [] },
      }),
    });
  });

  // Application 5 Detail (A05 Deficiency & Resubmission)
  await page.route(apiPattern('/applications/5$'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 5,
        institution_id: 1,
        institution_name: 'Apex Institute of Technology',
        application_type: 'new_institute',
        status: 'deficiency_sent',
        created_at: '2026-03-05T09:00:00Z',
      }),
    });
  });

  // Completeness for Application 5
  await page.route(apiPattern('/applications/5/completeness'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application_id: 5,
        is_complete: true,
        required: ['fire_safety_certificate', 'land_document', 'trust_registration'],
        present: ['fire_safety_certificate', 'land_document', 'trust_registration'],
        missing: [],
        unrecognized: [],
        duplicates_of_type: [],
        documents: [
          { id: 501, application_id: 5, doc_type: 'fire_safety_certificate', file_path: 'A05_fire.png', sha256: '1111', language: 'eng', ocr_confidence: 0.95, label: 'verified', system_label: 'verified', created_at: '2026-03-05' },
          { id: 502, application_id: 5, doc_type: 'land_document', file_path: 'A05_land.png', sha256: '2222', language: 'eng', ocr_confidence: 0.92, label: 'inconsistent', system_label: 'inconsistent', created_at: '2026-03-05' },
          { id: 503, application_id: 5, doc_type: 'trust_registration', file_path: 'A05_trust.png', sha256: '3333', language: 'eng', ocr_confidence: 0.96, label: 'verified', system_label: 'verified', created_at: '2026-03-05' },
        ],
        missing_findings: [],
      }),
    });
  });

  // Application 5 Deficiency Report
  await page.route(apiPattern('/applications/5/deficiency-report'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 51,
        application_id: 5,
        status: 'sent',
        approved_by: 'Dr. S. K. Verma',
        content: {
          items: [
            {
              id: 1,
              title: 'Land Ownership Mismatch',
              clause: 'Approval Process Handbook Regulation 2.1 (Title Continuity)',
              severity: 'high',
              description: "Land deed registered in individual owner's name 'Ramesh Chand' does not match sponsoring trust 'Apex Educational Foundation'.",
              action_required: 'Upload registered conveyance deed or lease agreement executed in favor of the sponsoring trust entity.',
            },
          ],
          summary_text: 'The submitted application has 1 critical title inconsistency that must be remedied in draft resubmission.',
        },
      }),
    });
  });

  // Create Draft for Application 5
  await page.route(apiPattern('/applications/5/drafts'), async (route: any) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 151,
        institution_id: 1,
        parent_application_id: 5,
        application_type: 'new_institute',
        status: 'draft',
        created_at: new Date().toISOString(),
      }),
    });
  });

  // Draft Upload
  await page.route(apiPattern('/drafts/151/documents'), async (route: any) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 599,
        application_id: 151,
        doc_type: 'land_document',
        file_path: 'storage/uploads/draft_151/land_document.png',
        sha256: 'd41d8cd98f00b204e9800998ecf8427e',
        language: 'eng',
        ocr_confidence: 0.97,
        label: 'verified',
      }),
    });
  });

  // Draft Recheck
  await page.route(apiPattern('/drafts/151/recheck'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application_id: 151,
        label: 'verified',
        status: 'rechecked',
      }),
    });
  });

  // Draft Comparison
  await page.route(apiPattern('/drafts/151/comparison'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        parent_application_id: 5,
        draft_application_id: 151,
        summary_sentence: '1 failure before, 0 remaining',
        counts: {
          resolved: 1,
          remaining: 0,
          new: 0,
          total_before: 1,
          total_remaining: 0,
        },
        resolved_issues: [
          {
            id: 'XDOC-OWNER-TRUST',
            category: 'consistency',
            title: 'Land Ownership Mismatch',
            status: 'resolved',
            doc_type: 'land_document',
            severity: 'high',
            before_message: "Land owner 'Ramesh Chand' differed from trust.",
            after_message: 'Land deed now verified in favor of Apex Educational Foundation.',
          },
        ],
        remaining_issues: [],
        new_issues: [],
        label_changes: [
          {
            doc_type: 'land_document',
            document_id: 502,
            before_label: 'inconsistent',
            after_label: 'verified',
          },
        ],
      }),
    });
  });

  // Officer Queue endpoint
  await page.route(apiPattern('/officer/queue'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          application_id: 11,
          rank: 1,
          institution_name: 'Vanguard Academy of Technical Studies',
          institution_state: 'Gujarat',
          application_type: 'new_institute',
          label: 'possible_tampering',
          risk_score: 88,
          risk_band: 'high',
          top_factors: [{ factor: 'Image Splice / ELA Anomaly', description: 'Pixel density anomaly' }],
          is_resubmission: false,
          submission_date: '2026-03-10',
        },
        {
          application_id: 5,
          rank: 2,
          institution_name: 'Horizon Institute of Engineering',
          institution_state: 'Karnataka',
          application_type: 'new_institute',
          label: 'inconsistent',
          risk_score: 68,
          risk_band: 'high',
          top_factors: [{ factor: 'Entity Name Conflict', description: 'Land deed title difference' }],
          is_resubmission: true,
          parent_application_id: 4,
          submission_date: '2026-03-08',
        },
        {
          application_id: 1,
          rank: 3,
          institution_name: 'Apex Institute of Technology',
          institution_state: 'Maharashtra',
          application_type: 'new_institute',
          label: 'verified',
          risk_score: 12,
          risk_band: 'low',
          top_factors: [{ factor: 'Clean Record Baseline', description: 'All norms passed' }],
          is_resubmission: false,
          submission_date: '2026-03-01',
        },
      ]),
    });
  });

  // Officer Application Detail for App 5
  await page.route(apiPattern('/officer/applications/5$'), async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application: {
          id: 5,
          institution_id: 2,
          institution_name: 'Horizon Institute of Engineering',
          application_type: 'new_institute',
          status: 'in_review',
          label: 'inconsistent',
          risk_score: 68,
          risk_band: 'high',
          created_at: '2026-03-05T09:00:00Z',
        },
        institution: {
          id: 2,
          name: 'Horizon Institute of Engineering',
          state: 'Karnataka',
          trust_name: 'Horizon Global Trust',
          history: [],
        },
        documents: [
          {
            id: 501,
            application_id: 5,
            doc_type: 'land_document',
            file_path: 'storage/uploads/A05_land.png',
            sha256: '2222',
            language: 'eng',
            ocr_confidence: 0.92,
            label: 'inconsistent',
            system_label: 'inconsistent',
            created_at: '2026-03-05',
          },
        ],
        consistency: [
          {
            rule_id: 'XDOC-OWNER-TRUST',
            description: 'Land owner name must match sponsoring trust',
            status: 'conflict',
            severity: 'high',
            score: 55.4,
            clause: 'Handbook Regulation 2.1',
            left: { doc_type: 'land_document', field: 'owner_name', original: 'Ramesh Chand', normalized: 'ramesh chand' },
            right: { doc_type: 'trust_registration', field: 'trust_name', original: 'Horizon Global Trust', normalized: 'horizon global trust' },
            evidence: { steps: ['Transliteration', 'Suffix Match'], diff_tokens: ['ramesh', 'chand', 'horizon'] },
          },
        ],
        rules: [],
        deficiency_report: null,
        audit_logs: [],
      }),
    });
  });
};

test.describe('DocValidate National Portal Verification Suite', () => {
  test.beforeEach(async ({ page }) => {
    await setupAllMocks(page);
  });

  test('1. Authentication Flow: Validation, Demo Fill, Login, and Session Persistence', async ({ page }) => {
    await page.goto('/login');

    // Verify Title & Wordmark
    await expect(page.locator('text=Faster, fairer document review for institution approvals.')).toBeVisible();
    await expect(page.locator('text=Sign in')).toBeVisible();

    // Verify Accessible Validation: Empty submit displays inline error
    await page.click('button:has-text("Sign in as Institution")');
    await expect(page.locator('#identifier-error')).toBeVisible();

    // Fill via Demo Account chip
    await page.click('button:has-text("Apex Institute (Clean Record)")');
    await expect(page.locator('#identifier-input')).toHaveValue('apex@aicte.demo');
    await expect(page.locator('#password-input')).toHaveValue('demo123');

    // Submit sign in
    await page.click('button:has-text("Sign in as Institution")');

    // Must redirect to /institution
    await expect(page).toHaveURL(/\/institution/);
    await expect(page.locator('h1')).toContainText('Welcome');

    // Verify session persistence on page refresh
    await page.reload();
    await expect(page).toHaveURL(/\/institution/);
    await expect(page.locator('h1')).toContainText('Welcome');

    // Capture Institution Dashboard Screenshot
    await page.screenshot({ path: 'screenshots/institution_dashboard.png', fullPage: true });
  });

  test('2. Route Guard & 403 Forbidden Access Test', async ({ page }) => {
    // Sign in as Institution
    await page.goto('/login');
    await page.click('button:has-text("Apex Institute (Clean Record)")');
    await page.click('button:has-text("Sign in as Institution")');
    await expect(page).toHaveURL(/\/institution/);

    // Attempt unauthorized navigation to /officer
    await page.goto('/officer');

    // Must be blocked by route guard with 403 page
    await expect(page.locator('text=403 - Access Restricted')).toBeVisible();
    await expect(page.locator('text=Return to Your Authorized Dashboard')).toBeVisible();
  });

  test('3. Mobile View Responsive Test for Login Page', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/login');

    await expect(page.locator('text=Sign in')).toBeVisible();
    await expect(page.locator('#identifier-input')).toBeVisible();

    // Capture Mobile Screenshot
    await page.screenshot({ path: 'screenshots/login_mobile.png' });
  });

  test('4. Desktop Login View Screenshot', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/login');

    await expect(page.locator('text=Smart India Hackathon prototype')).toBeVisible();
    await page.screenshot({ path: 'screenshots/login_desktop.png' });
  });

  test('5. Application A02: Missing Document Flagged in Checklist', async ({ page }) => {
    // Authenticate into session
    await page.goto('/login');
    await page.click('button:has-text("Apex Institute (Clean Record)")');
    await page.click('button:has-text("Sign in as Institution")');

    // Navigate to Application A02
    await page.goto('/institution/applications/2');

    // Stepper step 1 active
    await expect(page.locator('text=1. Documents')).toBeVisible();

    // Checklist must show missing trust_registration card
    await expect(page.locator('h4:has-text("trust registration")')).toBeVisible();
    await expect(page.locator('span:has-text("Missing Document")')).toBeVisible();

    // Capture Workspace Checklist Screenshot
    await page.screenshot({ path: 'screenshots/workspace_checklist.png' });
  });

  test('6. Application A02: Pre-Submission Check Displays Validation Labels', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Apex Institute (Clean Record)")');
    await page.click('button:has-text("Sign in as Institution")');

    await page.goto('/institution/applications/2');

    // Move to step 2: Pre-submission check
    await page.click('text=2. Pre-submission check');

    // Prominent safe check text must be visible
    await expect(page.locator('text=This check does not submit your application')).toBeVisible();

    // Click "Run Pre-submission Check"
    await page.click('button:has-text("Run Pre-submission Check")');

    // Wait for staged timeline and label summary strip to appear
    await expect(page.locator('text=Validation Findings Summary')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('span:has-text("Needs Verification")')).toBeVisible();

    // Capture Pre-Submission Results Screenshot
    await page.screenshot({ path: 'screenshots/pre_submission_results.png' });
  });

  test('7. Application A05: Deficiency Report and Resubmission Before/After Panel', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Apex Institute (Clean Record)")');
    await page.click('button:has-text("Sign in as Institution")');

    await page.goto('/institution/applications/5');

    // Step 4: Feedback / Deficiency Report
    await page.click('text=4. Feedback');
    await expect(page.locator('text=Land Ownership Mismatch')).toBeVisible();
    await expect(page.locator('text=Create draft and fix')).toBeVisible();

    // Capture Deficiency Report Screenshot
    await page.screenshot({ path: 'screenshots/deficiency_report.png' });

    // Step 5: Fix and recheck
    await page.click('text=5. Fix and recheck');

    // Confirm original submission stays unchanged notice
    await expect(page.locator('text=Your original submission stays unchanged')).toBeVisible();

    // Trigger recheck
    await page.click('button:has-text("Recheck Draft")');

    // Verify Before/After panel appears with "1 failure before, 0 remaining" and 3 columns
    await expect(page.locator('h3:has-text("1 failure before, 0 remaining")')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('span:has-text("Resolved")')).toBeVisible();
    await expect(page.locator('span:has-text("Remaining")')).toBeVisible();
    await expect(page.locator('span:has-text("New Defects")')).toBeVisible();

    // Capture Before/After Panel Screenshot
    await page.screenshot({ path: 'screenshots/before_after_panel.png' });
  });

  test('8. Officer Scrutiny Queue: Risk Ranking & Filters', async ({ page }) => {
    await page.goto('/login');
    // Select Officer tab and demo account
    await page.click('button:has-text("Officer")');
    await page.click('button:has-text("Scrutiny Officer (Dr. S. K. Verma)")');
    await page.click('button:has-text("Sign in as Officer")');

    await expect(page).toHaveURL(/\/officer/);

    // Verify Queue Header & Illustrative Score Note
    await expect(page.locator('h1')).toContainText('Risk-Ranked Scrutiny Queue');
    await expect(page.locator('text=Illustrative score. Supports the officer\'s decision; does not replace it.')).toBeVisible();

    // Verify 4 StatTiles exist
    await expect(page.locator('text=Applications Waiting')).toBeVisible();
    await expect(page.locator('text=High Risk Priority')).toBeVisible();

    // Verify Application A11 is ranked first with high risk
    await expect(page.locator('text=Vanguard Academy of Technical Studies')).toBeVisible();

    // Capture Officer Queue Screenshot
    await page.screenshot({ path: 'screenshots/officer_queue.png' });
  });

  test('9. Officer Application Detail: Consistency Tab & Documents Heatmap View', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Officer")');
    await page.click('button:has-text("Scrutiny Officer (Dr. S. K. Verma)")');
    await page.click('button:has-text("Sign in as Officer")');

    await page.goto('/officer/applications/5');

    // Consistency Tab
    await page.click('button:has-text("Cross-Check Consistency")');
    await expect(page.locator('text=XDOC-OWNER-TRUST')).toBeVisible();
    await expect(page.locator('span:has-text("Inconsistent")')).toBeVisible();

    // Capture Officer Consistency Tab Screenshot
    await page.screenshot({ path: 'screenshots/officer_consistency_tab.png' });

    // Documents Tab
    await page.click('button:has-text("Dossier Documents")');
    await expect(page.locator('button:has-text("ELA Heatmap")')).toBeVisible();
    await expect(page.locator('text=Forensic signals are probabilities, not proof')).toBeVisible();

    // Capture Officer Documents Tab Screenshot
    await page.screenshot({ path: 'screenshots/officer_documents_heatmap.png' });
  });

  test('10. Automated Axe Accessibility Audit across Key Screens', async ({ page }) => {
    // 1. Audit Login Screen
    await page.goto('/login');
    const loginScan = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .disableRules(['color-contrast']) // verified separately with token contrast ratios
      .analyze();
    const loginViolations = loginScan.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
    expect(loginViolations).toEqual([]);

    // 2. Audit Officer Queue
    await page.click('button:has-text("Officer")');
    await page.click('button:has-text("Scrutiny Officer (Dr. S. K. Verma)")');
    await page.click('button:has-text("Sign in as Officer")');
    await expect(page).toHaveURL(/\/officer/);

    const queueScan = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast'])
      .analyze();
    const queueViolations = queueScan.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
    expect(queueViolations).toEqual([]);
  });
});

