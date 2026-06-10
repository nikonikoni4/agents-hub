import React, { useState, useCallback, useEffect, useRef } from 'react';
import styles from './ImagePreviewModal.module.css';

export interface ImagePreviewModalProps {
  isOpen: boolean;
  imageUrl: string;
  alt?: string;
  onClose: () => void;
}

const SCALE_MIN = 0.1;
const SCALE_MAX = 5;
const ZOOM_FACTOR = 1.2;

export const ImagePreviewModal = React.memo(
  ({ isOpen, imageUrl, alt = '预览图片', onClose }: ImagePreviewModalProps) => {
    const [scale, setScale] = useState(1);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
      if (isOpen) {
        setScale(1);
        setPosition({ x: 0, y: 0 });
      }
    }, [isOpen, imageUrl]);

    // Native addEventListener for wheel (requires passive: false)
    useEffect(() => {
      const container = containerRef.current;
      if (!container || !isOpen) return;

      const handleWheel = (e: WheelEvent) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        setScale((prev) => Math.min(Math.max(SCALE_MIN, prev * delta), SCALE_MAX));
      };

      container.addEventListener('wheel', handleWheel, { passive: false });
      return () => container.removeEventListener('wheel', handleWheel);
    }, [isOpen]);

    const handleMouseDown = useCallback(
      (e: React.MouseEvent) => {
        if (e.button === 0) {
          setIsDragging(true);
          setDragStart({
            x: e.clientX - position.x,
            y: e.clientY - position.y,
          });
        }
      },
      [position]
    );

    const handleMouseMove = useCallback(
      (e: React.MouseEvent) => {
        if (isDragging) {
          setPosition({
            x: e.clientX - dragStart.x,
            y: e.clientY - dragStart.y,
          });
        }
      },
      [isDragging, dragStart]
    );

    const handleMouseUp = useCallback(() => {
      setIsDragging(false);
    }, []);

    const handleKeyDown = useCallback(
      (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onClose();
        }
      },
      [onClose]
    );

    useEffect(() => {
      if (!isOpen) return;
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, handleKeyDown]);

    const handleZoomIn = useCallback(() => {
      setScale((prev) => Math.min(prev * ZOOM_FACTOR, SCALE_MAX));
    }, []);

    const handleZoomOut = useCallback(() => {
      setScale((prev) => Math.max(prev / ZOOM_FACTOR, SCALE_MIN));
    }, []);

    const handleReset = useCallback(() => {
      setScale(1);
      setPosition({ x: 0, y: 0 });
    }, []);

    if (!isOpen) return null;

    return (
      <div
        className={styles.overlay}
        onClick={onClose}
        role="dialog"
        aria-modal="true"
        aria-label="图片预览"
      >
        <div className={styles.container} onClick={(e) => e.stopPropagation()}>
          <button className={styles.closeBtn} onClick={onClose} aria-label="关闭">
            ✕
          </button>
          <div
            ref={containerRef}
            className={styles.imageContainer}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <img
              src={imageUrl}
              alt={alt}
              className={styles.image}
              style={{
                transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
              }}
              draggable={false}
            />
          </div>
          <div className={styles.controls}>
            <button onClick={handleZoomIn} aria-label="放大">
              放大
            </button>
            <button onClick={handleZoomOut} aria-label="缩小">
              缩小
            </button>
            <button onClick={handleReset} aria-label="重置">
              重置
            </button>
          </div>
        </div>
      </div>
    );
  }
);

ImagePreviewModal.displayName = 'ImagePreviewModal';
