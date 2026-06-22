/**
 * AgentsHubAssistantModal 组件测试
 *
 * 测试覆盖：
 * 1. 打开/关闭功能
 * 2. ESC 键关闭
 * 3. 点击 overlay 关闭
 * 4. 关闭按钮点击
 * 5. 消息列表渲染
 * 6. 输入框交互
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentsHubAssistantModal } from './AgentsHubAssistantModal';

// Mock hooks
vi.mock('../hooks/useSingleChatMessages', () => ({
  useSingleChatMessages: vi.fn(() => ({
    messages: [],
    loading: false,
    streaming: false,
    streamingText: '',
    sendMessage: vi.fn(),
    cancelStream: vi.fn(),
  })),
}));

vi.mock('../store/singleChatStore', () => ({
  useSingleChatStore: vi.fn((selector) => {
    const state = {
      activeSingleChatId: null,
      singleChats: [],
      draftChat: null,
      openSingleChat: vi.fn(),
      openDraftChat: vi.fn(),
      clearActive: vi.fn(),
    };
    return selector ? selector(state) : state;
  }),
}));

describe('AgentsHubAssistantModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该在 isOpen=true 时渲染弹窗', () => {
    render(<AgentsHubAssistantModal {...defaultProps} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Agents Hub 助手')).toBeInTheDocument();
  });

  it('应该在 isOpen=false 时不渲染弹窗', () => {
    render(<AgentsHubAssistantModal {...defaultProps} isOpen={false} />);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('应该在点击关闭按钮时调用 onClose', () => {
    const onClose = vi.fn();
    render(<AgentsHubAssistantModal {...defaultProps} onClose={onClose} />);

    const closeButton = screen.getByTitle('关闭');
    fireEvent.click(closeButton);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('应该在点击 overlay 时调用 onClose', () => {
    const onClose = vi.fn();
    render(<AgentsHubAssistantModal {...defaultProps} onClose={onClose} />);

    const overlay = screen.getByRole('dialog').parentElement;
    fireEvent.click(overlay!);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('应该在点击 dialog 内部时不调用 onClose', () => {
    const onClose = vi.fn();
    render(<AgentsHubAssistantModal {...defaultProps} onClose={onClose} />);

    const dialog = screen.getByRole('dialog');
    fireEvent.click(dialog);

    expect(onClose).not.toHaveBeenCalled();
  });

  it('应该在按下 ESC 键时调用 onClose', () => {
    const onClose = vi.fn();
    render(<AgentsHubAssistantModal {...defaultProps} onClose={onClose} />);

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('应该在 isOpen=false 时不监听 ESC 键', () => {
    const onClose = vi.fn();
    render(<AgentsHubAssistantModal {...defaultProps} isOpen={false} onClose={onClose} />);

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(onClose).not.toHaveBeenCalled();
  });

  it('应该显示输入框和发送按钮', () => {
    render(<AgentsHubAssistantModal {...defaultProps} />);

    expect(screen.getByPlaceholderText('输入消息...')).toBeInTheDocument();
    expect(screen.getByText('发送')).toBeInTheDocument();
  });

  it('应该在输入框为空时禁用发送按钮', () => {
    render(<AgentsHubAssistantModal {...defaultProps} />);

    const sendButton = screen.getByText('发送');
    expect(sendButton).toBeDisabled();
  });

  it('应该在输入框有内容时启用发送按钮', () => {
    render(<AgentsHubAssistantModal {...defaultProps} />);

    const input = screen.getByPlaceholderText('输入消息...');
    fireEvent.change(input, { target: { value: '测试消息' } });

    const sendButton = screen.getByText('发送');
    expect(sendButton).not.toBeDisabled();
  });

  it('应该在按 Enter 时发送消息', async () => {
    const sendMessage = vi.fn();
    const { useSingleChatMessages } = await import('../hooks/useSingleChatMessages');
    vi.mocked(useSingleChatMessages).mockReturnValue({
      messages: [],
      loading: false,
      streaming: false,
      streamingText: '',
      sendMessage,
      cancelStream: vi.fn(),
    });

    render(<AgentsHubAssistantModal {...defaultProps} />);

    const input = screen.getByPlaceholderText('输入消息...');
    fireEvent.change(input, { target: { value: '测试消息' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });

    expect(sendMessage).toHaveBeenCalledWith('测试消息');
  });

  it('应该在按 Shift+Enter 时不发送消息', async () => {
    const sendMessage = vi.fn();
    const { useSingleChatMessages } = await import('../hooks/useSingleChatMessages');
    vi.mocked(useSingleChatMessages).mockReturnValue({
      messages: [],
      loading: false,
      streaming: false,
      streamingText: '',
      sendMessage,
      cancelStream: vi.fn(),
    });

    render(<AgentsHubAssistantModal {...defaultProps} />);

    const input = screen.getByPlaceholderText('输入消息...');
    fireEvent.change(input, { target: { value: '测试消息' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });

    expect(sendMessage).not.toHaveBeenCalled();
  });

  it('应该显示空状态提示当没有消息时', () => {
    render(<AgentsHubAssistantModal {...defaultProps} />);

    expect(screen.getByText('发送消息开始对话')).toBeInTheDocument();
  });

  it('应该显示加载状态', async () => {
    const { useSingleChatMessages } = await import('../hooks/useSingleChatMessages');
    vi.mocked(useSingleChatMessages).mockReturnValue({
      messages: [],
      loading: true,
      streaming: false,
      streamingText: '',
      sendMessage: vi.fn(),
      cancelStream: vi.fn(),
    });

    render(<AgentsHubAssistantModal {...defaultProps} />);

    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });
});
