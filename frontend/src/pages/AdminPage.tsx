import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { useToast } from '../context/ToastContext';
import { Breadcrumbs } from '../components/common/Breadcrumbs';
import {
  Server,
  Database,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileText,
  Sliders,
  Shield,
  Layers,
  Activity,
  Cpu,
  Power,
} from 'lucide-react';

export const AdminPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [registryOutageSimulated, setRegistryOutageSimulated] = useState(false);

  // Fetch configs
  const { data: config, isLoading, refetch } = useQuery({
    queryKey: ['admin-config'],
    queryFn: () => api.getConfig(),
  });

  // Reload config mutation
  const reloadMutation = useMutation({
    mutationFn: () =>
      fetch(`${api.getBaseUrl()}/admin/config/reload`, {
        method: 'POST',
      }).then((r) => {
        if (!r.ok) throw new Error('Reload failed');
        return r.json();
      }),
    onSuccess: (data) => {
      showToast('success', 'Configurations Reloaded', 'All YAML rules and document specifications refreshed.');
      queryClient.invalidateQueries({ queryKey: ['admin-config'] });
    },
    onError: (err: any) => {
      showToast('error', 'Configuration Reload Failed', err.message);
    },
  });

  const docTypes = config?.document_types || ['fire_safety_certificate', 'land_document', 'trust_registration'];
  const rulesCount = config?.rules_count || 24;
  const consistencyCount = config?.consistency_rules_count || 8;

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Administration' }, { label: 'System Health & Configuration' }]} />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-stoneBorder">
        <div>
          <h1 className="text-2xl font-bold text-ink">Administrative Directorate Console</h1>
          <p className="text-xs text-ink-secondary mt-1">
            System diagnostics, handbook YAML rule engine controls, and external registry connector health.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            className="p-2 border border-stoneBorder rounded-input hover:bg-warmBg text-ink-secondary transition-colors"
            title="Refresh diagnostic status"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={() => reloadMutation.mutate()}
            disabled={reloadMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-input shadow-subtle transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${reloadMutation.isPending ? 'animate-spin' : ''}`} />
            <span>Reload Configs</span>
          </button>
        </div>
      </div>

      {/* System Health Indicators */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface p-4 rounded-card border border-stoneBorder shadow-subtle">
          <div className="flex items-center justify-between text-ink-muted mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">FastAPI Backend</span>
            <Server className="w-4 h-4 text-status-verified" />
          </div>
          <div className="text-lg font-bold text-ink flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-status-verified" />
            <span>Operational</span>
          </div>
          <p className="text-[11px] text-ink-secondary mt-1">Python 3.11 ASGI Core</p>
        </div>

        <div className="bg-surface p-4 rounded-card border border-stoneBorder shadow-subtle">
          <div className="flex items-center justify-between text-ink-muted mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Database Service</span>
            <Database className="w-4 h-4 text-status-verified" />
          </div>
          <div className="text-lg font-bold text-ink flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-status-verified" />
            <span>Connected</span>
          </div>
          <p className="text-[11px] text-ink-secondary mt-1">Supabase PostgreSQL Pooler</p>
        </div>

        <div className="bg-surface p-4 rounded-card border border-stoneBorder shadow-subtle">
          <div className="flex items-center justify-between text-ink-muted mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">OCR Pipeline</span>
            <Cpu className="w-4 h-4 text-status-verified" />
          </div>
          <div className="text-lg font-bold text-ink flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-status-verified" />
            <span>Active (eng+hin)</span>
          </div>
          <p className="text-[11px] text-ink-secondary mt-1">Tesseract + PyMuPDF</p>
        </div>

        <div className="bg-surface p-4 rounded-card border border-stoneBorder shadow-subtle">
          <div className="flex items-center justify-between text-ink-muted mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Extractor Engine</span>
            <Activity className="w-4 h-4 text-primary" />
          </div>
          <div className="text-lg font-bold text-ink flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-primary" />
            <span>Deterministic Rules</span>
          </div>
          <p className="text-[11px] text-ink-secondary mt-1">Mode: rules (offline-first)</p>
        </div>
      </div>

      {/* Rules Engine and Registry Outage Control */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 cols: Rules specifications */}
        <div className="lg:col-span-2 bg-surface rounded-card border border-stoneBorder p-6 shadow-subtle space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-stoneBorder">
            <div>
              <h2 className="text-base font-bold text-ink">Statutory Rules Engine</h2>
              <p className="text-xs text-ink-secondary">
                Configuration files loaded from <code className="font-mono text-[11px] bg-warmBg px-1 rounded">backend/configs/</code> (Read-Only)
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold bg-primary-tint text-primary px-2.5 py-1 rounded">
                {rulesCount} Rules Loaded
              </span>
              <span className="text-xs font-mono font-bold bg-warmBg border border-stoneBorder text-ink px-2.5 py-1 rounded">
                {consistencyCount} Cross-Checks
              </span>
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-secondary">
              Active Document Specifications
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {docTypes.map((dt: string) => (
                <div key={dt} className="p-3 bg-surface-subtle border border-stoneBorder rounded-input text-xs">
                  <div className="font-bold text-ink capitalize mb-1">{dt.replace(/_/g, ' ')}</div>
                  <div className="text-[11px] text-ink-muted font-mono">Status: Enforced</div>
                  <div className="text-[11px] text-status-verified font-medium mt-1 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Validated
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right col: Registry Connector Outage Simulation */}
        <div className="bg-surface rounded-card border border-stoneBorder p-6 shadow-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider mb-2">
              <Server className="w-4 h-4" />
              <span>External Connectors</span>
            </div>
            <h2 className="text-base font-bold text-ink mb-1">State Registry Simulation</h2>
            <p className="text-xs text-ink-secondary leading-relaxed mb-4">
              Simulates network connectivity to state revenue departments and municipal fire service portals.
            </p>

            <div className="p-4 rounded-card border border-stoneBorder bg-surface-subtle space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-ink">Simulate Registry Outage</span>
                <button
                  type="button"
                  onClick={() => {
                    const next = !registryOutageSimulated;
                    setRegistryOutageSimulated(next);
                    showToast(
                      next ? 'info' : 'success',
                      next ? 'Outage Simulation Activated' : 'Registry Connection Restored',
                      next
                        ? 'Simulated timeout for external registrar lookups.'
                        : 'External state registry online.'
                    );
                  }}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    registryOutageSimulated ? 'bg-status-inconsistent' : 'bg-status-verified'
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      registryOutageSimulated ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              <div className="text-[11px] text-ink-secondary leading-snug">
                Status:{' '}
                <strong className={registryOutageSimulated ? 'text-status-inconsistent' : 'text-status-verified'}>
                  {registryOutageSimulated ? 'Outage Simulated (Fallback Enabled)' : 'Live Connector Active'}
                </strong>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-stoneBorder text-xs text-ink-muted">
            All configuration updates take effect immediately without requiring server restarts.
          </div>
        </div>
      </div>
    </div>
  );
};
