/**
 * 工具调用卡片组件
 *
 * 显示工具调用的名称和输入参数，默认折叠详细内容
 */

import { useState } from 'react';
import type { ToolCall } from '@/shared/types';
import styles from './ToolCallCard.module.css';

interface ToolCallCardProps {
  toolCall: ToolCall;
  /** 是否默认展开（流式输出时可能需要展开） */
  defaultExpanded?: boolean;
}

export function ToolCallCard({ toolCall, defaultExpanded = false }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className={styles.card}>
      <button
        className={styles.header}
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <span className={styles.icon}>🔧</span>
        <span className={styles.name}>{toolCall.name}</span>
        <span className={styles.expandIcon}>{expanded ? '▼' : '▶'}</span>
      </button>
      {expanded && (
        <div className={styles.content}>
          <pre className={styles.input}>
            {JSON.stringify(toolCall.input, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
