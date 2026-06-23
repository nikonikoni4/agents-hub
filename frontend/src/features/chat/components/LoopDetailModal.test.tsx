/**
 * LoopDetailModal 组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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
    expect(screen.getAllByText('执行者').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('审查者').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('判断者').length).toBeGreaterThanOrEqual(1);
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

    // Assert - 默认选中第一个节点，详情面板自动显示
    expect(screen.getAllByText('执行代码').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('请输出实现代码')).toBeDefined();
    expect(screen.getByText('## 实现代码')).toBeDefined();
  });

  it('显示迭代信息当有执行状态时', () => {
    // Arrange & Act
    render(
      <LoopDetailModal
        isOpen={true}
        loop={mockLoop}
        execution={mockExecution}
        onClose={mockOnClose}
      />
    );

    // Assert - 迭代信息显示
    expect(screen.getByText(/迭代 2 \/ 5/)).toBeDefined();
  });

  it('显示迭代信息当无执行状态时', () => {
    // Arrange & Act
    render(
      <LoopDetailModal isOpen={true} loop={mockLoop} execution={null} onClose={mockOnClose} />
    );

    // Assert - 迭代信息显示默认值
    expect(screen.getByText(/迭代 0 \/ 5/)).toBeDefined();
  });
});
