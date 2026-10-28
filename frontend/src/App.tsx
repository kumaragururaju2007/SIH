import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './auth/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { I18nProvider } from './i18n';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppLayout } from './components/common/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { DesignSystemPage } from './pages/DesignSystemPage';
import { HelpPage } from './pages/HelpPage';
import { AdminPage } from './pages/AdminPage';
import { AuditorPage } from './pages/AuditorPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { InstitutionDashboard } from './components/institution/InstitutionDashboard';
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

const RootRedirect: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }
  const dest =
    user.role === 'institution'
      ? '/institution'
      : user.role === 'officer'
      ? '/officer'
      : user.role === 'admin'
      ? '/admin'
      : '/audit';
  return <Navigate to={dest} replace />;
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <BrowserRouter>
          <AuthProvider>
            <ToastProvider>
              <Routes>
                {/* Public Authentication Route */}
                <Route path="/login" element={<LoginPage />} />

                {/* Root Route Redirect */}
                <Route path="/" element={<RootRedirect />} />

                {/* Authenticated App Shell Layout */}
                <Route element={<AppLayout />}>
                  {/* Public Help & Design Pages reachable within app */}
                  <Route path="/help" element={<HelpPage />} />
                  <Route path="/design" element={<DesignSystemPage />} />

                  {/* Institution Portal Protected Routes */}
                  <Route
                    path="/institution"
                    element={
                      <ProtectedRoute allowedRoles={['institution']}>
                        <InstitutionDashboard />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/institution/applications"
                    element={
                      <ProtectedRoute allowedRoles={['institution']}>
                        <InstitutionApplicationsList />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/institution/applications/:id"
                    element={
                      <ProtectedRoute allowedRoles={['institution']}>
                        <ApplicationWorkspace />
                      </ProtectedRoute>
                    }
                  />

                  {/* Officer Portal Protected Routes */}
                  <Route
                    path="/officer"
                    element={
                      <ProtectedRoute allowedRoles={['officer', 'admin']}>
                        <OfficerQueue />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/officer/queue"
                    element={
                      <ProtectedRoute allowedRoles={['officer', 'admin']}>
                        <OfficerQueue />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/officer/applications/:id"
                    element={
                      <ProtectedRoute allowedRoles={['officer', 'admin']}>
                        <OfficerApplicationDetail />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/officer/resubmission-compare/:id"
                    element={
                      <ProtectedRoute allowedRoles={['officer', 'admin']}>
                        <OfficerResubmissionCompare />
                      </ProtectedRoute>
                    }
                  />

                  {/* Administrator Portal */}
                  <Route
                    path="/admin"
                    element={
                      <ProtectedRoute allowedRoles={['admin']}>
                        <AdminPage />
                      </ProtectedRoute>
                    }
                  />

                  {/* Auditor Portal */}
                  <Route
                    path="/audit"
                    element={
                      <ProtectedRoute allowedRoles={['audit', 'admin', 'officer']}>
                        <AuditorPage />
                      </ProtectedRoute>
                    }
                  />

                  {/* 404 Catch-All */}
                  <Route path="*" element={<NotFoundPage />} />
                </Route>
              </Routes>
            </ToastProvider>
          </AuthProvider>
        </BrowserRouter>
      </I18nProvider>
    </QueryClientProvider>
  );
};

export default App;
