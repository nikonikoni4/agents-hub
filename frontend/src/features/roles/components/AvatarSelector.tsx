/**
 * 头像选择器组件
 */

import { useState, useEffect } from 'react';
import { listAvatars } from '@/core/api/roleApi';
import styles from './AvatarSelector.module.css';

export interface AvatarSelectorProps {
  selectedAvatar: string | null;
  onSelect: (avatar: string) => void;
}

export function AvatarSelector({ selectedAvatar, onSelect }: AvatarSelectorProps) {
  const [avatars, setAvatars] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listAvatars()
      .then(setAvatars)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className={styles.loading}>加载头像...</div>;
  }

  return (
    <div className={styles.container}>
      {avatars.map((avatar) => (
        <button
          key={avatar}
          type="button"
          className={`${styles.avatarItem} ${selectedAvatar === avatar ? styles.selected : ''}`}
          onClick={() => onSelect(avatar)}
          aria-label={`选择头像 ${avatar}`}
        >
          <div className={styles.avatarPreview}>{avatar.charAt(0).toUpperCase()}</div>
        </button>
      ))}
    </div>
  );
}
