import { useState, useEffect } from 'react';
import { ThemeManager } from '@/core/theme/ThemeManager';
import type { Theme } from '@/shared/types/theme';
import { MainLayout } from '@/layouts';

function App() {
  const [theme, setTheme] = useState<Theme>(() => ThemeManager.getInstance().getTheme());

  const handleToggleTheme = () => {
    ThemeManager.getInstance().toggleTheme();
    setTheme(ThemeManager.getInstance().getTheme());
  };

  useEffect(() => {
    const unwatch = ThemeManager.getInstance().watchSystemTheme((newTheme) => {
      setTheme(newTheme);
    });
    return unwatch;
  }, []);

  return <MainLayout theme={theme} onToggleTheme={handleToggleTheme} />;
}

export default App;
