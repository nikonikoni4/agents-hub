/**
 * LoopStatusPanel 组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LoopStatusPanel } from './LoopStatusPanel';

// Mock useLoopStatus hook
vi.mock('../hooks/useLoopStatus', () => ({
  useLoopStatus: vi.fn(),
}));

import { useLoopStatus } from '../hooks/useLoopStatus';

const mockUseLoopStatus = vi.mocked(useLoopStatus);

describe('LoopStatusPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('空状态显示"暂无Loop定义"', () => {
    // Arrange
    mockUseLoopStatus.mockReturnValue({
      loops: [],
      selectedLoop: null,
      execution: null,
      isLoading: false,
      error: null,
      refreshLoops: vi.fn(),
      loadActiveLoop: vi.fn(),
      selectLoop: vi.fn(),
    });

    // Act
    render(<LoopStatusPanel chatId="test-chat" />);

    // Assert
    expect(screen.getByText('暂无Loop定义')).toBeDefined();
  });

  it('有 Loop 时正确渲染节点列表', () => {
    // Arrange
    const mockNodes = [
      {
        node_id: 'node-1',
        node_type: 'normal' as const,
        agent_name: '执行者',
        role_description: '执行代码',
        output_schema_prompt: null,
        output_schema_fields: null,
        max_retries: 3,
      },
      {
        node_id: 'node-2',
        node_type: 'terminator' as const,
        agent_name: '审查者',
        role_description: '审查代码',
        output_schema_prompt: null,
        output_schema_fields: null,
        max_retries: 3,
      },
    ];

    mockUseLoopStatus.mockReturnValue({
      loops: [
        {
          loop_id: 'loop-1',
          name: '测试循环',
          nodes: mockNodes,
          max_iterations: 5,
        },
      ],
      selectedLoop: {
        loop_id: 'loop-1',
        name: '测试循环',
        nodes: mockNodes,
        max_iterations: 5,
      },
      execution: {
        execution_id: 'exec-1',
        status: 'running',
        current_iteration: 2,
        current_node_index: 0,
        error_message: null,
      },
      isLoading: false,
      error: null,
      refreshLoops: vi.fn(),
      loadActiveLoop: vi.fn(),
      selectLoop: vi.fn(),
    });

    // Act
    render(<LoopStatusPanel chatId="test-chat" />);

    // Assert
    expect(screen.getByText('执行者')).toBeDefined();
    expect(screen.getByText('执行代码')).toBeDefined();
    expect(screen.getByText('审查者')).toBeDefined();
    expect(screen.getByText('审查代码')).toBeDefined();
    expect(screen.getByText('迭代 2 / 5')).toBeDefined();
    expect(screen.getByText('运行中')).toBeDefined();
  });

  it('节点状态样式正确映射', () => {
    // Arrange
    const mockNodes = [
      {
        node_id: 'node-1',
        node_type: 'normal' as const,
        agent_name: '节点1',
        role_description: '已完成',
        output_schema_prompt: null,
        output_schema_fields: null,
        max_retries: 3,
      },
      {
        node_id: 'node-2',
        node_type: 'normal' as const,
        agent_name: '节点2',
        role_description: '当前执行',
        output_schema_prompt: null,
        output_schema_fields: null,
        max_retries: 3,
      },
      {
        node_id: 'node-3',
        node_type: 'normal' as const,
        agent_name: '节点3',
        role_description: '待执行',
        output_schema_prompt: null,
        output_schema_fields: null,
        max_retries: 3,
      },
    ];

    mockUseLoopStatus.mockReturnValue({
      loops: [
        {
          loop_id: 'loop-1',
          name: '测试循环',
          nodes: mockNodes,
          max_iterations: 5,
        },
      ],
      selectedLoop: {
        loop_id: 'loop-1',
        name: '测试循环',
        nodes: mockNodes,
        max_iterations: 5,
      },
      execution: {
        execution_id: 'exec-1',
        status: 'running',
        current_iteration: 1,
        current_node_index: 1, // 当前执行节点2
        error_message: null,
      },
      isLoading: false,
      error: null,
      refreshLoops: vi.fn(),
      loadActiveLoop: vi.fn(),
      selectLoop: vi.fn(),
    });

    // Act
    const { container } = render(<LoopStatusPanel chatId="test-chat" />);

    // Assert - 验证节点样式类存在
    const nodeElements = container.querySelectorAll('[class*="loopNode"]');
    expect(nodeElements.length).toBeGreaterThanOrEqual(3);
  });

  it('未激活的 Loop 显示为灰色状态', () => {
    // Arrange
    mockUseLoopStatus.mockReturnValue({
      loops: [
        {
          loop_id: 'loop-1',
          name: '测试循环',
          nodes: [],
          max_iterations: 5,
        },
      ],
      selectedLoop: {
        loop_id: 'loop-1',
        name: '测试循环',
        nodes: [],
        max_iterations: 5,
      },
      execution: null, // 未激活
      isLoading: false,
      error: null,
      refreshLoops: vi.fn(),
      loadActiveLoop: vi.fn(),
      selectLoop: vi.fn(),
    });

    // Act
    render(<LoopStatusPanel chatId="test-chat" />);

    // Assert - 不显示状态标识
    expect(screen.queryByText('运行中')).toBeNull();
    expect(screen.queryByText('已暂停')).toBeNull();
  });

  it('点击节点列表打开模态框', () => {
    // Arrange
    const mockNodes = [
      {
        node_id: 'node-1',
        node_type: 'normal' as const,
        agent_name: '执行者',
        role_description: '执行代码',
        output_schema_prompt: null,
        output_schema_fields: null,
        max_retries: 3,
      },
    ];

    mockUseLoopStatus.mockReturnValue({
      loops: [
        {
          loop_id: 'loop-1',
          name: '测试循环',
          nodes: mockNodes,
          max_iterations: 5,
        },
      ],
      selectedLoop: {
        loop_id: 'loop-1',
        name: '测试循环',
        nodes: mockNodes,
        max_iterations: 5,
      },
      execution: {
        execution_id: 'exec-1',
        status: 'running',
        current_iteration: 1,
        current_node_index: 0,
        error_message: null,
      },
      isLoading: false,
      error: null,
      refreshLoops: vi.fn(),
      loadActiveLoop: vi.fn(),
      selectLoop: vi.fn(),
    });

    // Act
    render(<LoopStatusPanel chatId="test-chat" />);

    // 点击节点列表区域
    const nodeList = screen.getByText('执行者').closest('[class*="loopNodeList"]');
    if (nodeList) {
      fireEvent.click(nodeList);
    }

    // Assert - 模态框应该显示（检查模态框特有的内容）
    expect(screen.getByText('第 1 轮 / 共 5 轮')).toBeDefined();
  });
});
