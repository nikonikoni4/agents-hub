/**
 * 技能卡片组件
 *
 * 显示在输入框上方，提供常用操作的快捷入口。
 * 点击卡片将 prompt 预填到输入框，不直接发送消息。
 */

import { useCallback } from 'react';
import styles from './AssistantSkillCards.module.css';

interface SkillCard {
  id: string;
  label: string;
  prompt: string;
  icon: string;
}

const SKILL_CARDS: SkillCard[] = [
  { id: 'create-agent', label: '创建 Agent', prompt: '帮助我创建一个 agent', icon: '👤' },
  { id: 'train-agent', label: '训练 Agent', prompt: '帮助我训练 agent', icon: '🎓' },
  { id: 'create-group', label: '创建群组', prompt: '帮助我创建群组', icon: '👥' },
];

interface AssistantSkillCardsProps {
  onSkillSelect: (prompt: string) => void;
}

export function AssistantSkillCards({ onSkillSelect }: AssistantSkillCardsProps) {
  const handleClick = useCallback(
    (prompt: string) => {
      onSkillSelect(prompt);
    },
    [onSkillSelect]
  );

  return (
    <div className={styles.container}>
      {SKILL_CARDS.map((skill) => (
        <button
          key={skill.id}
          type="button"
          className={styles.skillCard}
          onClick={() => handleClick(skill.prompt)}
        >
          <span className={styles.skillIcon}>{skill.icon}</span>
          <span>{skill.label}</span>
        </button>
      ))}
    </div>
  );
}
