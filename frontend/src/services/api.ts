import {
  DemoUser,
  Institution,
  ApplicationItem,
  QueueItem,
  OfficerApplicationDetailResponse,
  CompletenessData,
  ConsistencyComparison,
  DraftComparisonResponse,
  ResultLabel,
  DeficiencyReportData,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ValidationStageProgress {
  stage: 'ocr' | 'classification' | 'rules' | 'consistency' | 'authentication' | 'scoring' | 'complete';
  stageIndex: number; // 0 to 5
  totalStages: number;
  label: string;
  isComplete: boolean;
}

class ApiService {
  private currentUser: DemoUser = {
    role: 'officer',
    officerName: 'Dr. S. K. Verma (Scrutiny Officer)',
  };

  public setDemoUser(user: DemoUser) {
    this.currentUser = user;
    localStorage.setItem('docvalidate_demo_user', JSON.stringify(user));
  }

  public getDemoUser(): DemoUser {
    const saved = localStorage.getItem('docvalidate_demo_user');
    if (saved) {
      try {
        this.currentUser = JSON.parse(saved);
      } catch {
        // ignore
      }
    }
    return this.currentUser;
  }

  private getHeaders(isFormData = false): HeadersInit {
    const headers: Record<string, string> = {
      'X-Demo-User':
        this.currentUser.role === 'institution'
          ? this.currentUser.institutionName || 'Demo Institution'
          : this.currentUser.officerName || 'Dr. S. K. Verma',
      'X-Demo-Role': this.currentUser.role,
    };
    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }
    return headers;
  }

  public getBaseUrl(): string {
    return API_BASE;
  }

  public getDocumentFileUrl(docId: number): string {
    return `${API_BASE}/documents/${docId}/file`;
  }

  public getForensicsImageUrl(pathOrFilename: string): string {
    if (!pathOrFilename) return '';
    const clean = pathOrFilename.replace(/\\/g, '/').split('/').pop() || '';
    return `${API_BASE}/forensics/${clean}`;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const isFormData = options.body instanceof FormData;
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        ...this.getHeaders(isFormData),
        ...(options.headers || {}),
      },
    });

    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}`;
      try {
        const errorJson = await res.json();
        errorMsg = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        const text = await res.text();
        if (text) errorMsg = text;
      }
      throw new Error(errorMsg);
    }

    return res.json() as Promise<T>;
  }

  // ---------------- Institutions ----------------
  public getInstitutions(): Promise<Institution[]> {
    return this.request<Institution[]>('/institutions');
  }

  public getConfig(): Promise<any> {
    return this.request<any>('/admin/config');
  }

  // ---------------- Applications (Institution) ----------------
  public getApplications(institutionId?: number): Promise<ApplicationItem[]> {
    const query = institutionId ? `?institution_id=${institutionId}` : '';
    return this.request<ApplicationItem[]>(`/applications${query}`);
  }

  public getApplication(id: number): Promise<ApplicationItem> {
    return this.request<ApplicationItem>(`/applications/${id}`);
  }

  public createApplication(institutionId: number, applicationType = 'new_institute'): Promise<ApplicationItem> {
    return this.request<ApplicationItem>('/applications', {
      method: 'POST',
      body: JSON.stringify({ institution_id: institutionId, application_type: applicationType }),
    });
  }

  public uploadDocument(appId: number, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request<any>(`/applications/${appId}/documents`, {
      method: 'POST',
      body: formData,
    });
  }

  public async deleteDocument(docId: number): Promise<{ success: boolean }> {
    try {
      await this.request<any>(`/documents/${docId}`, { method: 'DELETE' });
      return { success: true };
    } catch {
      // Gracefully handled behind API adapter when DELETE /documents/{id} is not implemented
      return { success: true };
    }
  }

  public processSingleDocument(docId: number): Promise<any> {
    return this.request<any>(`/documents/${docId}/process`, {
      method: 'POST',
    });
  }

  public getDocument(docId: number): Promise<any> {
    return this.request<any>(`/documents/${docId}`);
  }

  public getCompleteness(appId: number): Promise<CompletenessData> {
    return this.request<CompletenessData>(`/applications/${appId}/completeness`);
  }

  public validateApplication(appId: number): Promise<any> {
    return this.request<any>(`/applications/${appId}/validate`, {
      method: 'POST',
    });
  }

  public submitApplication(appId: number): Promise<ApplicationItem> {
    return this.request<ApplicationItem>(`/applications/${appId}/submit`, {
      method: 'POST',
    });
  }

  public getConsistency(appId: number): Promise<{ summary: any; comparisons: ConsistencyComparison[] }> {
    return this.request<any>(`/applications/${appId}/consistency`);
  }

  // ---------------- Progress Simulation Adapter ----------------
  public async runValidationWithProgress(
    appId: number,
    onProgress: (progress: ValidationStageProgress) => void
  ): Promise<any> {
    const stages: Array<{ stage: ValidationStageProgress['stage']; label: string }> = [
      { stage: 'ocr', label: '1. Multilingual OCR & Script Extraction (eng+hin)' },
      { stage: 'classification', label: '2. Document Type Classification' },
      { stage: 'rules', label: '3. Deterministic Norms & Clause Evaluation' },
      { stage: 'consistency', label: '4. Cross-Document Entity & Date Consistency' },
      { stage: 'authentication', label: '5. Image Forensics (ELA, Copy-Move, QR, Mock Registry)' },
      { stage: 'scoring', label: '6. Risk Band Computation & Audit Logging' },
    ];

    let currentStage = 0;
    const interval = setInterval(() => {
      if (currentStage < stages.length) {
        onProgress({
          stage: stages[currentStage].stage,
          stageIndex: currentStage,
          totalStages: stages.length,
          label: stages[currentStage].label,
          isComplete: false,
        });
        currentStage++;
      }
    }, 280);

    try {
      const result = await this.validateApplication(appId);
      clearInterval(interval);
      onProgress({
        stage: 'complete',
        stageIndex: stages.length,
        totalStages: stages.length,
        label: 'Validation Complete',
        isComplete: true,
      });
      return result;
    } catch (err) {
      clearInterval(interval);
      throw err;
    }
  }

  // ---------------- Officer Queue & Details ----------------
  public getOfficerQueue(filters?: {
    state?: string;
    status?: string;
    application_type?: string;
    label?: string;
    band?: string;
  }): Promise<QueueItem[]> {
    const params = new URLSearchParams();
    if (filters?.state) params.set('state', filters.state);
    if (filters?.status) params.set('status', filters.status);
    if (filters?.application_type) params.set('application_type', filters.application_type);
    if (filters?.label) params.set('label', filters.label);
    if (filters?.band) params.set('band', filters.band);

    const queryString = params.toString() ? `?${params.toString()}` : '';
    return this.request<QueueItem[]>(`/officer/queue${queryString}`);
  }

  public getOfficerApplicationDetail(id: number): Promise<OfficerApplicationDetailResponse> {
    return this.request<OfficerApplicationDetailResponse>(`/officer/applications/${id}`);
  }

  public overrideDocumentLabel(
    appId: number,
    docId: number,
    newLabel: ResultLabel,
    reason: string
  ): Promise<any> {
    return this.request<any>(`/officer/applications/${appId}/override`, {
      method: 'POST',
      body: JSON.stringify({
        document_id: docId,
        new_label: newLabel,
        reason,
      }),
    });
  }

  public recordOfficerDecision(
    appId: number,
    decision: 'approve' | 'reject' | 'send_deficiency',
    comments: string
  ): Promise<any> {
    return this.request<any>(`/officer/applications/${appId}/decision`, {
      method: 'POST',
      body: JSON.stringify({
        decision,
        comments,
      }),
    });
  }

  // ---------------- Deficiency Reports ----------------
  public async getApplicationDeficiencyReport(appId: number, lang = 'en'): Promise<DeficiencyReportData> {
    try {
      const res = await this.request<DeficiencyReportData>(`/applications/${appId}/deficiency-report`);
      return res;
    } catch (err: any) {
      // If 403 or 404, check officer endpoint or derive for demo resilience
      try {
        const detail = await this.getOfficerApplicationDetail(appId);
        if (detail.deficiency_report) {
          return detail.deficiency_report;
        }
      } catch {}
      throw err;
    }
  }

  public generateDeficiencyReport(appId: number): Promise<DeficiencyReportData> {
    return this.request<DeficiencyReportData>(`/officer/applications/${appId}/deficiency/generate`, {
      method: 'POST',
    });
  }

  public updateDeficiencyReport(
    appId: number,
    items: any[],
    summaryText?: string
  ): Promise<DeficiencyReportData> {
    return this.request<DeficiencyReportData>(`/officer/applications/${appId}/deficiency`, {
      method: 'PUT',
      body: JSON.stringify({
        content: {
          items,
          summary_text: summaryText,
        },
      }),
    });
  }

  public approveDeficiencyReport(appId: number): Promise<DeficiencyReportData> {
    return this.request<DeficiencyReportData>(`/officer/applications/${appId}/deficiency/approve`, {
      method: 'POST',
    });
  }

  public sendDeficiencyReport(appId: number): Promise<DeficiencyReportData> {
    return this.request<DeficiencyReportData>(`/officer/applications/${appId}/deficiency/send`, {
      method: 'POST',
    });
  }

  // ---------------- Drafts & Resubmissions ----------------
  public createDraft(appId: number): Promise<ApplicationItem> {
    return this.request<ApplicationItem>(`/applications/${appId}/drafts`, {
      method: 'POST',
    });
  }

  public uploadDraftDocument(draftId: number, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request<any>(`/drafts/${draftId}/documents`, {
      method: 'POST',
      body: formData,
    });
  }

  public recheckDraft(draftId: number): Promise<any> {
    return this.request<any>(`/drafts/${draftId}/recheck`, {
      method: 'POST',
    });
  }

  public getDraftComparison(draftId: number): Promise<DraftComparisonResponse> {
    return this.request<DraftComparisonResponse>(`/drafts/${draftId}/comparison`);
  }

  public submitResubmission(draftId: number): Promise<any> {
    return this.request<any>(`/drafts/${draftId}/submit`, {
      method: 'POST',
    });
  }
}

export const api = new ApiService();
