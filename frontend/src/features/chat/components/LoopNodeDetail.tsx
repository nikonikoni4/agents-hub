/**
 * LoopNodeDetail 组件
 *
 * 显示 Loop 节点的详细信息，包括职责描述、输出格式提示词和必需字段列表。
 * 在 LoopDetailModal 中点击节点时显示在节点图右侧。
 */

import type { LoopNodeApiItem } from '@/shared/types';
import styles from './LoopNodeDetail.module.css';

interface LoopNodeDetailProps {
  node: LoopNodeApiItem;
}

export function LoopNodeDetail({ node }: LoopNodeDetailProps) {
  return (
    <div className={styles.container}>
      {/* 节点标题 */}
      <div className={styles.header}>
        <span className={styles.nodeName}>{node.agent_name}</span>
        <span className={styles.nodeType}>
          {node.node_type === 'terminator' ? '判断节点' : '执行节点'}
        </span>
      </div>

      {/* 职责描述 */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>职责描述</div>
        <div className={styles.sectionContent}>{node.role_description}</div>
      </div>

      {/* 输出格式提示词 */}
      {node.output_schema_prompt && (
        <div className={styles.section}>
          <div className={styles.sectionLabel}>输出格式提示词</div>
          <div className={styles.sectionContent}>{node.output_schema_prompt}</div>
        </div>
      )}

      {/* 必需字段列表 */}
      {node.output_schema_fields && node.output_schema_fields.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionLabel}>必需字段</div>
          <ul className={styles.fieldList}>
            {node.output_schema_fields.map((field, index) => (
              <li key={index} className={styles.fieldItem}>
                {field}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
