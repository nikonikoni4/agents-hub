import React, { useState, useCallback, useEffect } from 'react';
import styles from './ImagePreviewModal.module.css';

export interface ImagePreviewModalProps {
  isOpen: boolean;
  imageUrl: string;
  onClose: () => void;
}

export const ImagePreviewModal = React.memo(
  ({ isOpen, imageUrl, onClose }: ImagePreviewModalProps) => {
    const [scale, setScale] = useState(1);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

    useEffect(() => {
      if (isOpen) {
        setScale(1);
        setPosition({ x: 0, y: 0 });
      }
    }, [isOpen, imageUrl]);

    const handleWheel = useCallback((e: React.WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setScale((prev) => Math.min(Math.max(0.1, prev * delta), 5));
    }, []);

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

    if (!isOpen) return null;

    return (
      <div className={styles.overlay} onClick={onClose}>
        <div
          className={styles.container}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className={styles.closeBtn}
            onClick={onClose}
            aria-label="关闭"
          >
            ✕
          </button>
          <div
            className={styles.imageContainer}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <img
              src={imageUrl}
              alt="预览图片"
              className={styles.image}
              style={{
                transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
              }}
              draggable={false}
            />
          </div>
          <div className={styles.controls}>
            <button
              onClick={() => setScale((prev) => Math.min(prev * 1.2, 5))}
            >
              放大
            </button>
            <button
              onClick={() => setScale((prev) => Math.max(prev * 0.8, 0.1))}
            >
              缩小
            </button>
            <button
              onClick={() => {
                setScale(1);
                setPosition({ x: 0, y: 0 });
              }}
            >
              重置
            </button>
          </div>
        </div>
      </div>
    );
  }
);

ImagePreviewModal.displayName = 'ImagePreviewModal';
