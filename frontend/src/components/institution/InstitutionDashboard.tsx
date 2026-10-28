import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../../services/api';
import { useAuth } from '../../auth/AuthContext';
import { useI18n } from '../../i18n';
import { StatusChip } from '../common/StatusChip';
import {
  Building2,
  FileText,
  AlertTriangle,
  Clock,
  ArrowRight,
  CheckCircle2,
  Calendar,
  FileCheck2,
  HelpCircle,
  Plus,
} from 'lucide-react';

export const InstitutionDashboard: React.FC = () => {
  const { user } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();

  const { data: applications = [], isLoading } = useQuery({
    queryKey: ['institution-applications', user?.institutionId],
    queryFn: () => api.getApplications(user?.institutionId),
  });

  // Calculate metrics
  const totalApps = applications.length;
  const draftApps = applications.filter((a) => a.status === 'draft').length;
  const inReviewApps = applications.filter(
    (a) => a.status === 'submitted' || a.status === 'in_review'
  ).length;
  const deficiencyApps = applications.filter((a) => a.status === 'deficiency_sent').length;

  // Latest active application for "Continue where you left off"
  const latestApp = applications[0] || null;

  return (
    <div className="space-y-6">
      {/* Top Greeting */}
      <div className="bg-surface rounded-card border border-stoneBorder p-6 shadow-subtle flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary mb-1">
            <Building2 className="w-4 h-4" />
            <span>Institution Portal</span>
          </div>
          <h1 className="text-2xl font-bold text-ink">
            Welcome, {user?.institutionName || user?.name || 'Authorized Representative'}
          </h1>
          <p className="text-sm text-ink-secondary mt-1">
            Manage your AICTE approval applications, upload compliance documents, and verify pre-submission checks.
          </p>
        </div>

        <Link
          to="/institution/applications"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-hover text-stone-950 font-bold text-sm rounded-input shadow-subtle transition-colors flex-shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>New Application</span>
        </Link>
      </div>

      {/* 4 Summary Stat Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface p-4 rounded-card border border-stoneBorder shadow-subtle">
          <div className="flex items-center justify-between text-ink-muted mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Applications</span>
            <FileText className="w-4 h-4 text-primary" />
          </div>
          <div className="text-2xl font-bold font-mono-val tabular-nums text-ink">{totalApps}</div>
          <p className="text-[11px] text-ink-secondary mt-1">On record for this institution</p>
        </div>

        <div className="bg-surface p-4 rounded-card border border-stoneBorder shadow-subtle">
          <div className="flex items-center justify-between text-ink-muted mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Draft Applications</span>
            <Clock className="w-4 h-4 text-primary" />
          </div>
          <div className="text-2xl font-bold font-mono-val tabular-nums text-ink">{draftApps}</div>
          <p className="text-[11px] text-ink-secondary mt-1">In progress before official submit</p>
        </div>

        <div className="bg-surface p-4 rounded-card border border-stoneBorder shadow-subtle">
          <div className="flex items-center justify-between text-ink-muted mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Awaiting Officer</span>
            <Clock className="w-4 h-4 text-accent" />
          </div>
          <div className="text-2xl font-bold font-mono-val tabular-nums text-ink">{inReviewApps}</div>
          <p className="text-[11px] text-ink-secondary mt-1">Under official scrutiny queue</p>
        </div>

        <div className="bg-surface p-4 rounded-card border border-stoneBorder shadow-subtle">
          <div className="flex items-center justify-between text-ink-muted mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Issues to Fix</span>
            <AlertTriangle className="w-4 h-4 text-status-inconsistent" />
          </div>
          <div className="text-2xl font-bold font-mono-val tabular-nums text-status-inconsistent-text">
            {deficiencyApps}
          </div>
          <p className="text-[11px] text-ink-secondary mt-1">Deficiency notices pending draft fix</p>
        </div>
      </div>

      {/* "Continue where you left off" Card */}
      {latestApp && (
        <div className="bg-surface rounded-card border-2 border-primary/20 p-6 shadow-subtle">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-primary text-white uppercase tracking-wider">
                Continue Where You Left Off
              </span>
              <span className="text-xs text-ink-muted font-mono">
                Application #{latestApp.id}
              </span>
            </div>
            <StatusChip label={latestApp.status} size="sm" />
          </div>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mt-2">
            <div>
              <h3 className="text-base font-bold text-ink capitalize">
                {latestApp.application_type.replace(/_/g, ' ')}
              </h3>
              <p className="text-xs text-ink-secondary mt-1">
                Status: <strong className="capitalize">{latestApp.status.replace(/_/g, ' ')}</strong> • Created: {new Date(latestApp.created_at).toLocaleDateString()}
              </p>
            </div>

            <button
              type="button"
              onClick={() => navigate(`/institution/applications/${latestApp.id}`)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-input transition-colors self-start md:self-auto"
            >
              <span>Resume Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Recent Activity Timeline & Quick Guidance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-surface rounded-card border border-stoneBorder p-6 shadow-subtle">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-stoneBorder">
            <h3 className="text-base font-bold text-ink">Recent Submission Activity</h3>
            <Link
              to="/institution/applications"
              className="text-xs font-semibold text-primary hover:underline"
            >
              View all applications →
            </Link>
          </div>

          {applications.length > 0 ? (
            <div className="space-y-4">
              {applications.slice(0, 4).map((app) => (
                <div
                  key={app.id}
                  className="p-3.5 rounded-input bg-surface-subtle border border-stoneBorder flex items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary-tint text-primary font-bold flex items-center justify-center font-mono text-xs">
                      #{app.id}
                    </div>
                    <div>
                      <h4 className="font-semibold text-ink capitalize">
                        {app.application_type.replace(/_/g, ' ')}
                      </h4>
                      <p className="text-[11px] text-ink-muted">
                        Updated {new Date(app.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <StatusChip label={app.status} size="sm" />
                    <button
                      type="button"
                      onClick={() => navigate(`/institution/applications/${app.id}`)}
                      className="text-primary hover:text-primary-hover font-bold text-xs"
                    >
                      Open →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-ink-muted text-xs">
              No recent applications recorded. Click "New Application" to initiate.
            </div>
          )}
        </div>

        {/* Quick Guidance Box */}
        <div className="bg-surface-subtle rounded-card border border-stoneBorder p-6 shadow-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider mb-2">
              <HelpCircle className="w-4 h-4" />
              <span>Compliance Checklist</span>
            </div>
            <h3 className="text-sm font-bold text-ink mb-2">Approval Norms Guidance</h3>
            <p className="text-xs text-ink-secondary leading-relaxed mb-4">
              AICTE approval requirements depend on application category. Ensure land deed, building plan, and fire safety certificate match trust entities exactly.
            </p>
            <ul className="text-xs text-ink-secondary space-y-2">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-status-verified flex-shrink-0 mt-0.5" />
                <span>Pre-submission checks can be run safely multiple times.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-status-verified flex-shrink-0 mt-0.5" />
                <span>Deficiencies allow creating draft copies without altering originals.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-status-verified flex-shrink-0 mt-0.5" />
                <span>AICTE officers make all official final approval decisions.</span>
              </li>
            </ul>
          </div>

          <Link
            to="/help"
            className="mt-6 text-xs text-primary font-bold hover:underline inline-flex items-center gap-1"
          >
            <span>Read full Handbook guidance</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
};

