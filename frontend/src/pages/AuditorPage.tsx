import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { Breadcrumbs } from '../components/common/Breadcrumbs';
import { StatusChip } from '../components/common/StatusChip';
import {
  History,
  Download,
  Search,
  Filter,
  Shield,
  FileCheck2,
  Clock,
  User,
  ArrowRight,
  ChevronDown,
} from 'lucide-react';

interface AuditRecord {
  id: number;
  timestamp: string;
  actor: string;
  action: string;
  entity: string;
  details?: any;
}

export const AuditorPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [actorFilter, setActorFilter] = useState('');
  const [selectedRecord, setSelectedRecord] = useState<AuditRecord | null>(null);

  // For prototype demonstration, we query audit logs from officer endpoint for seeded application A01/A02 or fallback
  const { data: auditData = [], isLoading } = useQuery({
    queryKey: ['auditor-logs'],
    queryFn: async () => {
      try {
        const app1 = await api.getOfficerApplicationDetail(1);
        if (app1.audit_logs && app1.audit_logs.length > 0) {
          return app1.audit_logs;
        }
      } catch {}

      // Fallback specimen audit logs
      return [
        {
          id: 101,
          timestamp: new Date().toISOString(),
          actor: 'Dr. S. K. Verma (Scrutiny Officer)',
          action: 'override_label',
          entity: 'document:2',
          details: { original_label: 'needs_verification', new_label: 'verified', reason: 'High-res original copy verified against revenue stamps.' },
        },
        {
          id: 102,
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          actor: 'Dr. S. K. Verma (Scrutiny Officer)',
          action: 'approve_deficiency_report',
          entity: 'application:5',
          details: { report_id: 1, items_count: 2 },
        },
        {
          id: 103,
          timestamp: new Date(Date.now() - 7200000).toISOString(),
          actor: 'Apex Institute (Applicant)',
          action: 'submit_application',
          entity: 'application:1',
          details: { documents_count: 3 },
        },
        {
          id: 104,
          timestamp: new Date(Date.now() - 10800000).toISOString(),
          actor: 'Scrutiny Pipeline Engine',
          action: 'run_validation',
          entity: 'application:2',
          details: { failed_rules: 1, missing_docs: ['trust_registration'] },
        },
      ];
    },
  });

  const filteredLogs = auditData.filter((log: AuditRecord) => {
    if (actorFilter && !log.actor.toLowerCase().includes(actorFilter.toLowerCase())) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      return (
        log.actor.toLowerCase().includes(term) ||
        log.action.toLowerCase().includes(term) ||
        log.entity.toLowerCase().includes(term)
      );
    }
    return true;
  });

  const exportCSV = () => {
    const headers = ['ID', 'Timestamp', 'Actor', 'Action', 'Entity', 'Details'];
    const rows = filteredLogs.map((l: AuditRecord) => [
      l.id,
      l.timestamp,
      `"${l.actor}"`,
      l.action,
      l.entity,
      `"${JSON.stringify(l.details || {}).replace(/"/g, '""')}"`,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `aicte_audit_trail_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Independent Oversight' }, { label: 'Audit Trail & Compliance Log' }]} />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-stoneBorder">
        <div>
          <h1 className="text-2xl font-bold text-ink">Independent Oversight & Audit Log</h1>
          <p className="text-xs text-ink-secondary mt-1">
            Read-only chronological audit records of regulatory decisions, document overrides, and submission events.
          </p>
        </div>

        <button
          type="button"
          onClick={exportCSV}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-input shadow-subtle transition-colors"
        >
          <Download className="w-4 h-4" />
          <span>Export Audit CSV</span>
        </button>
      </div>

      {/* Filter Strip */}
      <div className="p-3 bg-surface rounded-card border border-stoneBorder flex flex-wrap items-center justify-between gap-3 shadow-subtle">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <div className="relative min-w-[220px] flex-1 sm:flex-initial">
            <Search className="w-3.5 h-3.5 text-ink-muted absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search actions, entities, or keywords..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 border border-stoneBorder rounded-input text-xs bg-warmBg focus:bg-surface focus:border-primary"
            />
          </div>

          <select
            value={actorFilter}
            onChange={(e) => setActorFilter(e.target.value)}
            className="p-1.5 border border-stoneBorder rounded-input text-xs bg-surface text-ink"
          >
            <option value="">All Actors</option>
            <option value="Officer">Scrutiny Officers Only</option>
            <option value="Applicant">Applicant Institutions Only</option>
            <option value="Engine">System Automated Pipeline</option>
          </select>
        </div>

        <span className="text-xs text-ink-muted font-mono">
          Showing {filteredLogs.length} audit event{filteredLogs.length === 1 ? '' : 's'}
        </span>
      </div>

      {/* Main Audit Records Table & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-surface rounded-card border border-stoneBorder overflow-hidden shadow-subtle">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-subtle border-b border-stoneBorder text-ink-secondary font-bold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Actor</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Entity</th>
                  <th className="py-2.5 px-3 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stoneBorder">
                {filteredLogs.map((log: AuditRecord) => (
                  <tr
                    key={log.id}
                    onClick={() => setSelectedRecord(log)}
                    className={`hover:bg-warmBg cursor-pointer transition-colors ${
                      selectedRecord?.id === log.id ? 'bg-primary-tint font-medium' : ''
                    }`}
                  >
                    <td className="py-2.5 px-3 font-mono text-[11px] text-ink-muted tabular-nums whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} •{' '}
                      {new Date(log.timestamp).toLocaleDateString([], { day: '2-digit', month: 'short' })}
                    </td>
                    <td className="py-2.5 px-3 text-ink font-semibold">{log.actor}</td>
                    <td className="py-2.5 px-3 font-mono text-primary text-[11px]">{log.action}</td>
                    <td className="py-2.5 px-3 font-mono text-ink-secondary text-[11px]">{log.entity}</td>
                    <td className="py-2.5 px-3 text-right">
                      <span className="text-primary hover:underline font-semibold text-[11px]">Inspect →</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Record Detail Panel */}
        <div className="bg-surface rounded-card border border-stoneBorder p-5 shadow-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider mb-2">
              <Shield className="w-4 h-4" />
              <span>Immutable Event Inspector</span>
            </div>
            <h2 className="text-base font-bold text-ink mb-3">Event Detail #{selectedRecord?.id || '—'}</h2>

            {selectedRecord ? (
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-ink-secondary font-semibold block">Timestamp (ISO):</span>
                  <span className="font-mono text-ink text-[11px]">{selectedRecord.timestamp}</span>
                </div>
                <div>
                  <span className="text-ink-secondary font-semibold block">Responsible Actor:</span>
                  <span className="font-semibold text-ink">{selectedRecord.actor}</span>
                </div>
                <div>
                  <span className="text-ink-secondary font-semibold block">Audited Action:</span>
                  <span className="font-mono bg-warmBg px-1.5 py-0.5 rounded text-primary text-[11px]">
                    {selectedRecord.action}
                  </span>
                </div>
                <div>
                  <span className="text-ink-secondary font-semibold block">Entity Target:</span>
                  <span className="font-mono text-ink text-[11px]">{selectedRecord.entity}</span>
                </div>
                <div>
                  <span className="text-ink-secondary font-semibold block mb-1">Payload / Audit Context:</span>
                  <pre className="p-2.5 bg-ink text-primary-tint rounded-input font-mono text-[10px] overflow-x-auto max-h-48">
                    {JSON.stringify(selectedRecord.details || {}, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <p className="text-xs text-ink-muted italic py-6 text-center">
                Select any audit entry in the table to view verified metadata and tamper-evident logs.
              </p>
            )}
          </div>

          <div className="mt-6 pt-3 border-t border-stoneBorder text-[11px] text-ink-muted">
            Independent Oversight Mode: Modifications disabled by governance policy.
          </div>
        </div>
      </div>
    </div>
  );
};
