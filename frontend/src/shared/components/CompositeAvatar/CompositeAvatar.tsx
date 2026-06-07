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

  // 单个头像：直接圆形展示
  const nonEmpty = avatars.filter(Boolean);
  if (nonEmpty.length <= 1) {
    return (
      <div className={styles.single} style={{ width: size, height: size }}>
        <AvatarImage avatar={nonEmpty[0] ?? null} />
      </div>
    );
  }

  const cells = avatars.slice(0, 4);
  while (cells.length < 4) cells.push(null);

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
