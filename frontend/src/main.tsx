import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import { ThemeManager } from '@/core/theme/ThemeManager';

// 引入样式
import '@/styles/reset.css';
import '@/styles/theme.css';
import '@/styles/global.css';

// 初始化主题管理器
ThemeManager.getInstance();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
