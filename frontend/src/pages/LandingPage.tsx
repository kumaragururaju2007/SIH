import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n } from '../i18n';
import { Building2, ShieldCheck, ArrowRight, ShieldAlert, CheckCircle2 } from 'lucide-react';

export const LandingPage: React.FC = () => {
  const { currentUser, institutions, switchRole } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();

  const [selectedRole, setSelectedRole] = useState<'institution' | 'officer'>('institution');
  const [selectedInstId, setSelectedInstId] = useState<number>(
    institutions.length > 0 ? institutions[0].id : 1
  );
  const [officerName, setOfficerName] = useState('Dr. S. K. Verma (Scrutiny Officer)');

  const handleEnterPortal = () => {
    if (selectedRole === 'institution') {
      switchRole('institution', selectedInstId);
      navigate('/institution/applications');
    } else {
      switchRole('officer');
      navigate('/officer/queue');
    }
  };

  return (
    <div className="min-h-[calc(100vh-80px)] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 max-w-content mx-auto">
      {/* Title & Introduction */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-100 border border-stoneBorder text-primary font-mono text-xs font-semibold mb-4">
          <div className="w-2 h-2 rounded-full bg-accent" />
          SPECIMEN PROTOTYPE • AICTE VALIDATOR
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-primary font-sans tracking-tight">
          DocValidate Workstation
        </h1>
        <p className="mt-3 text-sm text-stone-600 leading-relaxed font-sans">
          Calm, explainable, and deterministic verification of educational institution approval documents.
          Designed for scrutiny officers reading dense records and institution applicants fixing deficiencies.
        </p>
      </div>

      {/* Two Large Role Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto w-full mb-8">
        {/* Card 1: Institution */}
        <div
          onClick={() => setSelectedRole('institution')}
          className={`cursor-pointer rounded-xl border p-6 flex flex-col justify-between transition-all bg-surface ${
            selectedRole === 'institution'
              ? 'border-primary ring-2 ring-primary shadow-overlay'
              : 'border-stoneBorder hover:border-stone-400'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-primary-light flex items-center justify-center text-primary">
                <Building2 className="w-6 h-6" />
              </div>
              {selectedRole === 'institution' && (
                <CheckCircle2 className="w-5 h-5 text-primary" />
              )}
            </div>

            <button
              type="button"
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedRole('institution');
              }}
              className="w-full text-left focus-visible:ring-1 rounded p-0.5"
              aria-pressed={selectedRole === 'institution'}
            >
              <h2 className="text-lg font-bold text-stone-900 font-sans">
                Institution Applicant
              </h2>
            </button>
            <p className="text-xs text-stone-600 mt-1.5 leading-relaxed">
              Upload mandatory land, building, and fire safety deeds. Run self-scrutiny checks, inspect
              pre-submission issues, and upload draft replacements to fix deficiencies.
            </p>

            {/* Institution Selector */}
            <div className="mt-5 space-y-1.5" onClick={(e) => e.stopPropagation()}>
              <label htmlFor="landing-inst" className="text-xs font-semibold text-stone-700 block">
                Choose Registered Applicant:
              </label>
              <select
                id="landing-inst"
                value={selectedInstId}
                onChange={(e) => setSelectedInstId(Number(e.target.value))}
                className="w-full p-2.5 border border-stoneBorder rounded-md text-xs bg-surface text-stone-900 focus-visible:ring-1"
              >
                {institutions.map((inst) => (
                  <option key={inst.id} value={inst.id}>
                    {inst.name} ({inst.state})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-stoneBorder text-[11px] text-stone-600 font-mono">
            Access: Self-Check • Draft Fix • Resubmission
          </div>
        </div>

        {/* Card 2: Scrutiny Officer */}
        <div
          onClick={() => setSelectedRole('officer')}
          className={`cursor-pointer rounded-xl border p-6 flex flex-col justify-between transition-all bg-surface ${
            selectedRole === 'officer'
              ? 'border-primary ring-2 ring-primary shadow-overlay'
              : 'border-stoneBorder hover:border-stone-400'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-amber-50 flex items-center justify-center text-primary">
                <ShieldCheck className="w-6 h-6" />
              </div>
              {selectedRole === 'officer' && (
                <CheckCircle2 className="w-5 h-5 text-primary" />
              )}
            </div>

            <button
              type="button"
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedRole('officer');
              }}
              className="w-full text-left focus-visible:ring-1 rounded p-0.5"
              aria-pressed={selectedRole === 'officer'}
            >
              <h2 className="text-lg font-bold text-stone-900 font-sans">
                Scrutiny Officer
              </h2>
            </button>
            <p className="text-xs text-stone-600 mt-1.5 leading-relaxed">
              Prioritized risk-ranked scrutiny queue. In-depth document inspection with ELA forensic overlays,
              side-by-side consistency comparisons, deficiency authoring, and audit logs.
            </p>

            {/* Officer Name Input */}
            <div className="mt-5 space-y-1.5" onClick={(e) => e.stopPropagation()}>
              <label htmlFor="officer-name" className="text-xs font-semibold text-stone-700 block">
                Officer Identity:
              </label>
              <input
                id="officer-name"
                type="text"
                value={officerName}
                onChange={(e) => setOfficerName(e.target.value)}
                className="w-full p-2.5 border border-stoneBorder rounded-md text-xs bg-surface text-stone-900 focus-visible:ring-1"
                placeholder="Enter officer designation"
              />
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-stoneBorder text-[11px] text-stone-600 font-mono">
            Access: Risk Queue • Forensics • Override • Decision
          </div>
        </div>
      </div>

      {/* Enter Button CTA */}
      <div className="flex flex-col items-center gap-3">
        <button
          onClick={handleEnterPortal}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-bold bg-accent hover:bg-accent-hover text-stone-950 shadow-sm transition-all focus-visible:ring-2"
        >
          <span>
            Enter {selectedRole === 'institution' ? 'Institution Portal' : 'Officer Workstation'}
          </span>
          <ArrowRight className="w-4 h-4 text-stone-950" />
        </button>

        <p className="text-[11px] text-stone-600 flex items-center gap-1.5">
          <ShieldAlert className="w-3.5 h-3.5 text-stone-500" />
          <span>Demo auth only — all documents and scores are synthetic prototype values.</span>
        </p>
      </div>
    </div>
  );
};
