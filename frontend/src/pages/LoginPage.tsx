import React, { useState, useRef, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { UserRole, DEMO_ACCOUNTS, DemoAccount } from '../auth/authService';
import { useI18n } from '../i18n';
import { Wordmark } from '../components/common/Wordmark';
import { Banner } from '../components/common/Banner';
import {
  Building2,
  UserCheck,
  ShieldCheck,
  FileCheck2,
  Layers,
  FileText,
  RefreshCw,
  Eye,
  EyeOff,
  CheckCircle2,
  Lock,
  ArrowRight,
  ExternalLink,
  HelpCircle,
  AlertCircle,
  Loader2,
  Sliders,
  FileSearch,
} from 'lucide-react';

const loginSchema = z.object({
  identifier: z.string().min(1, 'Email or User ID is required'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, user } = useAuth();
  const { t, language, setLanguage } = useI18n();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [activeRole, setActiveRole] = useState<UserRole>('institution');
  const [showOtherRoles, setShowOtherRoles] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [showPrivacyModal, setShowPrivacyModal] = useState(false);

  const identifierRef = useRef<HTMLInputElement>(null);

  // If already authenticated, redirect to role home
  useEffect(() => {
    if (isAuthenticated && user) {
      const returnUrl = searchParams.get('returnUrl');
      if (returnUrl && !returnUrl.includes('/login')) {
        navigate(returnUrl, { replace: true });
      } else {
        const dest =
          user.role === 'institution'
            ? '/institution'
            : user.role === 'officer'
            ? '/officer'
            : user.role === 'admin'
            ? '/admin'
            : '/audit';
        navigate(dest, { replace: true });
      }
    }
  }, [isAuthenticated, user, navigate, searchParams]);

  const {
    register,
    handleSubmit,
    setValue,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      identifier: '',
      password: '',
      rememberMe: false,
    },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setAuthError(null);
    try {
      const loggedUser = await login(
        values.identifier,
        values.password,
        activeRole,
        values.rememberMe
      );

      const returnUrl = searchParams.get('returnUrl');
      if (returnUrl && !returnUrl.includes('/login')) {
        navigate(returnUrl, { replace: true });
      } else {
        const target =
          loggedUser.role === 'institution'
            ? '/institution'
            : loggedUser.role === 'officer'
            ? '/officer'
            : loggedUser.role === 'admin'
            ? '/admin'
            : '/audit';
        navigate(target, { replace: true });
      }
    } catch (err: any) {
      setAuthError(err.message || 'Authentication failed. Please verify credentials.');
      setFocus('identifier');
    }
  };

  const handleDemoFill = (account: DemoAccount) => {
    setActiveRole(account.role);
    if (account.role === 'admin' || account.role === 'audit') {
      setShowOtherRoles(true);
    }
    setValue('identifier', account.email);
    setValue('password', account.password);
    setAuthError(null);
  };

  const roleDescriptions: Record<UserRole, string> = {
    institution: t('login.roleDescInst', 'Upload deeds, run pre-submission checks, view deficiency feedback, and submit resubmissions.'),
    officer: t('login.roleDescOfficer', 'Review risk-ranked applications, inspect forensics & ELA heatmaps, verify cross-checks, and approve reports.'),
    admin: t('login.roleDescAdmin', 'Manage handbook document rules, trigger config reloads, and monitor registry health.'),
    audit: t('login.roleDescAudit', 'Inspect tamper-evident audit trails, override logs, and decision timelines.'),
  };

  return (
    <div className="min-h-screen bg-warmBg flex flex-col font-sans">
      <Banner />

      <main className="flex-1 flex flex-col lg:flex-row w-full max-w-7xl mx-auto items-stretch my-auto p-4 md:p-8 gap-8">
        {/* Left Panel: Ink-Blue Authoritative Brand Showcase (Desktop ~45%) */}
        <div className="lg:w-[45%] bg-primary rounded-card text-white p-8 md:p-12 flex flex-col justify-between relative overflow-hidden shadow-subtle border border-primary-hover">
          {/* Subtle SVG geometric line background pattern */}
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none opacity-5"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <defs>
              <pattern id="grid-pattern" width="48" height="48" patternUnits="userSpaceOnUse">
                <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#FFFFFF" strokeWidth="1" />
                <circle cx="24" cy="24" r="2" fill="#FFFFFF" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid-pattern)" />
          </svg>

          <div className="relative z-10">
            {/* Wordmark in white */}
            <div className="mb-8">
              <Wordmark size="lg" variant="light" />
              <div className="mt-2 text-xs font-mono tracking-wider text-accent-tint/80 uppercase">
                AICTE Regulatory Compliance & Scrutiny Engine
              </div>
            </div>

            {/* Headline & supporting text */}
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white leading-tight mb-4">
              Faster, fairer document review for institution approvals.
            </h1>
            <p className="text-sm md:text-base text-primary-tint/90 leading-relaxed mb-8">
              Checks completeness, authenticity and compliance, ranks applications by risk, and helps institutions fix problems before rejection.
            </p>

            {/* 3 Compact feature rows with icons */}
            <div className="space-y-4 mb-10">
              <div className="flex items-start gap-3.5 bg-primary-hover/50 p-3.5 rounded-card border border-white/10">
                <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0 text-accent-tint">
                  <FileSearch className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-white">Cross-document consistency checking</h2>
                  <p className="text-xs text-primary-tint/80 mt-0.5">
                    Validates entity names, survey parcels, trust resolution dates, and addresses across deeds.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3.5 bg-primary-hover/50 p-3.5 rounded-card border border-white/10">
                <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0 text-accent-tint">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-white">Risk-ranked review queue</h2>
                  <p className="text-xs text-primary-tint/80 mt-0.5">
                    Explainable risk scores with top contributing factors prioritize complex cases for scrutiny officers.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3.5 bg-primary-hover/50 p-3.5 rounded-card border border-white/10">
                <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0 text-accent-tint">
                  <RefreshCw className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-white">Deficiency report with fix and recheck</h2>
                  <p className="text-xs text-primary-tint/80 mt-0.5">
                    Provides constructive remediation guidance and before/after differential verification.
                  </p>
                </div>
              </div>
            </div>

            {/* "How it works" 4-step strip */}
            <div className="bg-primary-hover/70 rounded-card p-4 border border-white/15">
              <div className="text-xs font-bold uppercase tracking-wider text-accent-tint mb-3">
                How It Works
              </div>
              <div className="grid grid-cols-4 gap-2 text-center text-xs">
                <div className="flex flex-col items-center">
                  <span className="w-6 h-6 rounded-full bg-white/20 text-white font-bold flex items-center justify-center mb-1">1</span>
                  <span className="font-medium text-white">Upload</span>
                </div>
                <div className="flex flex-col items-center">
                  <span className="w-6 h-6 rounded-full bg-white/20 text-white font-bold flex items-center justify-center mb-1">2</span>
                  <span className="font-medium text-white">Check</span>
                </div>
                <div className="flex flex-col items-center">
                  <span className="w-6 h-6 rounded-full bg-white/20 text-white font-bold flex items-center justify-center mb-1">3</span>
                  <span className="font-medium text-white">Review</span>
                </div>
                <div className="flex flex-col items-center">
                  <span className="w-6 h-6 rounded-full bg-accent text-stone-950 font-bold flex items-center justify-center mb-1">4</span>
                  <span className="font-medium text-white">Fix & Recheck</span>
                </div>
              </div>
            </div>
          </div>

          <div className="relative z-10 pt-8 mt-8 border-t border-white/10 text-xs text-primary-tint/70 flex justify-between items-center">
            <span>Smart India Hackathon prototype</span>
            <span className="font-mono">Synthetic data only</span>
          </div>
        </div>

        {/* Right Panel: Surface Sign-in Form (Centered max-w-440px) */}
        <div className="flex-1 flex flex-col justify-center items-center">
          <div className="w-full max-w-[440px] bg-surface rounded-card border border-stoneBorder p-6 md:p-8 shadow-subtle">
            {/* Top Bar inside Form: Title & Language Toggle */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-ink tracking-tight">
                  {t('login.signInTitle', 'Sign in')}
                </h2>
                <p className="text-xs text-ink-secondary mt-0.5">
                  {t('login.signInSubtitle', 'Choose your role to continue')}
                </p>
              </div>

              {/* Language Toggle */}
              <button
                type="button"
                onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
                aria-label={`Toggle language: current ${language.toUpperCase()}`}
                className="px-2.5 py-1 text-xs font-semibold rounded-input border border-stoneBorder hover:bg-warmBg text-ink transition-colors flex items-center gap-1.5"
              >
                <span>{language === 'en' ? 'हिन्दी' : 'English'}</span>
              </button>
            </div>

            {/* Role Selector */}
            <div className="mb-4">
              <div
                role="tablist"
                aria-label="User role selection"
                className="grid grid-cols-2 p-1 bg-warmBg rounded-input border border-stoneBorder text-xs font-semibold"
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeRole === 'institution'}
                  onClick={() => {
                    setActiveRole('institution');
                    setAuthError(null);
                  }}
                  className={`py-2 px-3 rounded-sm flex items-center justify-center gap-2 transition-all ${
                    activeRole === 'institution'
                      ? 'bg-surface text-primary font-bold shadow-subtle border border-stoneBorder'
                      : 'text-ink-secondary hover:text-ink'
                  }`}
                >
                  <Building2 className="w-4 h-4 text-primary" aria-hidden="true" />
                  <span>{t('roles.institution', 'Institution')}</span>
                </button>

                <button
                  type="button"
                  role="tab"
                  aria-selected={activeRole === 'officer'}
                  onClick={() => {
                    setActiveRole('officer');
                    setAuthError(null);
                  }}
                  className={`py-2 px-3 rounded-sm flex items-center justify-center gap-2 transition-all ${
                    activeRole === 'officer'
                      ? 'bg-surface text-primary font-bold shadow-subtle border border-stoneBorder'
                      : 'text-ink-secondary hover:text-ink'
                  }`}
                >
                  <UserCheck className="w-4 h-4 text-primary" aria-hidden="true" />
                  <span>{t('roles.officer', 'Officer')}</span>
                </button>
              </div>

              {/* Other Roles (Admin, Auditor) Toggle */}
              <div className="mt-2 text-right">
                <button
                  type="button"
                  onClick={() => setShowOtherRoles(!showOtherRoles)}
                  className="text-xs text-primary font-medium hover:underline inline-flex items-center gap-1"
                >
                  <Sliders className="w-3 h-3" />
                  {showOtherRoles ? 'Hide administrative roles' : 'Other roles (Admin, Auditor)'}
                </button>
              </div>

              {showOtherRoles && (
                <div
                  role="tablist"
                  aria-label="Administrative roles"
                  className="grid grid-cols-2 p-1 mt-2 bg-warmBg rounded-input border border-stoneBorder text-xs font-semibold"
                >
                  <button
                    type="button"
                    role="tab"
                    aria-selected={activeRole === 'admin'}
                    onClick={() => {
                      setActiveRole('admin');
                      setAuthError(null);
                    }}
                    className={`py-1.5 px-3 rounded-sm flex items-center justify-center gap-1.5 transition-all ${
                      activeRole === 'admin'
                        ? 'bg-surface text-primary font-bold shadow-subtle border border-stoneBorder'
                        : 'text-ink-secondary hover:text-ink'
                    }`}
                  >
                    <span>Administrator</span>
                  </button>

                  <button
                    type="button"
                    role="tab"
                    aria-selected={activeRole === 'audit'}
                    onClick={() => {
                      setActiveRole('audit');
                      setAuthError(null);
                    }}
                    className={`py-1.5 px-3 rounded-sm flex items-center justify-center gap-1.5 transition-all ${
                      activeRole === 'audit'
                        ? 'bg-surface text-primary font-bold shadow-subtle border border-stoneBorder'
                        : 'text-ink-secondary hover:text-ink'
                    }`}
                  >
                    <span>Compliance Auditor</span>
                  </button>
                </div>
              )}

              {/* Dynamic One-line Role Description */}
              <div className="mt-3 p-2 bg-surface-subtle border border-stoneBorder rounded-input text-xs text-ink-secondary leading-snug">
                {roleDescriptions[activeRole]}
              </div>
            </div>

            {/* Error Summary for Screen Readers & Visual Feedback */}
            {authError && (
              <div
                role="alert"
                aria-live="assertive"
                className="mb-4 p-3 bg-status-inconsistent-bg border border-status-inconsistent/30 rounded-input flex items-start gap-2.5 text-xs text-status-inconsistent-text"
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <div>
                  <strong className="font-semibold">Sign-in Notice:</strong>
                  <p className="mt-0.5">{authError}</p>
                </div>
              </div>
            )}

            {/* Sign-in Form */}
            <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
              {/* Identifier Field */}
              <div>
                <label
                  htmlFor="identifier-input"
                  className="block text-xs font-semibold text-ink mb-1"
                >
                  {activeRole === 'institution'
                    ? 'Institution Email or Code'
                    : 'Official User ID or Gov Email'}
                </label>
                <input
                  id="identifier-input"
                  type="text"
                  autoComplete="username"
                  aria-invalid={!!errors.identifier}
                  aria-describedby={errors.identifier ? 'identifier-error' : undefined}
                  {...register('identifier')}
                  className={`w-full px-3 py-2 text-sm bg-surface rounded-input border transition-colors ${
                    errors.identifier
                      ? 'border-status-inconsistent focus:border-status-inconsistent ring-1 ring-status-inconsistent'
                      : 'border-stoneBorder hover:border-stoneBorder-strong focus:border-primary'
                  }`}
                  placeholder={
                    activeRole === 'institution'
                      ? 'apex@aicte.demo or 1-INST-001'
                      : 'officer.verma@aicte.gov.in'
                  }
                />
                {errors.identifier && (
                  <p id="identifier-error" className="text-xs text-status-inconsistent-text mt-1">
                    {errors.identifier.message}
                  </p>
                )}
              </div>

              {/* Password Field with Show/Hide Toggle */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label
                    htmlFor="password-input"
                    className="block text-xs font-semibold text-ink"
                  >
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowForgotModal(true)}
                    className="text-xs text-primary font-medium hover:underline"
                  >
                    Forgot password?
                  </button>
                </div>

                <div className="relative">
                  <input
                    id="password-input"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    aria-invalid={!!errors.password}
                    aria-describedby={errors.password ? 'password-error' : undefined}
                    {...register('password')}
                    className={`w-full pl-3 pr-10 py-2 text-sm bg-surface rounded-input border transition-colors ${
                      errors.password
                        ? 'border-status-inconsistent focus:border-status-inconsistent ring-1 ring-status-inconsistent'
                        : 'border-stoneBorder hover:border-stoneBorder-strong focus:border-primary'
                    }`}
                    placeholder="Enter password"
                  />
                  <button
                    type="button"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink p-1"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {errors.password && (
                  <p id="password-error" className="text-xs text-status-inconsistent-text mt-1">
                    {errors.password.message}
                  </p>
                )}
              </div>

              {/* Remember Me Checkbox */}
              <div className="flex items-center gap-2">
                <input
                  id="remember-me-checkbox"
                  type="checkbox"
                  {...register('rememberMe')}
                  className="w-4 h-4 rounded text-primary focus:ring-accent border-stoneBorder"
                />
                <label htmlFor="remember-me-checkbox" className="text-xs text-ink-secondary select-none">
                  Remember this device (30 days)
                </label>
              </div>

              {/* Sign In Primary Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 px-4 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-input transition-colors flex items-center justify-center gap-2 shadow-subtle disabled:opacity-70"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign in as {activeRole === 'institution' ? 'Institution' : activeRole === 'officer' ? 'Officer' : activeRole}</span>
                    <ArrowRight className="w-4 h-4" aria-hidden="true" />
                  </>
                )}
              </button>
            </form>

            {/* Divider "or" */}
            <div className="relative my-5 text-center">
              <div className="absolute inset-0 flex items-center" aria-hidden="true">
                <div className="w-full border-t border-stoneBorder" />
              </div>
              <span className="relative bg-surface px-3 text-xs text-ink-muted uppercase">or</span>
            </div>

            {/* Disabled DigiLocker Button */}
            <div className="relative">
              <button
                type="button"
                disabled
                className="w-full py-2 px-3 rounded-input border border-stoneBorder bg-surface-subtle text-ink-muted text-xs font-semibold flex items-center justify-center gap-2 cursor-not-allowed opacity-75"
              >
                <Lock className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Sign in with DigiLocker</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-primary-tint text-primary uppercase">
                  Coming soon
                </span>
              </button>
            </div>

            {/* Demo Accounts Box */}
            <div className="mt-6 pt-5 border-t border-stoneBorder">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-ink">
                  Prototype Demo Accounts
                </span>
                <span className="text-[11px] font-mono text-ink-muted">pw: demo123</span>
              </div>
              <p className="text-[11px] text-ink-secondary mb-3">
                Click any chip below to auto-fill verified credentials:
              </p>

              <div className="flex flex-wrap gap-1.5">
                {DEMO_ACCOUNTS.map((acc) => (
                  <button
                    key={acc.email}
                    type="button"
                    onClick={() => handleDemoFill(acc)}
                    className="text-xs px-2.5 py-1.5 rounded-sm bg-warmBg hover:bg-primary-tint hover:text-primary text-ink border border-stoneBorder font-medium transition-colors text-left"
                  >
                    {acc.label}
                  </button>
                ))}
              </div>

              <div className="mt-3 text-[11px] text-ink-muted leading-snug">
                Demo sign-in only. Real authentication, roles and DigiLocker are future scope.
              </div>
            </div>

            {/* Footer Links */}
            <div className="mt-6 pt-4 border-t border-stoneBorder flex items-center justify-between text-xs text-ink-muted">
              <Link to="/help" className="hover:text-primary transition-colors flex items-center gap-1">
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Help Handbook</span>
              </Link>
              <button
                type="button"
                onClick={() => setShowPrivacyModal(true)}
                className="hover:text-primary transition-colors"
              >
                Privacy note
              </button>
              <span className="font-mono text-[11px]">v2.4.0-sih</span>
            </div>
          </div>
        </div>
      </main>

      {/* Forgot Password Dialog */}
      {showForgotModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="forgot-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm"
        >
          <div className="bg-surface rounded-card border border-stoneBorder p-6 max-w-sm w-full shadow-modal">
            <h3 id="forgot-title" className="text-base font-bold text-ink mb-2">
              Password Recovery Notice
            </h3>
            <p className="text-xs text-ink-secondary leading-relaxed mb-4">
              Self-service password reset is disabled for this Smart India Hackathon prototype. Please use the pre-seeded demo accounts with password <code className="font-mono text-primary font-bold">demo123</code>.
            </p>
            <button
              type="button"
              onClick={() => setShowForgotModal(false)}
              className="w-full py-2 bg-primary text-white text-xs font-semibold rounded-input hover:bg-primary-hover"
            >
              Understood
            </button>
          </div>
        </div>
      )}

      {/* Privacy Note Dialog */}
      {showPrivacyModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="privacy-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm"
        >
          <div className="bg-surface rounded-card border border-stoneBorder p-6 max-w-md w-full shadow-modal">
            <h3 id="privacy-title" className="text-base font-bold text-ink mb-2">
              Privacy & Prototype Information
            </h3>
            <p className="text-xs text-ink-secondary leading-relaxed mb-3">
              This prototype operates entirely on synthetic specimen data generated for the AICTE approval process evaluation.
            </p>
            <ul className="text-xs text-ink-secondary space-y-1.5 list-disc list-inside mb-4">
              <li>No real institutional or citizen personally identifiable information (PII) is stored.</li>
              <li>Document forensic metrics represent algorithmic probability signals, not legal determinations.</li>
              <li>All final decisions are reserved for human scrutiny officers.</li>
            </ul>
            <button
              type="button"
              onClick={() => setShowPrivacyModal(false)}
              className="w-full py-2 bg-primary text-white text-xs font-semibold rounded-input hover:bg-primary-hover"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
