import React from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { UserRole } from './authService';
import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { Banner } from '../components/common/Banner';

interface ProtectedRouteProps {
  allowedRoles?: UserRole[];
  children?: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const { user, isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated || !user) {
    return <Navigate to={`/login?returnUrl=${encodeURIComponent(location.pathname)}`} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // 403 Forbidden view
    const homeUrl =
      user.role === 'institution'
        ? '/institution'
        : user.role === 'officer'
        ? '/officer'
        : user.role === 'admin'
        ? '/admin'
        : '/audit';

    return (
      <div className="min-h-screen bg-warmBg flex flex-col">
        <Banner />
        <main className="flex-1 flex items-center justify-center p-6">
          <div className="bg-surface border border-stoneBorder rounded-card p-8 max-w-lg w-full text-center shadow-subtle">
            <div className="w-14 h-14 bg-status-tampering-bg text-status-tampering rounded-full flex items-center justify-center mx-auto mb-4">
              <ShieldAlert className="w-8 h-8" aria-hidden="true" />
            </div>
            <h1 className="text-2xl font-bold text-ink mb-2">403 - Access Restricted</h1>
            <p className="text-sm text-ink-secondary mb-6 leading-relaxed">
              Your signed-in account role (<strong>{user.role}</strong>) does not have authorization to access the requested route: <code className="font-mono text-xs bg-warmBg px-1.5 py-0.5 rounded">{location.pathname}</code>.
            </p>
            <Link
              to={homeUrl}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-input transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Return to Your Authorized Dashboard ({user.role})
            </Link>
          </div>
        </main>
      </div>
    );
  }

  return children ? <>{children}</> : null;
};

