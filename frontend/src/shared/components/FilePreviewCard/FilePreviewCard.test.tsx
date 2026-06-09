import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { FilePreviewCard } from './FilePreviewCard';
import type { UploadedFileInfo } from '@/shared/types';

const mockDocumentFiles: UploadedFileInfo[] = [
  {
    file_name: 'report.pdf',
    file_path: 'docs/report.pdf',
    file_type: 'application/pdf',
    file_size: 2048,
  },
];

const mockImageFiles: UploadedFileInfo[] = [
  {
    file_name: 'screenshot.png',
    file_path: 'images/screenshot.png',
    file_type: 'image/png',
    file_size: 4096,
  },
];

describe('FilePreviewCard', () => {
  it('renders file name for document files', () => {
    render(
      <FilePreviewCard
        files={mockDocumentFiles}
        groupChatId="test-chat"
      />,
    );

    screen.getByText('report.pdf');
  });

  it('renders file size for document files', () => {
    render(
      <FilePreviewCard
        files={mockDocumentFiles}
        groupChatId="test-chat"
      />,
    );

    screen.getByText('2.0 KB');
  });

  it('renders image thumbnail for image files', () => {
    render(
      <FilePreviewCard
        files={mockImageFiles}
        groupChatId="test-chat"
      />,
    );

    const img = screen.getByRole('img', { name: 'screenshot.png' }) as HTMLImageElement;
    expect(img).toBeTruthy();
    expect(img.src).toContain('screenshot.png');
  });

  it('renders nothing when files array is empty', () => {
    const { container } = render(
      <FilePreviewCard
        files={[]}
        groupChatId="test-chat"
      />,
    );

    expect(container.innerHTML).toBe('');
  });

  it('renders multiple files', () => {
    const multipleFiles: UploadedFileInfo[] = [
      ...mockDocumentFiles,
      ...mockImageFiles,
    ];

    render(
      <FilePreviewCard
        files={multipleFiles}
        groupChatId="test-chat"
      />,
    );

    screen.getByText('report.pdf');
    screen.getByRole('img', { name: 'screenshot.png' });
  });

  it('calls onImageClick when image is clicked', () => {
    const onImageClick = vi.fn();
    render(
      <FilePreviewCard
        files={mockImageFiles}
        groupChatId="test-chat"
        onImageClick={onImageClick}
      />,
    );

    const imageButton = screen.getByLabelText('查看图片 screenshot.png');
    fireEvent.click(imageButton);

    expect(onImageClick).toHaveBeenCalledWith('images/screenshot.png');
  });

  it('calls onDocumentClick when document is clicked', () => {
    const onDocumentClick = vi.fn();
    render(
      <FilePreviewCard
        files={mockDocumentFiles}
        groupChatId="test-chat"
        onDocumentClick={onDocumentClick}
      />,
    );

    const docButton = screen.getByLabelText('下载文件 report.pdf');
    fireEvent.click(docButton);

    expect(onDocumentClick).toHaveBeenCalledWith('docs/report.pdf');
  });
});
