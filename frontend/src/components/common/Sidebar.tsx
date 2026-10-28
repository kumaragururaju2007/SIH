import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
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
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { currentUser } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const isOfficer = currentUser.role === 'officer';

  const officerLinks = [
    { to: '/officer/queue', label: 'Scrutiny Queue', icon: <Inbox className="w-4 h-4" /> },
    { to: '/help', label: 'Help & Handbook', icon: <HelpCircle className="w-4 h-4" /> },
    { to: '/design', label: 'Design System', icon: <Layers className="w-4 h-4" /> },
  ];

  const institutionLinks = [
    { to: '/institution/applications', label: 'Applications', icon: <FileCheck2 className="w-4 h-4" /> },
    { to: '/help', label: 'Help & Handbook', icon: <HelpCircle className="w-4 h-4" /> },
    { to: '/design', label: 'Design System', icon: <Layers className="w-4 h-4" /> },
  ];

  const links = isOfficer ? officerLinks : institutionLinks;

  return (
    <aside
      className={`hidden md:flex flex-col border-r border-stoneBorder bg-surface transition-all duration-200 select-none ${
        collapsed ? 'w-14' : 'w-56'
      }`}
      aria-label="Sidebar Navigation"
    >
      {/* Sidebar Top Toggle */}
      <div className="h-10 flex items-center justify-end px-3 border-b border-stoneBorder">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded text-stone-400 hover:text-stone-700 hover:bg-stone-100 focus-visible:ring-1"
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
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-md text-xs font-semibold transition-colors ${
                isActive
                  ? 'bg-primary text-white shadow-sm'
                  : 'text-stone-700 hover:bg-stone-100 hover:text-stone-900'
              }`
            }
            title={collapsed ? link.label : undefined}
          >
            <span className="flex-shrink-0" aria-hidden="true">
              {link.icon}
            </span>
            {!collapsed && <span className="truncate">{link.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Sidebar Footer info */}
      {!collapsed && (
        <div className="p-3 border-t border-stoneBorder bg-stone-50/50 text-[11px] text-stone-500">
          <div className="font-semibold text-stone-700 truncate">
            {isOfficer ? 'AICTE Scrutiny System' : currentUser.institutionName || 'Institution Mode'}
          </div>
          <div className="font-mono text-stone-600 mt-0.5">v0.1.0 • Specimen</div>
        </div>
      )}
    </aside>
  );
};
