import { AvatarImage } from '../AvatarImage';
import styles from './CompositeAvatar.module.css';

export interface CompositeAvatarProps {
  /** 最多 4 个头像 SVG 字符串 */
  avatars: (string | null)[];
  /** 整体尺寸（px），默认 36 */
  size?: number;
}

export function CompositeAvatar({ avatars, size = 36 }: CompositeAvatarProps) {
  if (avatars.length === 0) return null;

  const cells = avatars.slice(0, 4);
  // 补齐到 4 个格子
  while (cells.length < 4) cells.push(null);

  return (
    <div className={styles.grid} style={{ width: size, height: size }}>
      {cells.map((avatar, i) => (
        <div key={i} className={styles.cell}>
          {avatar ? <AvatarImage avatar={avatar} /> : null}
        </div>
      ))}
    </div>
  );
}
