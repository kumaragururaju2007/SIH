import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, RefreshCw, AlertCircle, ArrowRight, FileText, Calendar, Building, Clock } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { useI18n } from '../../i18n';
import { api } from '../../services/api';
import { ApplicationItem } from '../../types';
import { DataTable, Column } from '../common/DataTable';
import { StatusChip } from '../common/StatusChip';
import { ConfirmDialog } from '../common/ConfirmDialog';
import { Breadcrumbs } from '../common/Breadcrumbs';

export const InstitutionApplicationsList: React.FC = () => {
  const { currentUser } = useAuth();
  const { showToast } = useToast();
  const { t } = useI18n();
  const navigate = useNavigate();

  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [appType, setAppType] = useState('new_institute');
  const [submissionDate, setSubmissionDate] = useState(new Date().toISOString().split('T')[0]);
  const [isCreating, setIsCreating] = useState(false);
  const [availableTypes, setAvailableTypes] = useState<Array<{ key: string; name: string }>>([
    { key: 'new_institute', name: 'New Technical Institution (Establishment)' },
    { key: 'extension_of_approval', name: 'Extension of Approval (EoA - Annual Continuation)' },
    { key: 'increase_intake', name: 'Increase in Intake / Additional Course' },
  ]);

  const loadApplications = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [data, configData] = await Promise.all([
        api.getApplications(currentUser.institutionId),
        api.getConfig().catch(() => null),
      ]);
      setApplications(data);

      if (configData && configData.application_types) {
        const typesList = Object.entries(configData.application_types).map(([k, val]: [string, any]) => ({
          key: k,
          name: typeof val === 'object' && val.name ? val.name : k.replace(/_/g, ' ').toUpperCase(),
        }));
        if (typesList.length > 0) {
          setAvailableTypes(typesList);
          setAppType(typesList[0].key);
        }
      }
    } catch (err: any) {
      setLoadError(err.message || 'Failed to load applications');
      showToast('error', 'Failed to load applications', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadApplications();
  }, [currentUser.institutionId]);

  const handleCreate = async () => {
    if (!currentUser.institutionId) {
      showToast('error', 'No institution selected');
      return;
    }
    setIsCreating(true);
    try {
      const newApp = await api.createApplication(currentUser.institutionId, appType);
      showToast('success', 'Application created', `Application #${newApp.id} initialized successfully.`);
      setShowCreateModal(false);
      navigate(`/institution/applications/${newApp.id}`);
    } catch (err: any) {
      showToast('error', 'Application creation failed', err.message);
    } finally {
      setIsCreating(false);
    }
  };

  const getIssueCount = (app: ApplicationItem): number => {
    if (!app.reasons) return 0;
    if (Array.isArray(app.reasons)) return app.reasons.length;
    if (typeof app.reasons === 'object') return Object.keys(app.reasons).length;
    return 0;
  };

  const columns: Column<ApplicationItem>[] = [
    {
      key: 'id',
      header: 'Application ID',
      sortable: true,
      className: 'w-36 font-mono font-bold text-primary',
      render: (app) => (
        <div className="flex flex-col gap-1 items-start">
          <span className="font-bold text-sm">#{app.id}</span>
          {app.parent_application_id && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-amber-50 text-accent border border-amber-200">
              Resubmission of #{app.parent_application_id}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'application_type',
      header: 'Type',
      sortable: true,
      render: (app) => (
        <span className="capitalize font-medium text-stone-800 text-xs">
          {app.application_type.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (app) => <StatusChip label={app.status} size="sm" />,
    },
    {
      key: 'issue_count',
      header: 'Issue Count',
      sortable: true,
      className: 'text-center w-28',
      render: (app) => {
        const count = getIssueCount(app);
        if (count > 0) {
          return (
            <span className="inline-flex items-center gap-1 text-xs font-mono font-bold px-2 py-0.5 rounded bg-status-inconsistent-bg text-status-inconsistent-text border border-status-inconsistent-border">
              {count} {count === 1 ? 'issue' : 'issues'}
            </span>
          );
        }
        return (
          <span className="text-xs font-mono text-stone-500">
            0 issues
          </span>
        );
      },
    },
    {
      key: 'submission_date',
      header: 'Last Updated',
      sortable: true,
      className: 'font-mono text-xs text-stone-600 w-36',
      render: (app) => {
        const dateStr = app.submission_date || app.created_at;
        try {
          return new Date(dateStr).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
          });
        } catch {
          return dateStr || 'Draft';
        }
      },
    },
    {
      key: 'actions',
      header: 'Action',
      className: 'w-24 text-right',
      render: (app) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/institution/applications/${app.id}`);
          }}
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary-hover p-1 rounded hover:bg-stone-100 transition-colors"
          aria-label={`Open application #${app.id}`}
        >
          <span>Open</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      ),
    },
  ];

  return (
    <div className="max-w-content mx-auto p-4 sm:p-6 space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs items={[{ label: 'Institution Portal' }, { label: 'Applications' }]} />

      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-stoneBorder">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-primary font-sans">
            {t('institution.applications', 'Approval Applications')}
          </h1>
          <p className="text-xs text-stone-600 mt-0.5">
            Applicant:{' '}
            <strong className="text-stone-900 font-semibold">
              {currentUser.institutionName || 'Registered Technical Institute'}
            </strong>
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-accent hover:bg-accent-hover text-stone-950 text-xs font-bold shadow-sm transition-colors focus-visible:ring-2"
          aria-label="Create new application"
        >
          <Plus className="w-4 h-4 text-stone-950" />
          <span>{t('institution.newApplication', 'New Application')}</span>
        </button>
      </div>

      {/* Error state with retry */}
      {loadError && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-xs text-red-800 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
            <span>{loadError}</span>
          </div>
          <button
            onClick={loadApplications}
            className="px-3 py-1 rounded bg-red-100 hover:bg-red-200 text-red-900 font-semibold text-xs transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Applications Data Table */}
      <DataTable
        data={applications}
        columns={columns}
        keyExtractor={(app) => app.id}
        onRowClick={(app) => navigate(`/institution/applications/${app.id}`)}
        isLoading={isLoading}
        emptyMessage="No applications found. Click 'New Application' to begin your AICTE approval dossier."
        defaultSortKey="id"
        defaultSortDir="desc"
      />

      {/* Create Application Modal */}
      <ConfirmDialog
        isOpen={showCreateModal}
        title={t('institution.createNewApplication', 'Create New Approval Application')}
        message="Initialize a new institutional application dossier. You will be able to upload required legal deeds, run pre-submission compliance checks, and submit."
        confirmLabel={t('institution.create', 'Create Application')}
        cancelLabel={t('institution.cancel', 'Cancel')}
        onConfirm={handleCreate}
        onCancel={() => setShowCreateModal(false)}
        isLoading={isCreating}
        variant="primary"
      >
        <div className="space-y-3 pt-2">
          <div>
            <label htmlFor="app-type" className="text-xs font-semibold text-stone-700 block mb-1">
              {t('institution.applicationType', 'Application Type')}:
            </label>
            <select
              id="app-type"
              value={appType}
              onChange={(e) => setAppType(e.target.value)}
              className="w-full p-2.5 border border-stoneBorder rounded-md text-xs bg-surface text-stone-900 focus-visible:ring-1"
            >
              {availableTypes.map((tItem) => (
                <option key={tItem.key} value={tItem.key}>
                  {tItem.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="sub-date" className="text-xs font-semibold text-stone-700 block mb-1">
              {t('institution.submissionDate', 'Target Submission Date')}:
            </label>
            <input
              id="sub-date"
              type="date"
              value={submissionDate}
              onChange={(e) => setSubmissionDate(e.target.value)}
              className="w-full p-2.5 border border-stoneBorder rounded-md text-xs bg-surface text-stone-900 font-mono focus-visible:ring-1"
            />
          </div>
        </div>
      </ConfirmDialog>
    </div>
  );
};
