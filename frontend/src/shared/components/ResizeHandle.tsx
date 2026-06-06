import { useRef, useCallback } from 'react';
import styles from './ResizeHandle.module.css';

export interface ResizeHandleProps {
  direction: 'left' | 'right';
  onResize?: (delta: number) => void;
  onResizeStart?: () => void;
  onResizeEnd?: () => void;
}

export function ResizeHandle({
  direction,
  onResize,
  onResizeStart,
  onResizeEnd,
}: ResizeHandleProps) {
  const startXRef = useRef(0);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      startXRef.current = e.clientX;
      onResizeStart?.();

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const delta =
          direction === 'left'
            ? moveEvent.clientX - startXRef.current
            : startXRef.current - moveEvent.clientX;
        onResize?.(delta);
        startXRef.current = moveEvent.clientX;
      };

      const handleMouseUp = () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        onResizeEnd?.();
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [direction, onResize, onResizeStart, onResizeEnd]
  );

  return (
    <div
      className={`${styles.resizeHandle} ${styles[direction]}`}
      onMouseDown={handleMouseDown}
      role="separator"
      aria-orientation="vertical"
      aria-label="调整侧边栏宽度"
    />
  );
}
