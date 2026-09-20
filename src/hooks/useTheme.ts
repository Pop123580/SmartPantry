import { useState, useEffect } from 'react';

export type ThemeColor = 'green' | 'yellow' | 'blue' | 'purple' | 'pink' | 'orange' | 'red';

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeColor>('green');

  useEffect(() => {
    const savedTheme = localStorage.getItem('smartpantry-theme') as ThemeColor;
    if (savedTheme) {
      setThemeState(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
      document.documentElement.setAttribute('data-theme', 'green');
    }
  }, []);

  const setTheme = (newTheme: ThemeColor) => {
    setThemeState(newTheme);
    localStorage.setItem('smartpantry-theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  return { theme, setTheme };
}
