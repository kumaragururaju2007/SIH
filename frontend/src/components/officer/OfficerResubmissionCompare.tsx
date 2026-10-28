import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { RefreshCw, ArrowLeft, GitCompare } from 'lucide-react';
import { api } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import { DraftComparisonResponse } from '../../types';
import { BeforeAfterPanel } from '../common/BeforeAfterPanel';
import { Breadcrumbs } from '../common/Breadcrumbs';

export const OfficerResubmissionCompare: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const appId = Number(id);
  const { showToast } = useToast();

  const [comparison, setComparison] = useState<DraftComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadComparison = async () => {
    if (!appId) return;
    setIsLoading(true);
    try {
      const data = await api.getDraftComparison(appId);
      setComparison(data);
    } catch (err: any) {
      showToast('error', 'Failed to load comparison', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadComparison();
  }, [appId]);

  return (
    <div className="max-w-content mx-auto p-4 sm:p-6 space-y-6">
      <Breadcrumbs
        items={[
          { label: 'Scrutiny Officer', to: '/officer/queue' },
          { label: `Application #${appId}`, to: `/officer/applications/${appId}` },
          { label: 'Resubmission Compare' },
        ]}
      />

      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-stoneBorder">
        <div>
          <div className="flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-accent" />
            <h1 className="text-xl sm:text-2xl font-bold text-primary font-sans">
              Resubmission Differential Comparison
            </h1>
          </div>
          <p className="text-xs text-stone-600 mt-0.5">
            Side-by-side analysis of parent submission defects versus newly uploaded draft remedies.
          </p>
        </div>

        <Link
          to={`/officer/applications/${appId}`}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-stoneBorder bg-surface hover:bg-stone-50 text-xs font-semibold text-stone-700 shadow-sm transition-colors focus-visible:ring-1"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Dossier Detail</span>
        </Link>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-stone-500">
          <RefreshCw className="w-8 h-8 mx-auto animate-spin mb-2 text-primary" />
          <p className="text-xs">Evaluating resubmission delta...</p>
        </div>
      ) : comparison ? (
        <BeforeAfterPanel comparison={comparison} />
      ) : (
        <div className="p-8 text-center text-stone-500 bg-surface rounded-xl border border-stoneBorder text-xs">
          No comparison data available for this application. Ensure it is linked to a parent dossier.
        </div>
      )}
    </div>
  );
};
