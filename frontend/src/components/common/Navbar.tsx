import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useI18n } from '../../i18n';
import { User, HelpCircle, ArrowLeftRight, Globe, Layers } from 'lucide-react';
import { ConfirmDialog } from './ConfirmDialog';

interface NavbarProps {
  onOpenHelp: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenHelp }) => {
  const { currentUser, institutions, switchRole } = useAuth();
  const { language, setLanguage, t } = useI18n();
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [selectedRole, setSelectedRole] = useState<'institution' | 'officer'>(currentUser.role);
  const [selectedInstId, setSelectedInstId] = useState<number>(currentUser.institutionId || 1);
  const navigate = useNavigate();

  const handleRoleSwitchSubmit = () => {
    switchRole(selectedRole, selectedInstId);
    setShowRoleModal(false);
    if (selectedRole === 'officer') {
      navigate('/officer/queue');
    } else {
      navigate('/institution/applications');
    }
  };

  const toggleLanguage = () => {
    setLanguage(language === 'en' ? 'hi' : 'en');
  };

  return (
    <>
      <header className="bg-surface border-b border-stoneBorder sticky top-0 z-30 shadow-sm">
        <div className="max-w-content mx-auto px-4 h-14 flex items-center justify-between gap-4">
          {/* Brand Wordmark & Geometric Mark */}
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="flex items-center gap-2 text-primary font-bold text-lg tracking-tight hover:opacity-90 focus-visible:ring-1 p-1 rounded"
              aria-label="DocValidate Home"
            >
              {/* Geometric square with inset rotated diamond mark */}
              <div className="w-6 h-6 bg-primary rounded-sm flex items-center justify-center text-white" aria-hidden="true">
                <div className="w-2.5 h-2.5 bg-accent transform rotate-45" />
              </div>
              <span className="font-sans font-extrabold text-primary text-base">DocValidate</span>
            </Link>

            <span className="hidden sm:inline-block h-4 w-px bg-stone-300" />
            <span className="hidden md:inline-block text-xs text-stone-500 font-medium">
              Institutional Document Scrutiny
            </span>
          </div>

          {/* Right Navigation & Persona Tools */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Design System Link */}
            <Link
              to="/design"
              className="hidden lg:inline-flex items-center gap-1 text-xs font-semibold text-stone-600 hover:text-primary px-2 py-1 rounded hover:bg-stone-100 transition-colors focus-visible:ring-1"
              title="View Component Design System Showcase"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>/design</span>
            </Link>

            {/* Language Toggle (English / Hindi) */}
            <button
              onClick={toggleLanguage}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold border border-stoneBorder bg-surface hover:bg-stone-50 text-stone-700 transition-colors focus-visible:ring-1"
              aria-label={`Toggle language: ${language === 'en' ? 'EN (English)' : 'हिन्दी (Hindi)'}`}
              title="Toggle English / हिन्दी"
            >
              <Globe className="w-3.5 h-3.5 text-stone-500" />
              <span className="font-mono">{language === 'en' ? 'EN' : 'हिन्दी'}</span>
            </button>

            {/* Help Button */}
            <button
              onClick={onOpenHelp}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium text-stone-700 hover:bg-stone-100 transition-colors focus-visible:ring-1"
              aria-label="Open help guide explaining validation labels"
            >
              <HelpCircle className="w-4 h-4 text-stone-500" />
              <span className="hidden sm:inline">Help</span>
            </button>

            {/* Role Badge & Switch Button */}
            <button
              onClick={() => {
                setSelectedRole(currentUser.role);
                setSelectedInstId(currentUser.institutionId || 1);
                setShowRoleModal(true);
              }}
              className="inline-flex items-center gap-2 pl-2.5 pr-2 py-1 rounded-md border border-stoneBorder bg-stone-50 hover:bg-stone-100 transition-colors focus-visible:ring-1 text-left"
              title="Click to switch demo persona"
            >
              <div className="flex flex-col text-left">
                <span className="text-[10px] uppercase font-bold tracking-wider text-primary leading-none">
                  {currentUser.role === 'officer' ? 'Scrutiny Officer' : 'Institution Portal'}
                </span>
                <span className="text-xs font-medium text-stone-800 max-w-[140px] truncate leading-tight mt-0.5">
                  {currentUser.role === 'officer'
                    ? currentUser.officerName || 'Officer Verma'
                    : currentUser.institutionName || 'Demo Institute'}
                </span>
              </div>
              <ArrowLeftRight className="w-3.5 h-3.5 text-stone-400 ml-1 flex-shrink-0" />
            </button>
          </div>
        </div>
      </header>

      {/* Role Switcher Modal */}
      <ConfirmDialog
        isOpen={showRoleModal}
        title="Switch Demo Persona"
        message="Select whether you want to test the portal as an AICTE Scrutiny Officer or as an applicant Institution staff member."
        confirmLabel="Switch Persona"
        cancelLabel="Cancel"
        onConfirm={handleRoleSwitchSubmit}
        onCancel={() => setShowRoleModal(false)}
        variant="primary"
      >
        <div className="space-y-4 pt-2">
          {/* Role selector cards */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setSelectedRole('officer')}
              className={`p-3 rounded-lg border text-left transition-all ${
                selectedRole === 'officer'
                  ? 'border-primary bg-primary-light ring-2 ring-primary text-primary'
                  : 'border-stoneBorder hover:bg-stone-50 text-stone-700'
              }`}
            >
              <span className="text-xs font-bold uppercase tracking-wider block mb-1">
                Scrutiny Officer
              </span>
              <p className="text-[11px] text-stone-500">
                Review queue, forensic signals, cross-check consistency, and deficiency reports.
              </p>
            </button>

            <button
              type="button"
              onClick={() => setSelectedRole('institution')}
              className={`p-3 rounded-lg border text-left transition-all ${
                selectedRole === 'institution'
                  ? 'border-primary bg-primary-light ring-2 ring-primary text-primary'
                  : 'border-stoneBorder hover:bg-stone-50 text-stone-700'
              }`}
            >
              <span className="text-xs font-bold uppercase tracking-wider block mb-1">
                Institution
              </span>
              <p className="text-[11px] text-stone-500">
                Upload mandatory approval deeds, run self-checks, and fix flagged deficiencies.
              </p>
            </button>
          </div>

          {/* If institution selected, pick which seeded institution */}
          {selectedRole === 'institution' && (
            <div className="space-y-1.5 pt-1">
              <label htmlFor="inst-select" className="text-xs font-semibold text-stone-700 block">
                Select Applicant Institution:
              </label>
              <select
                id="inst-select"
                value={selectedInstId}
                onChange={(e) => setSelectedInstId(Number(e.target.value))}
                className="w-full p-2 border border-stoneBorder rounded-md text-xs bg-surface text-stone-900 focus-visible:ring-1"
              >
                {institutions.map((inst) => (
                  <option key={inst.id} value={inst.id}>
                    {inst.name} ({inst.state}) - Trust: {inst.trust_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <p className="text-[11px] text-stone-400 italic">
            Note: All institutional data and application profiles are synthetic specimen records.
          </p>
        </div>
      </ConfirmDialog>
    </>
  );
};
