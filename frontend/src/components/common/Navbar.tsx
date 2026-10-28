import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { useI18n } from '../../i18n';
import { Wordmark } from './Wordmark';
import {
  Search,
  Bell,
  LogOut,
  ChevronDown,
  Building2,
  UserCheck,
  ShieldCheck,
  HelpCircle,
  FileText,
  CheckCircle2,
  Clock,
  Layers,
} from 'lucide-react';

interface NavbarProps {
  onOpenHelp?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenHelp }) => {
  const { user, logout } = useAuth();
  const { language, setLanguage, t } = useI18n();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const notifRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const isOfficer = user?.role === 'officer' || user?.role === 'admin';

  // Mock notifications list
  const mockNotifications = [
    {
      id: 1,
      title: 'Deficiency Report Dispatched',
      desc: 'Application A05 deficiency notice delivered to Horizon Institute.',
      time: '12m ago',
      read: false,
    },
    {
      id: 2,
      title: 'Resubmission Received',
      desc: 'Corrected deed uploaded for Application A05 (Draft #151).',
      time: '1h ago',
      read: false,
    },
    {
      id: 3,
      title: 'Config Validation Succeeded',
      desc: 'All 24 Approval Process Handbook rules loaded cleanly.',
      time: '3h ago',
      read: true,
    },
  ];

  // Close dropdowns on outside click
  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    const q = searchQuery.trim().toLowerCase();
    // If input is like "2" or "a02"
    if (q.startsWith('a') && !isNaN(Number(q.slice(1)))) {
      navigate(`/officer/applications/${Number(q.slice(1))}`);
    } else if (!isNaN(Number(q))) {
      navigate(`/officer/applications/${Number(q)}`);
    } else {
      navigate(`/officer/queue?state=${encodeURIComponent(q)}`);
    }
  };

  const roleBadges: Record<string, { label: string; bg: string; text: string }> = {
    institution: { label: 'Institution', bg: 'bg-primary-tint', text: 'text-primary' },
    officer: { label: 'Scrutiny Officer', bg: 'bg-primary-tint', text: 'text-primary' },
    admin: { label: 'Administrator', bg: 'bg-amber-100', text: 'text-amber-900' },
    audit: { label: 'Auditor', bg: 'bg-stone-200', text: 'text-stone-900' },
  };

  const currentBadge = (user && roleBadges[user.role]) || {
    label: user?.role || 'User',
    bg: 'bg-stone-100',
    text: 'text-stone-800',
  };

  return (
    <header className="bg-surface border-b border-stoneBorder sticky top-0 z-30 shadow-subtle no-print">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
        {/* Brand Wordmark with inline geometric mark */}
        <div className="flex items-center gap-3">
          <Link
            to={
              user?.role === 'institution'
                ? '/institution'
                : user?.role === 'officer'
                ? '/officer'
                : user?.role === 'admin'
                ? '/admin'
                : '/audit'
            }
            className="flex items-center hover:opacity-95 focus-visible:ring-2 focus-visible:ring-accent rounded p-1"
            aria-label="DocValidate Home"
          >
            <Wordmark size="md" />
          </Link>
          <span className="hidden sm:inline-block h-4 w-px bg-stoneBorder" />
          <span className="hidden md:inline-block text-xs text-ink-muted font-medium">
            AICTE Scrutiny & Validation
          </span>
        </div>

        {/* Global Search (Officer and Admin only) */}
        {isOfficer && (
          <form
            onSubmit={handleSearchSubmit}
            className="hidden md:flex items-center flex-1 max-w-sm mx-4"
          >
            <div className="relative w-full">
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by ID (e.g. A02) or state..."
                aria-label="Global application search"
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-warmBg rounded-input border border-stoneBorder focus:bg-surface focus:border-primary transition-colors"
              />
              <Search className="w-3.5 h-3.5 text-ink-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </form>
        )}

        {/* Right Tools: Language, Notifications, Help, User Menu */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Design System / Component Showcase Shortcut */}
          <Link
            to="/design"
            className="hidden lg:flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-input border border-stoneBorder text-ink-secondary hover:bg-warmBg transition-colors"
            title="Design System & Component Catalog"
          >
            <Layers className="w-3.5 h-3.5 text-accent" />
            <span>Design</span>
          </Link>

          {/* Language Toggle */}
          <button
            type="button"
            onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
            aria-label={`Toggle language: ${language === 'en' ? 'EN (English)' : 'HI (Hindi)'}`}
            className="px-2.5 py-1 text-xs font-semibold rounded-input border border-stoneBorder hover:bg-warmBg text-ink transition-colors"
          >
            {language === 'en' ? 'हिन्दी' : 'English'}
          </button>

          {/* Notifications Dropdown */}
          <div ref={notifRef} className="relative">
            <button
              type="button"
              onClick={() => setShowNotifications(!showNotifications)}
              aria-label="Notifications (2 unread)"
              aria-expanded={showNotifications}
              className="p-2 rounded-input hover:bg-warmBg text-ink-secondary hover:text-ink relative transition-colors"
            >
              <Bell className="w-4 h-4" />
              <span className="w-2 h-2 rounded-full bg-accent absolute top-1.5 right-1.5 ring-2 ring-surface" />
            </button>

            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 bg-surface rounded-card border border-stoneBorder shadow-modal z-50 p-2 animate-fade-in">
                <div className="flex items-center justify-between p-2 border-b border-stoneBorder">
                  <span className="text-xs font-bold text-ink">Notifications</span>
                  <span className="text-[11px] font-mono text-ink-muted">2 unread</span>
                </div>
                <div className="divide-y divide-stoneBorder max-h-64 overflow-y-auto">
                  {mockNotifications.map((n) => (
                    <div key={n.id} className="p-2.5 hover:bg-warmBg rounded transition-colors text-xs">
                      <div className="flex items-center justify-between mb-0.5">
                        <strong className="font-semibold text-ink">{n.title}</strong>
                        <span className="text-[10px] text-ink-muted">{n.time}</span>
                      </div>
                      <p className="text-ink-secondary text-[11px] leading-snug">{n.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Help Handbook Link / Drawer Trigger */}
          <Link
            to="/help"
            aria-label="Help & Handbook guidance"
            className="p-2 rounded-input hover:bg-warmBg text-ink-secondary hover:text-ink transition-colors"
            title="Help Handbook"
          >
            <HelpCircle className="w-4 h-4" />
          </Link>

          {/* User Menu */}
          {user ? (
            <div ref={userMenuRef} className="relative">
              <button
                type="button"
                onClick={() => setShowUserMenu(!showUserMenu)}
                aria-expanded={showUserMenu}
                aria-label={`User menu for ${user.name}`}
                className="flex items-center gap-2 p-1.5 rounded-input hover:bg-warmBg border border-transparent hover:border-stoneBorder transition-colors text-left"
              >
                <div className="w-7 h-7 rounded-full bg-primary text-white font-bold text-xs flex items-center justify-center flex-shrink-0">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                <div className="hidden sm:block leading-tight">
                  <div className="text-xs font-bold text-ink truncate max-w-[140px]">
                    {user.name}
                  </div>
                  <span className={`inline-block px-1.5 py-0.2 rounded text-[10px] font-bold ${currentBadge.bg} ${currentBadge.text}`}>
                    {currentBadge.label}
                  </span>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-ink-muted" />
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-56 bg-surface rounded-card border border-stoneBorder shadow-modal z-50 p-1.5 text-xs animate-fade-in">
                  <div className="p-2.5 border-b border-stoneBorder">
                    <p className="font-semibold text-ink truncate">{user.name}</p>
                    <p className="text-[11px] text-ink-muted truncate">{user.email}</p>
                    <div className="mt-1">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${currentBadge.bg} ${currentBadge.text}`}>
                        {currentBadge.label}
                      </span>
                    </div>
                  </div>

                  <div className="py-1">
                    <Link
                      to={user.role === 'institution' ? '/institution' : '/officer'}
                      onClick={() => setShowUserMenu(false)}
                      className="block px-2.5 py-1.5 rounded hover:bg-warmBg text-ink"
                    >
                      Dashboard
                    </Link>
                    <Link
                      to="/help"
                      onClick={() => setShowUserMenu(false)}
                      className="block px-2.5 py-1.5 rounded hover:bg-warmBg text-ink"
                    >
                      Documentation & Rules
                    </Link>
                  </div>

                  <div className="pt-1 border-t border-stoneBorder">
                    <button
                      type="button"
                      onClick={() => {
                        setShowUserMenu(false);
                        logout('user_initiated');
                      }}
                      className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded hover:bg-status-inconsistent-bg text-status-inconsistent-text font-medium text-left"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Sign out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <Link
              to="/login"
              className="px-3 py-1.5 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-input transition-colors"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
