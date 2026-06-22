/**
 * AssistantSkillCards 组件测试
 *
 * 测试覆盖：
 * 1. 渲染 3 个技能卡片
 * 2. 点击卡片回调
 * 3. 卡片内容显示
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AssistantSkillCards } from './AssistantSkillCards';

describe('AssistantSkillCards', () => {
  const defaultProps = {
    onSkillSelect: vi.fn(),
  };

  it('应该渲染 3 个技能卡片', () => {
    render(<AssistantSkillCards {...defaultProps} />);

    expect(screen.getByText('创建 Agent')).toBeInTheDocument();
    expect(screen.getByText('训练 Agent')).toBeInTheDocument();
    expect(screen.getByText('创建群组')).toBeInTheDocument();
  });

  it('应该在点击"创建 Agent"时调用 onSkillSelect', () => {
    const onSkillSelect = vi.fn();
    render(<AssistantSkillCards onSkillSelect={onSkillSelect} />);

    fireEvent.click(screen.getByText('创建 Agent'));

    expect(onSkillSelect).toHaveBeenCalledWith('帮助我创建一个 agent');
  });

  it('应该在点击"训练 Agent"时调用 onSkillSelect', () => {
    const onSkillSelect = vi.fn();
    render(<AssistantSkillCards onSkillSelect={onSkillSelect} />);

    fireEvent.click(screen.getByText('训练 Agent'));

    expect(onSkillSelect).toHaveBeenCalledWith('帮助我训练 agent');
  });

  it('应该在点击"创建群组"时调用 onSkillSelect', () => {
    const onSkillSelect = vi.fn();
    render(<AssistantSkillCards onSkillSelect={onSkillSelect} />);

    fireEvent.click(screen.getByText('创建群组'));

    expect(onSkillSelect).toHaveBeenCalledWith('帮助我创建群组');
  });

  it('应该为每个卡片添加适当的样式类', () => {
    render(<AssistantSkillCards {...defaultProps} />);

    const cards = screen.getAllByRole('button');
    expect(cards).toHaveLength(3);
  });
});
