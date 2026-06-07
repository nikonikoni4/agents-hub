import React, { useMemo } from 'react';
import styles from './DiffViewer.module.css';

interface DiffLine {
  type: 'add' | 'del' | 'context' | 'hunk' | 'header';
  oldNum?: number;
  newNum?: number;
  content: string;
}

function parseDiff(diff: string): DiffLine[] {
  const lines = diff.split('\n');
  const result: DiffLine[] = [];
  let oldNum = 0;
  let newNum = 0;

  for (const line of lines) {
    // 文件头
    if (line.startsWith('diff --git') || line.startsWith('---') || line.startsWith('+++')) {
      result.push({ type: 'header', content: line });
      continue;
    }

    // hunk 头 @@ -a,b +c,d @@
    const hunkMatch = line.match(/^@@\s+-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@(.*)$/);
    if (hunkMatch?.[1] && hunkMatch[2]) {
      oldNum = parseInt(hunkMatch[1], 10);
      newNum = parseInt(hunkMatch[2], 10);
      result.push({ type: 'hunk', content: line });
      continue;
    }

    // 新增行
    if (line.startsWith('+')) {
      result.push({ type: 'add', newNum: newNum++, content: line.slice(1) });
      continue;
    }

    // 删除行
    if (line.startsWith('-')) {
      result.push({ type: 'del', oldNum: oldNum++, content: line.slice(1) });
      continue;
    }

    // 上下文行（无变化）
    if (line.startsWith(' ')) {
      result.push({ type: 'context', oldNum: oldNum++, newNum: newNum++, content: line.slice(1) });
      continue;
    }

    // 其他（空行等）
    if (line.trim() === '') {
      result.push({ type: 'context', content: '' });
      continue;
    }

    result.push({ type: 'context', content: line });
  }

  return result;
}

export interface DiffViewerProps {
  diff: string;
}

export const DiffViewer = React.memo(({ diff }: DiffViewerProps) => {
  const lines = useMemo(() => parseDiff(diff), [diff]);

  if (!diff || lines.length === 0) {
    return <div className={styles.empty}>无代码差异</div>;
  }

  return (
    <div className={styles.container}>
      <table className={styles.table}>
        <tbody>
          {lines.map((line, i) => (
            <tr key={i} className={styles[line.type]}>
              <td className={styles.lineNum}>{line.oldNum ?? ''}</td>
              <td className={styles.lineNum}>{line.newNum ?? ''}</td>
              <td className={styles.prefix}>
                {line.type === 'add'
                  ? '+'
                  : line.type === 'del'
                    ? '-'
                    : line.type === 'hunk'
                      ? '@'
                      : ' '}
              </td>
              <td className={styles.content}>
                <code>{line.content}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
});
