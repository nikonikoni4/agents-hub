import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { UploadPreview } from './UploadPreview';
import type { UploadedFileInfo } from '@/shared/types';

const mockFiles: UploadedFileInfo[] = [
  {
    file_name: 'test.pdf',
    file_path: 'test/test.pdf',
    file_type: 'application/pdf',
    file_size: 1024,
  },
];

const mockImageFiles: UploadedFileInfo[] = [
  {
    file_name: 'photo.png',
    file_path: 'uploads/photo.png',
    file_type: 'image/png',
    file_size: 2048,
  },
];

describe('UploadPreview', () => {
  it('renders file name for document files', () => {
    render(
      <UploadPreview
        files={mockFiles}
        onRemove={vi.fn()}
        groupChatId="test-chat"
      />,
    );

    screen.getByText('test.pdf');
  });

  it('renders file size for document files', () => {
    render(
      <UploadPreview
        files={mockFiles}
        onRemove={vi.fn()}
        groupChatId="test-chat"
      />,
    );

    screen.getByText('1.0 KB');
  });

  it('renders image preview for image files', () => {
    render(
      <UploadPreview
        files={mockImageFiles}
        onRemove={vi.fn()}
        groupChatId="test-chat"
      />,
    );

    const img = screen.getByRole('img', { name: 'photo.png' }) as HTMLImageElement;
    expect(img).toBeTruthy();
    expect(img.src).toContain('photo.png');
  });

  it('renders nothing when files array is empty', () => {
    const { container } = render(
      <UploadPreview
        files={[]}
        onRemove={vi.fn()}
        groupChatId="test-chat"
      />,
    );

    expect(container.innerHTML).toBe('');
  });

  it('calls onRemove with correct index when remove button clicked', () => {
    const onRemove = vi.fn();
    render(
      <UploadPreview
        files={mockFiles}
        onRemove={onRemove}
        groupChatId="test-chat"
      />,
    );

    fireEvent.click(screen.getByLabelText('删除文件 test.pdf'));
    expect(onRemove).toHaveBeenCalledWith(0);
  });

  it('renders multiple files with correct indices', () => {
    const multipleFiles: UploadedFileInfo[] = [
      ...mockFiles,
      {
        file_name: 'image.jpg',
        file_path: 'test/image.jpg',
        file_type: 'image/jpeg',
        file_size: 512,
      },
    ];

    const onRemove = vi.fn();
    render(
      <UploadPreview
        files={multipleFiles}
        onRemove={onRemove}
        groupChatId="test-chat"
      />,
    );

    screen.getByText('test.pdf');
    screen.getByRole('img', { name: 'image.jpg' });

    fireEvent.click(screen.getByLabelText('删除文件 image.jpg'));
    expect(onRemove).toHaveBeenCalledWith(1);
  });

  it('calls onImageClick when image preview is clicked', () => {
    const onImageClick = vi.fn();
    render(
      <UploadPreview
        files={mockImageFiles}
        onRemove={vi.fn()}
        groupChatId="test-chat"
        onImageClick={onImageClick}
      />,
    );

    const imagePreview = screen.getByLabelText('预览图片 photo.png');
    fireEvent.click(imagePreview);

    expect(onImageClick).toHaveBeenCalledWith('uploads/photo.png');
  });
});
