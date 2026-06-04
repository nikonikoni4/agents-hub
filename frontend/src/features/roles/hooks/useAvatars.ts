/**
 * 头像列表管理 hook
 */

import { useEffect, useState, useCallback } from 'react';
import { listAvatars } from '@/core/api/roleApi';

export function useAvatars() {
  const [avatars, setAvatars] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAvatars = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listAvatars();
      setAvatars(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载头像失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAvatars();
  }, [fetchAvatars]);

  return { avatars, loading, error, refreshAvatars: fetchAvatars };
}
