import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ThemeManager } from './ThemeManager';

function mockMatchMedia(matches: boolean) {
  const listeners: Array<(e: MediaQueryListEvent) => void> = [];
  const mql = {
    matches,
    addEventListener: vi.fn((_: string, listener: (e: MediaQueryListEvent) => void) => {
      listeners.push(listener);
    }),
    removeEventListener: vi.fn(),
  };
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue(mql));
  return { mql, listeners };
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
  // Reset singleton
  (ThemeManager as any).instance = undefined;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ThemeManager', () => {
  describe('getInstance', () => {
    it('返回单例', () => {
      mockMatchMedia(false);
      const a = ThemeManager.getInstance();
      const b = ThemeManager.getInstance();
      expect(a).toBe(b);
    });
  });

  describe('getTheme / setTheme', () => {
    it('默认从 localStorage 读取', () => {
      localStorage.setItem('theme', 'dark');
      mockMatchMedia(false);
      const tm = ThemeManager.getInstance();
      expect(tm.getTheme()).toBe('dark');
    });

    it('localStorage 无值时根据系统偏好决定', () => {
      mockMatchMedia(true);
      const tm = ThemeManager.getInstance();
      expect(tm.getTheme()).toBe('dark');
    });

    it('setTheme 更新当前主题和 localStorage', () => {
      mockMatchMedia(false);
      const tm = ThemeManager.getInstance();
      tm.setTheme('dark');
      expect(tm.getTheme()).toBe('dark');
      expect(localStorage.getItem('theme')).toBe('dark');
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    });

    it('setTheme(light) 移除 data-theme 属性', () => {
      mockMatchMedia(false);
      const tm = ThemeManager.getInstance();
      tm.setTheme('dark');
      tm.setTheme('light');
      expect(document.documentElement.hasAttribute('data-theme')).toBe(false);
    });
  });

  describe('toggleTheme', () => {
    it('light -> dark', () => {
      mockMatchMedia(false);
      const tm = ThemeManager.getInstance();
      tm.toggleTheme();
      expect(tm.getTheme()).toBe('dark');
    });

    it('dark -> light', () => {
      localStorage.setItem('theme', 'dark');
      mockMatchMedia(false);
      const tm = ThemeManager.getInstance();
      tm.toggleTheme();
      expect(tm.getTheme()).toBe('light');
    });
  });

  describe('watchSystemTheme', () => {
    it('注册 media query 监听器', () => {
      const { mql } = mockMatchMedia(false);
      const tm = ThemeManager.getInstance();
      const cb = vi.fn();
      tm.watchSystemTheme(cb);
      expect(mql.addEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    });

    it('返回取消订阅函数', () => {
      const { mql } = mockMatchMedia(false);
      const tm = ThemeManager.getInstance();
      const unsub = tm.watchSystemTheme(vi.fn());
      unsub();
      expect(mql.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    });
  });
});
