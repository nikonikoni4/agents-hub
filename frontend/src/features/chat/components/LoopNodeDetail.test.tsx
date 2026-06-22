/**
 * LoopNodeDetail 组件测试
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoopNodeDetail } from './LoopNodeDetail';
import type { LoopNodeApiItem } from '@/shared/types';

describe('LoopNodeDetail', () => {
  const mockNode: LoopNodeApiItem = {
    node_id: 'node-1',
    node_type: 'normal',
    agent_name: '执行者',
    role_description: '负责执行代码修改',
    output_schema_prompt: '请输出实现代码和修改说明',
    output_schema_fields: ['## 实现代码', '## 修改说明'],
    max_retries: 3,
  };

  it('显示节点的 role_description', () => {
    // Arrange & Act
    render(<LoopNodeDetail node={mockNode} />);

    // Assert
    expect(screen.getByText('负责执行代码修改')).toBeDefined();
  });

  it('显示节点的 output_schema_prompt', () => {
    // Arrange & Act
    render(<LoopNodeDetail node={mockNode} />);

    // Assert
    expect(screen.getByText('请输出实现代码和修改说明')).toBeDefined();
  });

  it('显示节点的 output_schema_fields', () => {
    // Arrange & Act
    render(<LoopNodeDetail node={mockNode} />);

    // Assert
    expect(screen.getByText('## 实现代码')).toBeDefined();
    expect(screen.getByText('## 修改说明')).toBeDefined();
  });

  it('当 output_schema_prompt 为 null 时不显示该部分', () => {
    // Arrange
    const nodeWithoutPrompt: LoopNodeApiItem = {
      ...mockNode,
      output_schema_prompt: null,
    };

    // Act
    render(<LoopNodeDetail node={nodeWithoutPrompt} />);

    // Assert
    expect(screen.queryByText('请输出实现代码和修改说明')).toBeNull();
  });

  it('当 output_schema_fields 为 null 时不显示该部分', () => {
    // Arrange
    const nodeWithoutFields: LoopNodeApiItem = {
      ...mockNode,
      output_schema_fields: null,
    };

    // Act
    render(<LoopNodeDetail node={nodeWithoutFields} />);

    // Assert
    expect(screen.queryByText('## 实现代码')).toBeNull();
    expect(screen.queryByText('## 修改说明')).toBeNull();
  });
});
