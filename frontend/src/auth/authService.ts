/**
 * NOTICE: Smart India Hackathon Prototype Authorization Service.
 * This module provides prototype authentication against seeded demo accounts.
 * Real identity provider integrations (e.g. DigiLocker, e-Pramaan, OpenID Connect)
 * are planned for future scope.
 */

import { api } from '../services/api';

export type UserRole = 'institution' | 'officer' | 'admin' | 'audit';

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  institutionId?: number;
  institutionName?: string;
}

export interface DemoAccount {
  label: string;
  email: string;
  password: string;
  role: UserRole;
  name: string;
  institutionId?: number;
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    label: 'Apex Institute (Clean Record)',
    email: 'apex@aicte.demo',
    password: 'demo123',
    role: 'institution',
    name: 'Apex Institute of Technology',
    institutionId: 1,
  },
  {
    label: 'Horizon Institute (Flags/Deficiencies)',
    email: 'horizon@aicte.demo',
    password: 'demo123',
    role: 'institution',
    name: 'Horizon Institute of Engineering',
    institutionId: 2,
  },
  {
    label: 'National Polytechnic (New Institution)',
    email: 'national@aicte.demo',
    password: 'demo123',
    role: 'institution',
    name: 'National Polytechnic College',
    institutionId: 3,
  },
  {
    label: 'Scrutiny Officer (Dr. S. K. Verma)',
    email: 'officer.verma@aicte.gov.in',
    password: 'demo123',
    role: 'officer',
    name: 'Dr. S. K. Verma (Scrutiny Officer)',
  },
  {
    label: 'System Administrator',
    email: 'admin@aicte.gov.in',
    password: 'demo123',
    role: 'admin',
    name: 'National Tech Admin (Directorate)',
  },
  {
    label: 'Compliance Auditor',
    email: 'auditor@aicte.gov.in',
    password: 'demo123',
    role: 'audit',
    name: 'Independent Audit Officer (CVC Nominee)',
  },
];

const SESSION_KEY = 'docvalidate_session';
const REMEMBER_KEY = 'docvalidate_remember';

class AuthService {
  public async login(
    identifier: string,
    password: string,
    role: UserRole,
    rememberMe = false
  ): Promise<AuthUser> {
    const cleanId = identifier.trim().toLowerCase();

    // 1. Check if backend /auth/login endpoint exists
    try {
      const res = await fetch(`${api.getBaseUrl()}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: cleanId, password, role }),
      });
      if (res.ok) {
        const data = await res.json();
        const user: AuthUser = {
          id: String(data.id || cleanId),
          name: data.name || cleanId,
          email: data.email || cleanId,
          role: data.role || role,
          institutionId: data.institution_id || data.institutionId,
          institutionName: data.institution_name || data.institutionName,
        };
        this.saveSession(user, rememberMe);
        return user;
      }
    } catch {
      // Backend auth endpoint not present; proceed with deterministic prototype demo validation
    }

    // 2. Validate against seeded demo accounts
    const match = DEMO_ACCOUNTS.find(
      (acc) =>
        (acc.email.toLowerCase() === cleanId || acc.name.toLowerCase() === cleanId) &&
        acc.role === role &&
        acc.password === password
    );

    if (!match) {
      // Allow flexible demo logins if password is 'demo123' and role matches
      if (password === 'demo123') {
        const user: AuthUser = {
          id: cleanId,
          name: cleanId.includes('@') ? cleanId.split('@')[0] : cleanId,
          email: cleanId,
          role: role,
          institutionId: role === 'institution' ? 1 : undefined,
          institutionName: role === 'institution' ? 'Apex Institute of Technology' : undefined,
        };
        this.saveSession(user, rememberMe);
        return user;
      }
      throw new Error('Invalid credentials. Please verify your Email/User ID and password.');
    }

    const user: AuthUser = {
      id: String(match.institutionId || match.email),
      name: match.name,
      email: match.email,
      role: match.role,
      institutionId: match.institutionId,
      institutionName: match.role === 'institution' ? match.name : undefined,
    };

    this.saveSession(user, rememberMe);
    return user;
  }

  public saveSession(user: AuthUser, rememberMe = false): void {
    const serialized = JSON.stringify(user);
    try {
      sessionStorage.setItem(SESSION_KEY, serialized);
    } catch (e) {
      console.warn('Unable to access sessionStorage', e);
    }

    if (rememberMe) {
      try {
        localStorage.setItem(REMEMBER_KEY, serialized);
      } catch (e) {
        console.warn('Unable to access localStorage', e);
      }
    } else {
      try {
        localStorage.removeItem(REMEMBER_KEY);
      } catch {}
    }

    // Propagate headers to api adapter
    api.setDemoUser({
      role: user.role === 'audit' || user.role === 'admin' ? 'officer' : user.role,
      officerName: user.name,
      institutionId: user.institutionId,
      institutionName: user.institutionName,
    });
  }

  public getSession(): AuthUser | null {
    try {
      const inSession = sessionStorage.getItem(SESSION_KEY);
      if (inSession) {
        const user = JSON.parse(inSession) as AuthUser;
        api.setDemoUser({
          role: user.role === 'audit' || user.role === 'admin' ? 'officer' : user.role,
          officerName: user.name,
          institutionId: user.institutionId,
          institutionName: user.institutionName,
        });
        return user;
      }

      const inLocal = localStorage.getItem(REMEMBER_KEY);
      if (inLocal) {
        const user = JSON.parse(inLocal) as AuthUser;
        sessionStorage.setItem(SESSION_KEY, inLocal);
        api.setDemoUser({
          role: user.role === 'audit' || user.role === 'admin' ? 'officer' : user.role,
          officerName: user.name,
          institutionId: user.institutionId,
          institutionName: user.institutionName,
        });
        return user;
      }
    } catch (e) {
      console.warn('Error reading session', e);
    }
    return null;
  }

  public logout(): void {
    try {
      sessionStorage.removeItem(SESSION_KEY);
      localStorage.removeItem(REMEMBER_KEY);
    } catch {}
    api.setDemoUser({
      role: 'institution',
      institutionName: 'Logged Out',
    });
  }
}

export const authService = new AuthService();

