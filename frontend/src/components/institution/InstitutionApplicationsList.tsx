import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, RefreshCw, AlertCircle, ArrowRight, FileText, Calendar, Building, Clock } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { useToast } from '../../context/ToastContext';
import { useI18n } from '../../i18n';
import { api } from '../../services/api';
import { ApplicationItem } from '../../types';
import { DataTable, Column } from '../common/DataTable';
import { StatusChip } from '../common/StatusChip';
import { ConfirmDialog } from '../common/ConfirmDialog';
import { Breadcrumbs } from '../common/Breadcrumbs';

export const InstitutionApplicationsList: React.FC = () => {
  const { user } = useAuth();
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
        api.getApplications(user?.institutionId),
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
  }, [user?.institutionId]);

  const handleCreateApplication = async () => {
    setIsCreating(true);
    try {
      const institutionId = user?.institutionId || 1;
      const newApp = await api.createApplication(institutionId, appType);
      showToast('success', 'Application Draft Created', `Application #${newApp.id} is ready for document upload.`);
      setShowCreateModal(false);
      navigate(`/institution/applications/${newApp.id}`);
    } catch (err: any) {
      showToast('error', 'Failed to create application', err.message);
    } finally {
      setIsCreating(false);
    }
  };

  const columns: Column<ApplicationItem>[] = [
    {
      key: 'id',
      header: 'Application ID',
      className: 'w-[160px]',
      render: (item) => (
        <div className="flex flex-col gap-1 items-start">
          <div className="flex items-center gap-1.5">
            <span className="font-mono-val font-bold text-primary text-xs bg-warmBg px-2 py-0.5 rounded border border-stoneBorder">
              #{item.id}
            </span>
          </div>
          {item.parent_application_id && (
            <span className="inline-flex items-center gap-1 text-[11px] font-bold text-accent bg-accent-tint border border-accent/30 px-1.5 py-0.2 rounded-full">
              Resubmission of #{item.parent_application_id}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'application_type',
      header: 'Category / Purpose',
      render: (item) => (
        <div className="capitalize font-semibold text-ink text-xs leading-snug">
          {item.application_type.replace(/_/g, ' ')}
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      className: 'w-[160px]',
      render: (item) => <StatusChip label={item.status} size="sm" />,
    },
    {
      key: 'risk_factors',
      header: 'Issues Flagged',
      className: 'w-[130px]',
      render: (item) => {
        const issues = item.reasons?.length || (item.label === 'inconsistent' ? 1 : 0);
        return (
          <span
            className={`font-mono-val tabular-nums text-xs font-semibold px-2 py-0.5 rounded ${issues > 0 ? 'bg-status-inconsistent-bg text-status-inconsistent-text' : 'text-ink-secondary'
              }`}
          >
            {issues > 0 ? `${issues} issue${issues > 1 ? 's' : ''}` : '0 issues'}
          </span>
        );
      },
    },
    {
      key: 'created_at',
      header: 'Last Updated',
      className: 'w-[140px]',
      render: (item) => (
        <span className="text-xs text-ink-secondary tabular-nums">
          {new Date(item.created_at).toLocaleDateString('en-GB', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
          })}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Action',
      className: 'w-[130px]',
      render: (item) => (
        <button
          onClick={() => navigate(`/institution/applications/${item.id}`)}
          className="inline-flex items-center gap-1.5 px-3 py-1 bg-warmBg hover:bg-primary hover:text-white text-primary text-xs font-semibold rounded-input border border-stoneBorder transition-colors"
        >
          <span>Workspace</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: 'Institution', to: '/institution' },
          { label: t('institution.applications', 'Approval Applications') },
        ]}
      />

      {/* Page Header with Single Main Saffron CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-stoneBorder">
        <div>
          <h1 className="text-2xl font-bold text-ink">
            {t('institution.applications', 'Approval Applications')}
          </h1>
          <p className="text-xs text-ink-secondary mt-1">
            Track statutory approval filings, run completeness checks, and inspect regulatory feedback.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadApplications}
            disabled={isLoading}
            className="p-2 border border-stoneBorder rounded-input hover:bg-warmBg text-ink-secondary transition-colors"
            title="Refresh application records"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          {/* Saffron CTA - ONE main action on this screen */}
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-stone-950 font-bold text-xs rounded-input shadow-subtle transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>{t('institution.newApplication', 'New Application')}</span>
          </button>
        </div>
      </div>

      {loadError && (
        <div className="p-4 rounded-card bg-status-inconsistent-bg border border-status-inconsistent/30 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-status-inconsistent flex-shrink-0 mt-0.5" />
          <div className="text-xs text-status-inconsistent-text">
            <strong>Error loading applications:</strong> {loadError}
          </div>
        </div>
      )}

      {/* Applications Data Table */}
      <DataTable
        columns={columns}
        data={applications}
        keyExtractor={(item) => item.id}
        isLoading={isLoading}
        emptyMessage="No applications found. Click 'New Application' to initiate an AICTE approval filing."
        onRowClick={(item) => navigate(`/institution/applications/${item.id}`)}
      />

      {/* "New Application" Modal with Dynamic Types from config */}
      {showCreateModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="new-app-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/60 backdrop-blur-sm animate-fade-in"
        >
          <div className="bg-surface rounded-card border border-stoneBorder p-6 max-w-md w-full shadow-modal">
            <h3 id="new-app-title" className="text-base font-bold text-ink mb-1">
              {t('institution.createNewApplication', 'Create New Approval Application')}
            </h3>
            <p className="text-xs text-ink-secondary mb-4 leading-relaxed">
              Select the Approval Process Handbook approval track and target submission date for {user?.institutionName || 'your institution'}.
            </p>

            <div className="space-y-4">
              <div>
                <label htmlFor="app-type-select" className="block text-xs font-semibold text-ink mb-1">
                  {t('institution.applicationType', 'Application Type')}
                </label>
                <select
                  id="app-type-select"
                  value={appType}
                  onChange={(e) => setAppType(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-surface border border-stoneBorder rounded-input text-ink focus:border-primary"
                >
                  {availableTypes.map((tItem) => (
                    <option key={tItem.key} value={tItem.key}>
                      {tItem.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="sub-date-input" className="block text-xs font-semibold text-ink mb-1">
                  {t('institution.submissionDate', 'Submission Date')}
                </label>
                <input
                  id="sub-date-input"
                  type="date"
                  value={submissionDate}
                  onChange={(e) => setSubmissionDate(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-surface border border-stoneBorder rounded-input text-ink focus:border-primary font-mono"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-5 mt-5 border-t border-stoneBorder">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-xs font-semibold text-ink-secondary hover:text-ink hover:bg-warmBg rounded-input transition-colors"
              >
                {t('institution.cancel', 'Cancel')}
              </button>
              <button
                type="button"
                disabled={isCreating}
                onClick={handleCreateApplication}
                className="px-5 py-2 text-xs font-bold bg-accent hover:bg-accent-hover text-stone-950 rounded-input shadow-subtle transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                {isCreating ? 'Creating Draft...' : t('institution.create', 'Create Application')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
