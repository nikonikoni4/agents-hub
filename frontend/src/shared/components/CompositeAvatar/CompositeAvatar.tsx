import { AvatarImage } from '../AvatarImage';
import type { AvatarData } from '@/shared/types/domain';
import styles from './CompositeAvatar.module.css';

export interface CompositeAvatarProps {
  /** 最多 4 个头像数据 */
  avatars: AvatarData[];
  /** 整体尺寸（px），默认 36 */
  size?: number;
}

export function CompositeAvatar({ avatars, size = 36 }: CompositeAvatarProps) {
  if (avatars.length === 0) return null;

  // 单个头像：直接圆形展示
  if (avatars.length === 1) {
    const first = avatars[0];
    if (!first) return null;
    return (
      <div className={styles.single} style={{ width: size, height: size }}>
        <AvatarImage avatar={first} />
      </div>
    );
  }

  const cells = avatars.slice(0, 4);
  while (cells.length < 4) cells.push(null as unknown as AvatarData);

  const gap = Math.max(1, Math.round(size * 0.06));
  const cellSize = Math.round((size - gap) / 2);

  return (
    <div
      className={styles.grid}
      style={{
        width: size,
        height: size,
        gap: `${gap}px`,
      }}
    >
      {cells.map((avatar, i) => (
        <div key={i} className={styles.cell} style={{ width: cellSize, height: cellSize }}>
          {avatar ? <AvatarImage avatar={avatar} /> : <div className={styles.empty} />}
        </div>
      ))}
    </div>
  );
}
