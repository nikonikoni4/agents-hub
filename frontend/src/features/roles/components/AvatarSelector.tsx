/**
 * 头像选择器组件
 *
 * avatar 字段存储 SVG 内容字符串
 */

import { AvatarImage } from '@/shared/components';
import { useAvatars } from '../hooks/useAvatars';
import styles from './AvatarSelector.module.css';

export interface AvatarSelectorProps {
  selectedAvatar: string | null;
  onSelect: (avatar: string) => void;
}

export function AvatarSelector({ selectedAvatar, onSelect }: AvatarSelectorProps) {
  const { avatars, loading } = useAvatars();

  if (loading) {
    return <div className={styles.loading}>加载头像...</div>;
  }

  return (
    <div className={styles.container}>
      {avatars.map((avatar, index) => (
        <button
          key={index}
          type="button"
          className={`${styles.avatarItem} ${selectedAvatar === avatar ? styles.selected : ''}`}
          onClick={() => onSelect(avatar)}
          aria-label={`选择头像 ${index + 1}`}
        >
          <AvatarImage avatar={avatar} />
        </button>
      ))}
    </div>
  );
}
