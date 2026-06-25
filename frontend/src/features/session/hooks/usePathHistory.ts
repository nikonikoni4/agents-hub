/**
 * 路径历史管理 hook
 * 使用 localStorage 存储用户选择过的项目路径
 */

import { useState, useCallback } from 'react';

const STORAGE_KEY = 'path-history';
const MAX_HISTORY = 15;

export function usePathHistory() {
  const [history, setHistory] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  // 保存路径到历史（去重并移到最前面）
  const addToHistory = useCallback((path: string) => {
    if (!path.trim()) return;

    setHistory((prev) => {
      const filtered = prev.filter((p) => p !== path);
      const updated = [path, ...filtered].slice(0, MAX_HISTORY);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  // 清除历史
  const clearHistory = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setHistory([]);
  }, []);

  // 删除单条历史
  const removeFromHistory = useCallback((path: string) => {
    setHistory((prev) => {
      const updated = prev.filter((p) => p !== path);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  return { history, addToHistory, clearHistory, removeFromHistory };
}
