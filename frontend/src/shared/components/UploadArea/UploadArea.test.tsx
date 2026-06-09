import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { UploadArea } from './UploadArea';

describe('UploadArea', () => {
  it('renders upload area with hint text', () => {
    render(<UploadArea chatId="test-chat" onUploadComplete={vi.fn()} onUploadError={vi.fn()} />);

    // getByText throws if not found, so this is an implicit existence check
    screen.getByText('拖拽文件到此处或点击上传');
  });

  it('has button role and upload aria-label', () => {
    render(<UploadArea chatId="test-chat" onUploadComplete={vi.fn()} onUploadError={vi.fn()} />);

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    expect(uploadArea.getAttribute('aria-disabled')).not.toBe('true');
  });

  it('renders file input with multiple and accept attributes', () => {
    render(<UploadArea chatId="test-chat" onUploadComplete={vi.fn()} onUploadError={vi.fn()} />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeTruthy();
    expect(fileInput.multiple).toBe(true);
    expect(fileInput.accept).toContain('image/jpeg');
    expect(fileInput.accept).toContain('application/pdf');
  });

  it('sets aria-disabled and tabIndex when disabled', () => {
    render(
      <UploadArea chatId="test-chat" onUploadComplete={vi.fn()} onUploadError={vi.fn()} disabled />
    );

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    expect(uploadArea.getAttribute('aria-disabled')).toBe('true');
    expect(uploadArea.getAttribute('tabindex')).toBe('-1');
  });

  it('handles drag over event without crashing', () => {
    render(<UploadArea chatId="test-chat" onUploadComplete={vi.fn()} onUploadError={vi.fn()} />);

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    fireEvent.dragOver(uploadArea);

    // Component should still be in the document after drag over
    screen.getByRole('button', { name: '上传文件' });
  });

  it('handles drag leave event without crashing', () => {
    render(<UploadArea chatId="test-chat" onUploadComplete={vi.fn()} onUploadError={vi.fn()} />);

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    fireEvent.dragOver(uploadArea);
    fireEvent.dragLeave(uploadArea);

    screen.getByRole('button', { name: '上传文件' });
  });

  it('handles drop event with unsupported file type', () => {
    const onUploadError = vi.fn();
    render(
      <UploadArea chatId="test-chat" onUploadComplete={vi.fn()} onUploadError={onUploadError} />
    );

    const uploadArea = screen.getByRole('button', { name: '上传文件' });

    // Create a mock file with unsupported type to trigger validation error
    const file = new File(['content'], 'test.exe', {
      type: 'application/x-msdownload',
    });
    const dataTransfer = { files: [file] };

    fireEvent.drop(uploadArea, { dataTransfer });

    // Unsupported file type should trigger onUploadError
    expect(onUploadError).toHaveBeenCalledWith(expect.stringContaining('不支持的文件类型'));
  });

  it('triggers file input click on area click', () => {
    render(<UploadArea chatId="test-chat" onUploadComplete={vi.fn()} onUploadError={vi.fn()} />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const clickSpy = vi.spyOn(fileInput, 'click');

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    fireEvent.click(uploadArea);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('does not trigger file input click when disabled', () => {
    render(
      <UploadArea chatId="test-chat" onUploadComplete={vi.fn()} onUploadError={vi.fn()} disabled />
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const clickSpy = vi.spyOn(fileInput, 'click');

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    fireEvent.click(uploadArea);

    expect(clickSpy).not.toHaveBeenCalled();
  });
});
