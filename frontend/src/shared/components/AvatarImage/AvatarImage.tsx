import { buildAvatarUrl } from '@/core/api/roleApi';
import type { AvatarData } from '@/shared/types/domain';
import styles from './AvatarImage.module.css';

export interface AvatarImageProps {
  /** 头像数据：支持新格式 AvatarData 或旧格式 string | null */
  avatar: AvatarData | string | null;
  /** 字符 fallback 的文本（仅旧格式需要） */
  fallback?: string;
}

export function AvatarImage({ avatar, fallback = '' }: AvatarImageProps) {
  // 新格式：AvatarData 对象
  if (avatar && typeof avatar === 'object') {
    if (avatar.type === 'svg') {
      return <img src={buildAvatarUrl(avatar.filename)} alt="头像" className={styles.img} />;
    }
    // avatar.type === 'char'
    return <div className={styles.fallback}>{avatar.char}</div>;
  }

  // 旧格式：string | null（向后兼容）
  if (avatar && typeof avatar === 'string') {
    return <img src={buildAvatarUrl(avatar)} alt="头像" className={styles.img} />;
  }

  // 旧格式：null → 使用 fallback
  return <div className={styles.fallback}>{fallback.charAt(0).toUpperCase()}</div>;
}
