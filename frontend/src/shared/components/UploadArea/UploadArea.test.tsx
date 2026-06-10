import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { UploadArea } from './UploadArea';

describe('UploadArea', () => {
  it('renders upload area with hint text', () => {
    render(<UploadArea onFilesSelected={vi.fn()} />);

    // getByText throws if not found, so this is an implicit existence check
    screen.getByText('拖拽文件到此处或点击上传');
  });

  it('has button role and upload aria-label', () => {
    render(<UploadArea onFilesSelected={vi.fn()} />);

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    expect(uploadArea.getAttribute('aria-disabled')).not.toBe('true');
  });

  it('renders file input with multiple attribute', () => {
    render(<UploadArea onFilesSelected={vi.fn()} />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeTruthy();
    expect(fileInput.multiple).toBe(true);
  });

  it('sets aria-disabled and tabIndex when disabled', () => {
    render(<UploadArea onFilesSelected={vi.fn()} disabled />);

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    expect(uploadArea.getAttribute('aria-disabled')).toBe('true');
    expect(uploadArea.getAttribute('tabindex')).toBe('-1');
  });

  it('handles drag over event without crashing', () => {
    render(<UploadArea onFilesSelected={vi.fn()} />);

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    fireEvent.dragOver(uploadArea);

    // Component should still be in the document after drag over
    screen.getByRole('button', { name: '上传文件' });
  });

  it('handles drag leave event without crashing', () => {
    render(<UploadArea onFilesSelected={vi.fn()} />);

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    fireEvent.dragOver(uploadArea);
    fireEvent.dragLeave(uploadArea);

    screen.getByRole('button', { name: '上传文件' });
  });

  it('handles drop event and calls onFilesSelected', () => {
    const onFilesSelected = vi.fn();
    render(<UploadArea onFilesSelected={onFilesSelected} />);

    const uploadArea = screen.getByRole('button', { name: '上传文件' });

    // Create a mock file
    const file = new File(['content'], 'test.txt', {
      type: 'text/plain',
    });
    const dataTransfer = { files: [file] };

    fireEvent.drop(uploadArea, { dataTransfer });

    // onFilesSelected should be called with the files
    expect(onFilesSelected).toHaveBeenCalled();
  });

  it('triggers file input click on area click', () => {
    render(<UploadArea onFilesSelected={vi.fn()} />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const clickSpy = vi.spyOn(fileInput, 'click');

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    fireEvent.click(uploadArea);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('does not trigger file input click when disabled', () => {
    render(<UploadArea onFilesSelected={vi.fn()} disabled />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const clickSpy = vi.spyOn(fileInput, 'click');

    const uploadArea = screen.getByRole('button', { name: '上传文件' });
    fireEvent.click(uploadArea);

    expect(clickSpy).not.toHaveBeenCalled();
  });
});
