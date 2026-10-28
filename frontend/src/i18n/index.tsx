import React, { createContext, useContext, useState, useEffect } from 'react';
import en from './en.json';
import hi from './hi.json';

export type Language = 'en' | 'hi';

type NestedKeyOf<ObjectType extends object> = {
  [Key in keyof ObjectType & (string | number)]: ObjectType[Key] extends object
    ? `${Key}` | `${Key}.${NestedKeyOf<ObjectType[Key]>}`
    : `${Key}`;
}[keyof ObjectType & (string | number)];

interface I18nContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, defaultText?: string) => string;
}

const translations: Record<Language, any> = { en, hi };

const I18nContext = createContext<I18nContextType>({
  language: 'en',
  setLanguage: () => {},
  t: (key) => key,
});

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    return (localStorage.getItem('docvalidate_lang') as Language) || 'en';
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('docvalidate_lang', lang);
    if (lang === 'hi') {
      document.documentElement.lang = 'hi';
      document.body.classList.add('lang-hi');
    } else {
      document.documentElement.lang = 'en';
      document.body.classList.remove('lang-hi');
    }
  };

  useEffect(() => {
    if (language === 'hi') {
      document.documentElement.lang = 'hi';
      document.body.classList.add('lang-hi');
    } else {
      document.documentElement.lang = 'en';
      document.body.classList.remove('lang-hi');
    }
  }, [language]);

  const t = (path: string, defaultText?: string): string => {
    const keys = path.split('.');
    let current = translations[language];
    for (const key of keys) {
      if (current && current[key] !== undefined) {
        current = current[key];
      } else {
        // Fallback to English
        let fallback = translations.en;
        for (const fKey of keys) {
          if (fallback && fallback[fKey] !== undefined) {
            fallback = fallback[fKey];
          } else {
            return defaultText || path;
          }
        }
        return typeof fallback === 'string' ? fallback : defaultText || path;
      }
    }
    return typeof current === 'string' ? current : defaultText || path;
  };

  return (
    <I18nContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </I18nContext.Provider>
  );
};

export const useI18n = () => useContext(I18nContext);
