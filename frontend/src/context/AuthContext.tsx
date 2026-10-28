import React, { createContext, useContext, useState, useEffect } from 'react';
import { DemoUser, Institution } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  currentUser: DemoUser;
  setCurrentUser: (user: DemoUser) => void;
  institutions: Institution[];
  isLoadingInstitutions: boolean;
  switchRole: (role: 'institution' | 'officer', institutionId?: number) => void;
}

const AuthContext = createContext<AuthContextType>({
  currentUser: api.getDemoUser(),
  setCurrentUser: () => {},
  institutions: [],
  isLoadingInstitutions: false,
  switchRole: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUserState] = useState<DemoUser>(() => api.getDemoUser());
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [isLoadingInstitutions, setIsLoadingInstitutions] = useState(false);

  useEffect(() => {
    setIsLoadingInstitutions(true);
    api
      .getInstitutions()
      .then((data) => {
        setInstitutions(data);
        // If current user is institution and has no institutionId set, default to first
        if (currentUser.role === 'institution' && !currentUser.institutionId && data.length > 0) {
          const updated: DemoUser = {
            ...currentUser,
            institutionId: data[0].id,
            institutionName: data[0].name,
          };
          setCurrentUser(updated);
        }
      })
      .catch((err) => console.error('Failed to load institutions:', err))
      .finally(() => setIsLoadingInstitutions(false));
  }, []);

  const setCurrentUser = (user: DemoUser) => {
    setCurrentUserState(user);
    api.setDemoUser(user);
  };

  const switchRole = (role: 'institution' | 'officer', institutionId?: number) => {
    if (role === 'officer') {
      const updated: DemoUser = {
        role: 'officer',
        officerName: 'Dr. S. K. Verma (Scrutiny Officer)',
      };
      setCurrentUser(updated);
    } else {
      const inst = institutions.find((i) => i.id === institutionId) || institutions[0];
      const updated: DemoUser = {
        role: 'institution',
        institutionId: inst ? inst.id : 1,
        institutionName: inst ? inst.name : 'Apex Institute of Technology',
      };
      setCurrentUser(updated);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        setCurrentUser,
        institutions,
        isLoadingInstitutions,
        switchRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
