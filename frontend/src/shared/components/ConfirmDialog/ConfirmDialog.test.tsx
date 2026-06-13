import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ConfirmDialog } from './ConfirmDialog';

describe('ConfirmDialog', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    message: '确认要执行此操作吗？',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dialog when isOpen is true', () => {
    render(<ConfirmDialog {...defaultProps} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('确认要执行此操作吗？')).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    render(<ConfirmDialog {...defaultProps} isOpen={false} />);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('displays custom title', () => {
    render(<ConfirmDialog {...defaultProps} title="自定义标题" />);

    expect(screen.getByText('自定义标题')).toBeInTheDocument();
  });

  it('displays default title when not provided', () => {
    render(<ConfirmDialog {...defaultProps} />);

    expect(screen.getByText('确认操作')).toBeInTheDocument();
  });

  it('displays custom button text', () => {
    render(<ConfirmDialog {...defaultProps} confirmText="是的" cancelText="不" />);

    expect(screen.getByText('是的')).toBeInTheDocument();
    expect(screen.getByText('不')).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button is clicked', () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog {...defaultProps} onConfirm={onConfirm} />);

    fireEvent.click(screen.getByText('确认'));

    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn();
    render(<ConfirmDialog {...defaultProps} onClose={onClose} />);

    fireEvent.click(screen.getByText('取消'));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when overlay is clicked', () => {
    const onClose = vi.fn();
    render(<ConfirmDialog {...defaultProps} onClose={onClose} />);

    fireEvent.click(screen.getByRole('dialog').parentElement!);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('does not call onClose when dialog is clicked', () => {
    const onClose = vi.fn();
    render(<ConfirmDialog {...defaultProps} onClose={onClose} />);

    fireEvent.click(screen.getByRole('dialog'));

    expect(onClose).not.toHaveBeenCalled();
  });

  it('calls onClose when Escape key is pressed', () => {
    const onClose = vi.fn();
    render(<ConfirmDialog {...defaultProps} onClose={onClose} />);

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('disables confirm button when confirmDisabled is true', () => {
    render(<ConfirmDialog {...defaultProps} confirmDisabled />);

    expect(screen.getByText('确认')).toBeDisabled();
  });

  it('shows loading text when loading is true', () => {
    render(<ConfirmDialog {...defaultProps} loading />);

    expect(screen.getByText('处理中...')).toBeInTheDocument();
  });

  it('disables both buttons when loading is true', () => {
    render(<ConfirmDialog {...defaultProps} loading />);

    expect(screen.getByText('处理中...')).toBeDisabled();
    expect(screen.getByText('取消')).toBeDisabled();
  });

  it('applies variant class to dialog', () => {
    render(<ConfirmDialog {...defaultProps} variant="danger" />);

    const dialog = screen.getByRole('dialog');
    expect(dialog.className).toContain('danger');
  });

  it('has correct aria attributes', () => {
    render(<ConfirmDialog {...defaultProps} />);

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'confirm-dialog-title');
    expect(dialog).toHaveAttribute('aria-describedby', 'confirm-dialog-message');
  });
});
