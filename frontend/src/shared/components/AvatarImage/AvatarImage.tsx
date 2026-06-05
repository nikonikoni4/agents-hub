import { buildAvatarUrl } from '@/core/api/roleApi';
import styles from './AvatarImage.module.css';

export interface AvatarImageProps {
  avatar: string | null;
  fallback?: string;
}

export function AvatarImage({ avatar, fallback = '' }: AvatarImageProps) {
  if (avatar) {
    return <img src={buildAvatarUrl(avatar)} alt="头像" className={styles.img} />;
  }

  return <div className={styles.fallback}>{fallback.charAt(0).toUpperCase()}</div>;
}
