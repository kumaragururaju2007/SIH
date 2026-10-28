import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { I18nProvider } from './i18n';
import { Navbar } from './components/common/Navbar';
import { Sidebar } from './components/common/Sidebar';
import { Banner } from './components/common/Banner';
import { HelpDrawer } from './components/common/HelpDrawer';
import { LandingPage } from './pages/LandingPage';
import { DesignSystemPage } from './pages/DesignSystemPage';
import { HelpPage } from './pages/HelpPage';
import { InstitutionApplicationsList } from './components/institution/InstitutionApplicationsList';
import { ApplicationWorkspace } from './components/institution/ApplicationWorkspace';
import { OfficerQueue } from './components/officer/OfficerQueue';
import { OfficerApplicationDetail } from './components/officer/OfficerApplicationDetail';
import { OfficerResubmissionCompare } from './components/officer/OfficerResubmissionCompare';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <AuthProvider>
          <ToastProvider>
            <BrowserRouter>
              <div className="min-h-screen flex flex-col bg-warmBg text-stone-900 font-sans antialiased">
                {/* Skip to Content accessible link */}
                <a
                  href="#main-content"
                  className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-accent focus:text-white focus:rounded focus:font-semibold"
                >
                  Skip to main content
                </a>

                {/* Top Navigation */}
                <Navbar onOpenHelp={() => setIsHelpOpen(true)} />

                {/* Persistent Slim Banner */}
                <Banner />

                {/* App Content Body with Collapsible Sidebar */}
                <div className="flex-1 flex overflow-hidden">
                  <Sidebar />

                  <main id="main-content" className="flex-1 overflow-y-auto">
                    <Routes>
                      {/* Landing / Role Chooser */}
                      <Route path="/" element={<LandingPage />} />

                      {/* Design System Showcase */}
                      <Route path="/design" element={<DesignSystemPage />} />

                      {/* Help & Guidelines Page */}
                      <Route path="/help" element={<HelpPage />} />

                      {/* Institution Portal Routes */}
                      <Route path="/institution/applications" element={<InstitutionApplicationsList />} />
                      <Route path="/institution/applications/:id" element={<ApplicationWorkspace />} />

                      {/* Officer Workstation Routes */}
                      <Route path="/officer/queue" element={<OfficerQueue />} />
                      <Route path="/officer/applications/:id" element={<OfficerApplicationDetail />} />
                      <Route path="/officer/applications/:id/compare" element={<OfficerResubmissionCompare />} />

                      {/* Fallback */}
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                  </main>
                </div>

                {/* Persistent Help Drawer */}
                <HelpDrawer isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
              </div>
            </BrowserRouter>
          </ToastProvider>
        </AuthProvider>
      </I18nProvider>
    </QueryClientProvider>
  );
};

export default App;
