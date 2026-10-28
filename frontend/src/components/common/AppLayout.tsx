import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { Banner } from './Banner';
import { HelpDrawer } from './HelpDrawer';
import { IdleTimeoutModal } from '../../auth/IdleTimeoutModal';

export const AppLayout: React.FC = () => {
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-warmBg text-ink font-sans antialiased">
      {/* Skip to Content accessible link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-accent focus:text-stone-950 focus:rounded-input focus:font-bold"
      >
        Skip to main content
      </a>

      {/* Top Navigation Bar */}
      <Navbar onOpenHelp={() => setIsHelpOpen(true)} />

      {/* Persistent Slim Notice Banner */}
      <Banner />

      {/* App Content Body with Collapsible Sidebar */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />

        <main id="main-content" tabIndex={-1} className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 outline-none">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Global Modals & Drawers */}
      <HelpDrawer isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
      <IdleTimeoutModal />
    </div>
  );
};

