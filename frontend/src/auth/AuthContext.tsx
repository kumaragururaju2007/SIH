import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { AuthUser, UserRole, authService } from './authService';
import { useNavigate } from 'react-router-dom';

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (identifier: string, password: string, role: UserRole, rememberMe?: boolean) => Promise<AuthUser>;
  logout: (reason?: string) => void;
  stayLoggedIn: () => void;
  showIdlePrompt: boolean;
  idleSecondsLeft: number;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => {
    throw new Error('Not implemented');
  },
  logout: () => {},
  stayLoggedIn: () => {},
  showIdlePrompt: false,
  idleSecondsLeft: 60,
});

// 30 minutes idle limit (1,800,000 ms)
const IDLE_LIMIT_MS = 30 * 60 * 1000;
const WARNING_COUNTDOWN_SECONDS = 60;

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(() => authService.getSession());
  const [isLoading, setIsLoading] = useState(false);
  const [showIdlePrompt, setShowIdlePrompt] = useState(false);
  const [idleSecondsLeft, setIdleSecondsLeft] = useState(WARNING_COUNTDOWN_SECONDS);
  const navigate = useNavigate();

  const lastActivityRef = useRef<number>(Date.now());
  const countdownTimerRef = useRef<any>(null);

  const resetActivity = useCallback(() => {
    lastActivityRef.current = Date.now();
    if (showIdlePrompt) {
      setShowIdlePrompt(false);
      setIdleSecondsLeft(WARNING_COUNTDOWN_SECONDS);
      if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    }
  }, [showIdlePrompt]);

  const logout = useCallback((reason?: string) => {
    authService.logout();
    setUser(null);
    setShowIdlePrompt(false);
    if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    const search = reason ? `?reason=${encodeURIComponent(reason)}` : '';
    navigate(`/login${search}`, { replace: true });
  }, [navigate]);

  const stayLoggedIn = useCallback(() => {
    resetActivity();
  }, [resetActivity]);

  // Activity listeners
  useEffect(() => {
    if (!user) return;

    const handleUserAction = () => {
      if (!showIdlePrompt) {
        lastActivityRef.current = Date.now();
      }
    };

    window.addEventListener('mousemove', handleUserAction);
    window.addEventListener('keydown', handleUserAction);
    window.addEventListener('click', handleUserAction);
    window.addEventListener('scroll', handleUserAction);

    const idleChecker = setInterval(() => {
      if (!user) return;
      const elapsed = Date.now() - lastActivityRef.current;
      if (elapsed >= IDLE_LIMIT_MS && !showIdlePrompt) {
        setShowIdlePrompt(true);
        setIdleSecondsLeft(WARNING_COUNTDOWN_SECONDS);

        countdownTimerRef.current = setInterval(() => {
          setIdleSecondsLeft((prev) => {
            if (prev <= 1) {
              clearInterval(countdownTimerRef.current);
              logout('session_expired');
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      }
    }, 15000);

    return () => {
      window.removeEventListener('mousemove', handleUserAction);
      window.removeEventListener('keydown', handleUserAction);
      window.removeEventListener('click', handleUserAction);
      window.removeEventListener('scroll', handleUserAction);
      clearInterval(idleChecker);
      if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    };
  }, [user, showIdlePrompt, logout]);

  const login = async (
    identifier: string,
    password: string,
    role: UserRole,
    rememberMe = false
  ): Promise<AuthUser> => {
    setIsLoading(true);
    try {
      const authenticatedUser = await authService.login(identifier, password, role, rememberMe);
      setUser(authenticatedUser);
      lastActivityRef.current = Date.now();
      return authenticatedUser;
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        stayLoggedIn,
        showIdlePrompt,
        idleSecondsLeft,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

