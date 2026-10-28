import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import {
  Inbox,
  FileCheck2,
  Layers,
  ChevronLeft,
  ChevronRight,
  Shield,
  FileText,
  History,
  Sliders,
  HelpCircle,
  LayoutDashboard,
  GitCompare,
  FileWarning,
  Server,
  UserCheck,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const role = user?.role || 'institution';

  const institutionLinks = [
    { to: '/institution', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { to: '/institution/applications', label: 'My Applications', icon: <FileCheck2 className="w-4 h-4" /> },
    { to: '/help', label: 'Help & Handbook', icon: <HelpCircle className="w-4 h-4" /> },
  ];

  const officerLinks = [
    { to: '/officer', label: 'Queue', icon: <Inbox className="w-4 h-4" /> },
    { to: '/officer/queue?resubmissions=true', label: 'Resubmissions', icon: <GitCompare className="w-4 h-4" /> },
    { to: '/officer/queue?status=deficiency_sent', label: 'Reports Pending', icon: <FileWarning className="w-4 h-4" /> },
    { to: '/audit', label: 'Audit Trail', icon: <History className="w-4 h-4" /> },
    { to: '/help', label: 'Handbook Rules', icon: <HelpCircle className="w-4 h-4" /> },
  ];

  const adminLinks = [
    { to: '/admin', label: 'Admin Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { to: '/admin#rules', label: 'Handbook Rules', icon: <FileText className="w-4 h-4" /> },
    { to: '/admin#registry', label: 'Registry Connector', icon: <Server className="w-4 h-4" /> },
    { to: '/audit', label: 'System Audit Log', icon: <History className="w-4 h-4" /> },
  ];

  const auditLinks = [
    { to: '/audit', label: 'Audit Log & Export', icon: <History className="w-4 h-4" /> },
    { to: '/audit#overrides', label: 'Override History', icon: <Shield className="w-4 h-4" /> },
    { to: '/audit#decisions', label: 'Decision History', icon: <FileCheck2 className="w-4 h-4" /> },
  ];

  const links =
    role === 'officer'
      ? officerLinks
      : role === 'admin'
      ? adminLinks
      : role === 'audit'
      ? auditLinks
      : institutionLinks;

  return (
    <aside
      className={`sidebar-container hidden md:flex flex-col border-r border-stoneBorder bg-surface transition-all duration-200 select-none flex-shrink-0 ${
        collapsed ? 'w-14' : 'w-60'
      }`}
      aria-label="Sidebar Navigation"
    >
      {/* Sidebar Top Header & Collapse Toggle */}
      <div className="h-12 flex items-center justify-between px-3 border-b border-stoneBorder bg-surface-subtle">
        {!collapsed && (
          <span className="text-[11px] font-bold uppercase tracking-wider text-ink-secondary">
            {role.toUpperCase()} PORTAL
          </span>
        )}
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded-input text-ink-muted hover:text-ink hover:bg-stoneBorder/50 transition-colors ml-auto"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Nav items */}
      <nav className="flex-1 p-2 space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/institution' || link.to === '/officer' || link.to === '/admin' || link.to === '/audit'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 text-xs font-semibold rounded-input relative transition-colors ${
                isActive
                  ? 'bg-primary-tint text-primary font-bold'
                  : 'text-ink-secondary hover:text-ink hover:bg-warmBg'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {/* Left accent bar for active item */}
                {isActive && (
                  <span
                    className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-accent rounded-r"
                    aria-hidden="true"
                  />
                )}
                <span className={`flex-shrink-0 ${isActive ? 'text-primary' : 'text-ink-muted'}`}>
                  {link.icon}
                </span>
                {!collapsed && <span className="truncate">{link.label}</span>}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer Specimen Indicator */}
      {!collapsed && (
        <div className="p-3 border-t border-stoneBorder bg-surface-subtle text-[11px] text-ink-secondary">
          <p className="font-semibold text-ink">AICTE Scrutiny v2.4</p>
          <p className="text-[10px] text-ink-muted mt-0.5">Prototype Specimen Engine</p>
        </div>
      )}
    </aside>
  );
};
