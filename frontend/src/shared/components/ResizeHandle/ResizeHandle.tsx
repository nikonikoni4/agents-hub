import { useCallback, useRef } from 'react';
import styles from './ResizeHandle.module.css';

interface ResizeHandleProps {
  direction: 'left' | 'right';
  onResize: (delta: number) => void;
  onResizeStart?: () => void;
  onResizeEnd?: () => void;
}

export function ResizeHandle({
  direction,
  onResize,
  onResizeStart,
  onResizeEnd,
}: ResizeHandleProps) {
  const isDragging = useRef(false);
  const startX = useRef(0);
  const pendingDelta = useRef(0);
  const rafId = useRef(0);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      isDragging.current = true;
      startX.current = e.clientX;
      pendingDelta.current = 0;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      onResizeStart?.();

      const flushDelta = () => {
        if (pendingDelta.current !== 0) {
          const d = pendingDelta.current;
          pendingDelta.current = 0;
          onResize(direction === 'right' ? -d : d);
        }
        if (isDragging.current) {
          rafId.current = requestAnimationFrame(flushDelta);
        }
      };
      rafId.current = requestAnimationFrame(flushDelta);

      const handleMouseMove = (e: MouseEvent) => {
        if (!isDragging.current) return;
        pendingDelta.current += e.clientX - startX.current;
        startX.current = e.clientX;
      };

      const handleMouseUp = () => {
        isDragging.current = false;
        cancelAnimationFrame(rafId.current);
        // flush remaining delta
        if (pendingDelta.current !== 0) {
          const d = pendingDelta.current;
          pendingDelta.current = 0;
          onResize(direction === 'right' ? -d : d);
        }
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        onResizeEnd?.();
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [direction, onResize, onResizeStart, onResizeEnd]
  );

  return <div className={styles.handle} onMouseDown={handleMouseDown} data-direction={direction} />;
}
