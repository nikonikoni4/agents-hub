/**
 * LoopDetailModal 组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LoopDetailModal } from './LoopDetailModal';
import type { LoopDetailApiResponse, LoopExecutionApiItem } from '@/shared/types';

describe('LoopDetailModal', () => {
  const mockLoop: LoopDetailApiResponse = {
    loop_id: 'loop-1',
    name: '测试循环',
    nodes: [
      {
        node_id: 'node-1',
        node_type: 'normal',
        agent_name: '执行者',
        role_description: '执行代码',
        output_schema_prompt: null,
        output_schema_fields: null,
        max_retries: 3,
      },
      {
        node_id: 'node-2',
        node_type: 'normal',
        agent_name: '审查者',
        role_description: '审查代码',
        output_schema_prompt: null,
        output_schema_fields: null,
        max_retries: 3,
      },
      {
        node_id: 'node-3',
        node_type: 'terminator',
        agent_name: '判断者',
        role_description: '判断是否继续',
        output_schema_prompt: null,
        output_schema_fields: null,
        max_retries: 3,
      },
    ],
    max_iterations: 5,
  };

  const mockExecution: LoopExecutionApiItem = {
    execution_id: 'exec-1',
    status: 'running',
    current_iteration: 2,
    current_node_index: 1,
    error_message: null,
  };

  const mockOnClose = vi.fn();

  it('不显示模态框当 isOpen 为 false', () => {
    // Arrange & Act
    render(
      <LoopDetailModal
        isOpen={false}
        loop={mockLoop}
        execution={mockExecution}
        onClose={mockOnClose}
      />
    );

    // Assert
    expect(screen.queryByText('测试循环')).toBeNull();
  });

  it('显示模态框当 isOpen 为 true', () => {
    // Arrange & Act
    render(
      <LoopDetailModal
        isOpen={true}
        loop={mockLoop}
        execution={mockExecution}
        onClose={mockOnClose}
      />
    );

    // Assert
    expect(screen.getByText('测试循环')).toBeDefined();
    expect(screen.getByText('执行者')).toBeDefined();
    expect(screen.getByText('审查者')).toBeDefined();
    expect(screen.getByText('判断者')).toBeDefined();
  });

  it('显示迭代次数', () => {
    // Arrange & Act
    render(
      <LoopDetailModal
        isOpen={true}
        loop={mockLoop}
        execution={mockExecution}
        onClose={mockOnClose}
      />
    );

    // Assert
    expect(screen.getByText(/迭代 2 \/ 5/)).toBeDefined();
  });

  it('显示错误信息当 Loop 失败时', () => {
    // Arrange
    const failedExecution: LoopExecutionApiItem = {
      ...mockExecution,
      status: 'failed',
      error_message: '节点执行超时',
    };

    // Act
    render(
      <LoopDetailModal
        isOpen={true}
        loop={mockLoop}
        execution={failedExecution}
        onClose={mockOnClose}
      />
    );

    // Assert
    expect(screen.getByText('失败')).toBeDefined();
    expect(screen.getByText('节点执行超时')).toBeDefined();
  });

  it('未激活时显示未激活状态', () => {
    // Arrange & Act
    render(
      <LoopDetailModal isOpen={true} loop={mockLoop} execution={null} onClose={mockOnClose} />
    );

    // Assert
    expect(screen.getByText('未激活')).toBeDefined();
  });

  it('点击节点显示详情面板', () => {
    // Arrange
    const loopWithSchema: LoopDetailApiResponse = {
      ...mockLoop,
      nodes: [
        {
          ...mockLoop.nodes[0]!,
          output_schema_prompt: '请输出实现代码',
          output_schema_fields: ['## 实现代码', '## 修改说明'],
        },
        mockLoop.nodes[1]!,
        mockLoop.nodes[2]!,
      ],
    };

    render(
      <LoopDetailModal
        isOpen={true}
        loop={loopWithSchema}
        execution={mockExecution}
        onClose={mockOnClose}
      />
    );

    // Act - 点击第一个节点
    fireEvent.click(screen.getByText('执行者'));

    // Assert - 详情面板显示节点信息（节点列表和详情面板中都有 role_description）
    expect(screen.getAllByText('执行代码').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('请输出实现代码')).toBeDefined();
    expect(screen.getByText('## 实现代码')).toBeDefined();
  });

  it('显示 loopBack 区域当有执行状态时', () => {
    // Arrange & Act
    const { container } = render(
      <LoopDetailModal
        isOpen={true}
        loop={mockLoop}
        execution={mockExecution}
        onClose={mockOnClose}
      />
    );

    // Assert - loopBack 区域显示迭代标签
    expect(screen.getByText(/第 2 轮 \/ 共 5 轮/)).toBeDefined();
    // SVG 弧线箭头存在
    expect(container.querySelector('svg')).toBeDefined();
  });

  it('不显示 loopBack 区域当无执行状态时', () => {
    // Arrange & Act
    render(
      <LoopDetailModal isOpen={true} loop={mockLoop} execution={null} onClose={mockOnClose} />
    );

    // Assert - loopBack 区域不存在
    expect(screen.queryByText(/第.*轮 \/ 共.*轮/)).toBeNull();
  });
});
