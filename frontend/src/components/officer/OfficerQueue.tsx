import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Inbox,
  AlertTriangle,
  RefreshCw,
  FileCheck2,
  Filter,
  ArrowRight,
  TrendingUp,
  Search,
  Info,
} from 'lucide-react';
import { api } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import { QueueItem } from '../../types';
import { DataTable, Column } from '../common/DataTable';
import { StatusChip } from '../common/StatusChip';
import { RiskMeter } from '../common/RiskMeter';
import { Breadcrumbs } from '../common/Breadcrumbs';

export const OfficerQueue: React.FC = () => {
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [labelFilter, setLabelFilter] = useState<string>('');
  const [bandFilter, setBandFilter] = useState<string>('');
  const [resubmissionOnly, setResubmissionOnly] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const loadQueue = async () => {
    setIsLoading(true);
    try {
      const data = await api.getOfficerQueue({
        label: labelFilter || undefined,
        band: bandFilter || undefined,
      });
      setQueue(data);
    } catch (err: any) {
      showToast('error', 'Failed to load officer queue', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [labelFilter, bandFilter]);

  // Derived filtered items for client search & resubmissions filter
  const filteredQueue = queue.filter((item) => {
    if (resubmissionOnly && !item.is_resubmission) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const matchName = item.institution_name.toLowerCase().includes(term);
      const matchApp = String(item.application_id).includes(term);
      const matchState = item.institution_state.toLowerCase().includes(term);
      if (!matchName && !matchApp && !matchState) return false;
    }
    return true;
  });

  // 4 Top Summary Tiles
  const totalWaiting = queue.length;
  const highRiskCount = queue.filter((q) => q.risk_band === 'high' || (q.risk_score && q.risk_score > 60)).length;
  const resubmissionsCount = queue.filter((q) => q.is_resubmission).length;
  const deficiencyCount = queue.filter(
    (q) => q.label === 'inconsistent' || q.label === 'possible_tampering'
  ).length;

  const columns: Column<QueueItem>[] = [
    {
      key: 'rank',
      header: 'Rank',
      sortable: true,
      className: 'w-16 font-mono font-bold text-stone-500',
      render: (item, idx) => `#${item.rank || idx + 1}`,
    },
    {
      key: 'institution_name',
      header: 'Institution & Application',
      sortable: true,
      render: (item) => (
        <div className="flex flex-col">
          <span className="font-bold text-stone-900 font-sans text-xs hover:text-primary">
            {item.institution_name}
          </span>
          <div className="flex items-center gap-2 text-[11px] text-stone-500 font-mono mt-0.5">
            <span>App #{item.application_id}</span>
            <span>•</span>
            <span>{item.institution_state}</span>
            <span>•</span>
            <span className="capitalize">{item.application_type.replace(/_/g, ' ')}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'label',
      header: 'Scrutiny Result',
      sortable: true,
      render: (item) => <StatusChip label={item.label || 'needs_verification'} size="sm" />,
    },
    {
      key: 'risk_score',
      header: 'Calculated Risk Meter',
      sortable: true,
      className: 'w-48',
      render: (item) => <RiskMeter score={item.risk_score} band={item.risk_band} size="sm" />,
    },
    {
      key: 'top_factors',
      header: 'Top Contributing Risk Factors',
      render: (item) => {
        const factors = item.top_factors || [];
        if (factors.length === 0) {
          return <span className="text-stone-400 font-mono text-[11px]">Clean Record</span>;
        }
        return (
          <div className="flex flex-wrap gap-1 max-w-xs">
            {factors.slice(0, 2).map((f, i) => (
              <span
                key={i}
                className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-stone-100 text-stone-700 border border-stoneBorder truncate"
                title={`${f.factor}: ${f.description}`}
              >
                {f.factor.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        );
      },
    },
    {
      key: 'type',
      header: 'Dossier Type',
      render: (item) =>
        item.is_resubmission ? (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-accent font-semibold px-2 py-0.5 bg-amber-50 rounded border border-amber-200">
            Resubmission #{item.parent_application_id}
          </span>
        ) : (
          <span className="text-[11px] text-stone-400 font-mono">Original</span>
        ),
    },
    {
      key: 'submission_date',
      header: 'Submission Date',
      sortable: true,
      className: 'font-mono text-stone-600 text-xs',
      render: (item) => item.submission_date || '2026-03-12',
    },
  ];

  return (
    <div className="max-w-content mx-auto p-4 sm:p-6 space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs items={[{ label: 'Scrutiny Officer' }, { label: 'Prioritized Queue' }]} />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-stoneBorder">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-primary font-sans">
            Risk-Ranked Scrutiny Queue
          </h1>
          <p className="text-xs text-stone-600 mt-0.5">
            Prioritized by calculated risk factor breakdown. Use arrow keys to navigate table rows and Enter to open.
          </p>
        </div>

        <button
          onClick={loadQueue}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-stoneBorder bg-surface hover:bg-stone-50 text-xs font-semibold text-stone-700 shadow-sm transition-colors focus-visible:ring-1"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* 4 Summary Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Tile 1 */}
        <div className="p-4 bg-surface rounded-xl border border-stoneBorder shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-stone-500 uppercase tracking-wide">
              Applications Waiting
            </span>
            <div className="text-2xl font-bold font-mono text-primary mt-1 tabular-nums">
              {totalWaiting}
            </div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-primary-light flex items-center justify-center text-primary">
            <Inbox className="w-5 h-5" />
          </div>
        </div>

        {/* Tile 2 */}
        <div className="p-4 bg-surface rounded-xl border border-stoneBorder shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-status-inconsistent-text uppercase tracking-wide">
              High Risk Priority
            </span>
            <div className="text-2xl font-bold font-mono text-status-inconsistent mt-1 tabular-nums">
              {highRiskCount}
            </div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-status-inconsistent-bg flex items-center justify-center text-status-inconsistent">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>

        {/* Tile 3 */}
        <div className="p-4 bg-surface rounded-xl border border-stoneBorder shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-stone-500 uppercase tracking-wide">
              Resubmissions
            </span>
            <div className="text-2xl font-bold font-mono text-accent mt-1 tabular-nums">
              {resubmissionsCount}
            </div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center text-accent">
            <FileCheck2 className="w-5 h-5" />
          </div>
        </div>

        {/* Tile 4 */}
        <div className="p-4 bg-surface rounded-xl border border-stoneBorder shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-stone-500 uppercase tracking-wide">
              Deficiencies Pending
            </span>
            <div className="text-2xl font-bold font-mono text-stone-900 mt-1 tabular-nums">
              {deficiencyCount}
            </div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center text-stone-700">
            <TrendingUp className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-3 bg-surface rounded-lg border border-stoneBorder flex flex-wrap items-center justify-between gap-3 shadow-sm">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {/* Search box */}
          <div className="relative min-w-[200px] flex-1 sm:flex-initial">
            <Search className="w-3.5 h-3.5 text-stone-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Filter by institution, state, or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 border border-stoneBorder rounded-md text-xs bg-surface text-stone-900 focus-visible:ring-1"
            />
          </div>

          {/* Label Filter */}
          <select
            value={labelFilter}
            onChange={(e) => setLabelFilter(e.target.value)}
            className="p-1.5 border border-stoneBorder rounded-md text-xs bg-surface text-stone-800 focus-visible:ring-1"
          >
            <option value="">All Scrutiny Labels</option>
            <option value="verified">Verified</option>
            <option value="needs_verification">Needs Verification</option>
            <option value="inconsistent">Inconsistent</option>
            <option value="possible_tampering">Possible Tampering</option>
          </select>

          {/* Risk Band Filter */}
          <select
            value={bandFilter}
            onChange={(e) => setBandFilter(e.target.value)}
            className="p-1.5 border border-stoneBorder rounded-md text-xs bg-surface text-stone-800 focus-visible:ring-1"
          >
            <option value="">All Risk Bands</option>
            <option value="low">Low Risk Band</option>
            <option value="medium">Medium Risk Band</option>
            <option value="high">High Risk Band</option>
          </select>
        </div>

        {/* Resubmissions only toggle */}
        <label className="flex items-center gap-2 text-xs font-semibold text-stone-700 select-none cursor-pointer">
          <input
            type="checkbox"
            checked={resubmissionOnly}
            onChange={(e) => setResubmissionOnly(e.target.checked)}
            className="rounded border-stone-300 text-primary focus-visible:ring-1"
          />
          <span>Resubmissions Only</span>
        </label>
      </div>

      {/* Illustrative score note */}
      <div className="p-3 bg-surface-subtle border border-stoneBorder rounded-card text-xs text-ink-secondary flex items-center gap-2 shadow-subtle">
        <Info className="w-4 h-4 text-primary flex-shrink-0" />
        <span>Illustrative score. Supports the officer's decision; does not replace it.</span>
      </div>

      {/* Main Scrutiny List Data Table */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-600">
            Prioritized Scrutiny List ({filteredQueue.length})
          </span>
          <span className="text-[11px] text-stone-400">
            Click row or press Enter to inspect full dossier
          </span>
        </div>

        <DataTable
          data={filteredQueue}
          columns={columns}
          keyExtractor={(item) => item.application_id}
          onRowClick={(item) => navigate(`/officer/applications/${item.application_id}`)}
          isLoading={isLoading}
          emptyMessage="No applications currently match your queue filters."
          defaultSortKey="risk_score"
          defaultSortDir="desc"
        />
      </div>
    </div>
  );
};
