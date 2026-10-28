import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import path from 'path';

// Setup common API route mocks for deterministic end-to-end testing
const setupMocks = async (page: any) => {
  // Institutions
  await page.route('**/institutions', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 1,
          name: 'Apex Institute of Technology',
          state: 'Maharashtra',
          trust_name: 'Apex Educational Society',
          created_at: '2026-01-01',
        },
        {
          id: 2,
          name: 'Horizon Institute of Engineering',
          state: 'Karnataka',
          trust_name: 'Horizon Educational Trust',
          created_at: '2026-01-01',
        },
      ]),
    });
  });

  // Officer Queue
  await page.route('**/officer/queue*', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          application_id: 1,
          rank: 1,
          institution_id: 2,
          institution_name: 'Horizon Institute of Engineering',
          institution_state: 'Karnataka',
          application_type: 'new_institute',
          status: 'submitted',
          submission_date: '2026-03-12',
          label: 'inconsistent',
          risk_score: 78,
          risk_band: 'high',
          top_factors: [
            { factor: 'cross_doc_owner_mismatch', points: 40, description: 'Land deed owner does not match trust.' },
            { factor: 'fire_noc_expired', points: 25, description: 'Fire NOC expired.' },
          ],
          issue_counts: { total: 3, rule_failures: 2, consistency_conflicts: 1, possible_tampering: 0, needs_verification: 0 },
          is_resubmission: false,
          created_at: '2026-03-12T10:00:00Z',
        },
        {
          application_id: 2,
          rank: 2,
          institution_id: 1,
          institution_name: 'Apex Institute of Technology',
          institution_state: 'Maharashtra',
          application_type: 'extension_of_approval',
          status: 'submitted',
          submission_date: '2026-03-10',
          label: 'verified',
          risk_score: 18,
          risk_band: 'low',
          top_factors: [],
          issue_counts: { total: 0, rule_failures: 0, consistency_conflicts: 0, possible_tampering: 0, needs_verification: 0 },
          is_resubmission: true,
          parent_application_id: 99,
          created_at: '2026-03-10T10:00:00Z',
        },
      ]),
    });
  });

  // Officer Application Detail
  await page.route('**/officer/applications/1', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application: {
          id: 1,
          institution_id: 2,
          application_type: 'new_institute',
          status: 'submitted',
          submission_date: '2026-03-12',
          risk_score: 78,
          risk_band: 'high',
          label: 'inconsistent',
        },
        institution: {
          id: 2,
          name: 'Horizon Institute of Engineering',
          state: 'Karnataka',
          trust_name: 'Horizon Educational Trust',
        },
        history_timeline: [
          { id: 1, year: 2025, outcome: 'Deficiency Noted', deficiency_count: 2, flags_count: 1 },
          { id: 2, year: 2024, outcome: 'Approved', deficiency_count: 0, flags_count: 0 },
        ],
        documents: [
          {
            id: 101,
            application_id: 1,
            doc_type: 'fire_safety_certificate',
            file_path: 'storage/uploads/1/fire_cert.png',
            label: 'needs_verification',
            ocr_language: 'en',
            ocr_confidence: 0.88,
            extracted_fields: [
              { name: 'certificate_number', value_original: 'FS-2026-88', value_normalized: 'FS202688', confidence: 0.95 },
              { name: 'valid_until', value_original: '2026-01-15', value_normalized: '2026-01-15', confidence: 0.92, needs_verification: true },
            ],
          },
          {
            id: 102,
            application_id: 1,
            doc_type: 'land_document',
            file_path: 'storage/uploads/1/land_deed.png',
            label: 'inconsistent',
            ocr_language: 'en',
            ocr_confidence: 0.91,
            extracted_fields: [
              { name: 'owner_name', value_original: 'Ramesh Chand', value_normalized: 'ramesh chand', confidence: 0.94 },
              { name: 'area_sqm', value_original: '6500', value_normalized: '6500', confidence: 0.89, needs_verification: true },
            ],
          },
        ],
        completeness: {
          application_id: 1,
          application_type: 'new_institute',
          is_complete: true,
          required: ['fire_safety_certificate', 'land_document', 'trust_registration'],
          present: ['fire_safety_certificate', 'land_document'],
          missing: ['trust_registration'],
          unrecognized: [],
          duplicates_of_type: [],
        },
        rule_results: [
          {
            id: 1,
            rule_id: 'LAND-AREA-MIN',
            description: 'Land area meets minimum norm (10,000 sq.m)',
            status: 'failed',
            passed: false,
            severity: 'high',
            message: 'Total land area 6,500 sq.m is below required 10,000 sq.m norm.',
            clause: 'Handbook Norm 2.1',
            evidence: { area_sqm: 6500, min_required: 10000 },
          },
        ],
        consistency: [
          {
            rule_id: 'XDOC-OWNER-TRUST',
            description: 'Land owner name must match sponsoring trust or trustee',
            status: 'conflict',
            severity: 'high',
            score: 54.0,
            message: "Land owner 'Ramesh Chand' does not match sponsoring trust 'Horizon Educational Trust'.",
            clause: 'Handbook Norm 2.3',
            left: { doc_type: 'land_document', field: 'owner_name', original: 'Ramesh Chand', normalized: 'ramesh chand' },
            right: { doc_type: 'trust_registration', field: 'trust_name', original: 'Horizon Educational Trust', normalized: 'horizon education trust' },
            evidence: { diff_tokens: ['ramesh', 'chand', 'horizon'] },
          },
        ],
        forensics: [
          {
            document_id: 101,
            doc_type: 'fire_safety_certificate',
            tampering_score: 0.12,
            status: 'ok',
            annotated_image_path: 'storage/forensics/fire_annotated.png',
            heatmap_image_path: 'storage/forensics/fire_heatmap.png',
          },
        ],
        risk_breakdown: {
          score: 78,
          band: 'high',
          top_factors: [
            { factor: 'cross_doc_owner_mismatch', points: 40, description: 'Land deed owner does not match trust.' },
            { factor: 'land_area_below_norm', points: 25, description: 'Area 6,500 sq.m below 10,000 sq.m norm.' },
          ],
        },
        audit_logs: [
          { id: 1, timestamp: '2026-03-12T10:15:00Z', actor: 'system', action: 'run_consistency_check', entity: 'application:1' },
          { id: 2, timestamp: '2026-03-12T10:00:00Z', actor: 'institution', action: 'submit_application', entity: 'application:1' },
        ],
        deficiency_report: {
          id: 1,
          application_id: 1,
          status: 'draft',
          content: {
            items: [
              {
                id: 'DEF-1',
                clause: 'Handbook Norm 2.1',
                severity: 'high',
                description: 'Land area of 6,500 sq.m does not satisfy the statutory minimum requirement of 10,000 sq.m.',
                actual_values: { area_sqm: 6500 },
                action_required: 'Submit supplementary registered deed for additional contiguous land parcel.',
              },
            ],
          },
        },
      }),
    });
  });

  // Institution Application
  await page.route('**/applications/1', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 1,
        institution_id: 1,
        application_type: 'new_institute',
        status: 'draft',
        submission_date: '2026-03-12',
        label: 'needs_verification',
        documents: [
          {
            id: 101,
            application_id: 1,
            doc_type: 'fire_safety_certificate',
            file_path: 'storage/uploads/1/fire_cert.png',
            ocr_language: 'en',
            ocr_confidence: 0.94,
            label: 'verified',
          },
          {
            id: 102,
            application_id: 1,
            doc_type: 'land_document',
            file_path: 'storage/uploads/1/land_deed.png',
            ocr_language: 'en',
            ocr_confidence: 0.88,
            label: 'needs_verification',
          },
        ],
      }),
    });
  });

  // Completeness check
  await page.route('**/applications/1/completeness', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        application_id: 1,
        application_type: 'new_institute',
        is_complete: false,
        required: ['fire_safety_certificate', 'land_document', 'trust_registration'],
        present: ['fire_safety_certificate', 'land_document'],
        missing: ['trust_registration'],
        unrecognized: [],
        duplicates_of_type: [],
      }),
    });
  });

  // Draft Comparison
  await page.route('**/drafts/1/comparison', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        parent_application_id: 1,
        draft_application_id: 2,
        summary_sentence: '3 failures before, 1 remaining',
        counts: { resolved: 2, remaining: 1, new: 0, total_before: 3, total_remaining: 1 },
        resolved_issues: [
          { id: '1', category: 'rule_failure', title: 'Land Area Below Norm', status: 'resolved', before_message: 'Area 6,500 sq.m below norm', after_message: 'Fixed: 12,000 sq.m registered', clause: 'Norm 2.1', severity: 'high' },
          { id: '2', category: 'missing_document', title: 'Missing Trust Registration', status: 'resolved', before_message: 'Trust deed missing', after_message: 'Deed uploaded and verified', clause: 'Norm 1.4', severity: 'high' },
        ],
        remaining_issues: [
          { id: '3', category: 'rule_failure', title: 'Fire Safety NOC Expiry', status: 'remaining', before_message: 'Expired 2026-01-15', after_message: 'Pending municipal renewal verification', clause: 'Norm 1.4', severity: 'medium' },
        ],
        new_issues: [],
        label_changes: [
          { doc_type: 'land_document', before_label: 'inconsistent', after_label: 'verified' },
          { doc_type: 'trust_registration', before_label: 'needs_verification', after_label: 'verified' },
        ],
        risk_changes: { before_score: 78, after_score: 28, score_delta: -50 },
      }),
    });
  });

  // Mock static files and images
  await page.route('**/documents/*/file', async (route: any) => {
    // 1x1 transparent png
    const pngBuffer = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64');
    await route.fulfill({ status: 200, contentType: 'image/png', body: pngBuffer });
  });

  await page.route('**/forensics/*', async (route: any) => {
    const pngBuffer = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64');
    await route.fulfill({ status: 200, contentType: 'image/png', body: pngBuffer });
  });
};

test.describe('DocValidate Workstation - E2E Tests & Screenshots', () => {
  test('Quality Bar: Screenshots & Accessibility', async ({ page }) => {
    await setupMocks(page);

    // 1. Landing Screen
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('DocValidate Workstation');
    await page.screenshot({ path: 'screenshots/landing.png' });

    // Axe accessibility check on Landing
    const axeLanding = await new AxeBuilder({ page }).analyze();
    const criticalLanding = axeLanding.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(criticalLanding).toHaveLength(0);

    // 2. Institution Checklist (Step 1)
    await page.goto('/institution/applications/1');
    await expect(page.locator('h1')).toContainText('Apex Institute of Technology');
    await page.screenshot({ path: 'screenshots/institution_checklist.png' });

    // 3. Pre-submission Results (Step 2)
    await page.locator('button:has-text("2. Pre-Check")').click();
    await expect(page.locator('text=Pre-Submission Validation Check')).toBeVisible();
    await page.screenshot({ path: 'screenshots/pre_submission_results.png' });

    // 4. Deficiency Report (Step 4)
    await page.locator('button:has-text("4. Deficiency Report")').click();
    await expect(page.locator('text=Official Scrutiny Feedback & Deficiency Report')).toBeVisible();
    await page.screenshot({ path: 'screenshots/deficiency_report.png' });

    // 5. Fix & Recheck Before/After (Step 5)
    await page.locator('button:has-text("5. Fix & Recheck")').click();
    await expect(page.locator('text=Fix Deficiencies & Run Recheck')).toBeVisible();
    await page.screenshot({ path: 'screenshots/draft_before_after.png' });

    // 6. Officer Queue
    await page.goto('/officer/queue');
    await expect(page.locator('h1')).toContainText('Risk-Ranked Scrutiny Queue');
    await page.screenshot({ path: 'screenshots/officer_queue.png' });

    // Axe accessibility check on Officer Queue
    const axeQueue = await new AxeBuilder({ page }).analyze();
    const criticalQueue = axeQueue.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(criticalQueue).toHaveLength(0);

    // 7. Officer Detail - Consistency Tab (Side by side comparison)
    await page.goto('/officer/applications/1');
    await expect(page.locator('h1')).toContainText('Horizon Institute of Engineering');
    await page.locator('button:has-text("Cross-Doc Consistency")').click();
    await expect(page.locator('text=Cross-Document Consistency Verifications')).toBeVisible();
    await expect(page.locator('text=Shri Sai Educational Trust')).toBeVisible();
    await page.screenshot({ path: 'screenshots/officer_detail_consistency.png' });

    // 8. Officer Detail - Documents Tab with ELA Heatmap Overlay
    await page.locator('button:has-text("Documents")').click();
    await page.locator('button:has-text("ELA Heatmap")').click();
    await page.screenshot({ path: 'screenshots/documents_tab_heatmap.png' });

    // 9. Design System Showcase (/design)
    await page.goto('/design');
    await expect(page.locator('h1')).toContainText('DocValidate Design System & Component Library');
    await page.screenshot({ path: 'screenshots/design_page.png' });

    // Axe accessibility check on Design Page
    const axeDesign = await new AxeBuilder({ page }).analyze();
    const criticalDesign = axeDesign.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(criticalDesign).toHaveLength(0);
  });

  test('Keyboard navigation: Queue row selection and Dialog Escape trap', async ({ page }) => {
    await setupMocks(page);

    await page.goto('/officer/queue');
    const tableRegion = page.locator('div[role="region"]');
    await tableRegion.focus();

    // Press ArrowDown to select first row
    await page.keyboard.press('ArrowDown');
    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toHaveAttribute('aria-selected', 'true');

    // Press Enter to open application detail
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/officer\/applications\/1/);

    // Open an action dialog (Approve)
    await page.locator('button:has-text("Approve")').first().click();
    const dialog = page.locator('div[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Verify Escape key closes the dialog
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
  });
});
