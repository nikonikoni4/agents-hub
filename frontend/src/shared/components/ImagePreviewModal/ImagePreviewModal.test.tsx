import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ImagePreviewModal } from './ImagePreviewModal';

describe('ImagePreviewModal', () => {
  it('renders modal when isOpen is true', () => {
    render(
      <ImagePreviewModal
        isOpen={true}
        imageUrl="test.jpg"
        onClose={vi.fn()}
      />,
    );

    screen.getByRole('dialog');
    screen.getByAltText('预览图片');
  });

  it('renders image with correct src', () => {
    render(
      <ImagePreviewModal
        isOpen={true}
        imageUrl="/uploads/test.jpg"
        onClose={vi.fn()}
      />,
    );

    const img = screen.getByAltText('预览图片') as HTMLImageElement;
    expect(img.src).toContain('/uploads/test.jpg');
  });

  it('uses custom alt text when provided', () => {
    render(
      <ImagePreviewModal
        isOpen={true}
        imageUrl="test.jpg"
        alt="自定义图片"
        onClose={vi.fn()}
      />,
    );

    screen.getByAltText('自定义图片');
  });

  it('does not render when isOpen is false', () => {
    render(
      <ImagePreviewModal
        isOpen={false}
        imageUrl="test.jpg"
        onClose={vi.fn()}
      />,
    );

    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.queryByAltText('预览图片')).toBeNull();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(
      <ImagePreviewModal
        isOpen={true}
        imageUrl="test.jpg"
        onClose={onClose}
      />,
    );

    fireEvent.click(screen.getByLabelText('关闭'));
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when overlay is clicked', () => {
    const onClose = vi.fn();
    render(
      <ImagePreviewModal
        isOpen={true}
        imageUrl="test.jpg"
        onClose={onClose}
      />,
    );

    // Click the overlay (dialog element), not the container
    fireEvent.click(screen.getByRole('dialog'));
    expect(onClose).toHaveBeenCalled();
  });

  it('renders zoom controls', () => {
    render(
      <ImagePreviewModal
        isOpen={true}
        imageUrl="test.jpg"
        onClose={vi.fn()}
      />,
    );

    screen.getByLabelText('放大');
    screen.getByLabelText('缩小');
    screen.getByLabelText('重置');
  });

  it('has aria-modal attribute on dialog', () => {
    render(
      <ImagePreviewModal
        isOpen={true}
        imageUrl="test.jpg"
        onClose={vi.fn()}
      />,
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog.getAttribute('aria-modal')).toBe('true');
  });
});
