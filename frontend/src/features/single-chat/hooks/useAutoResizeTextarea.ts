import { useCallback, useEffect, useRef } from 'react';

/**
 * textarea 高度自适应 hook
 *
 * 根据内容自动调整 textarea 高度：
 * - 最小高度：1 行
 * - 最大高度：150px（可通过参数覆盖）
 * - 超过后显示滚动条
 */
export function useAutoResizeTextarea(maxHeight = 150) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // 重置高度以获取正确的 scrollHeight
    textarea.style.height = 'auto';

    // 计算新高度
    const newHeight = Math.min(textarea.scrollHeight, maxHeight);
    textarea.style.height = `${newHeight}px`;

    // 超过最大高度时显示滚动条
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? 'auto' : 'hidden';
  }, [maxHeight]);

  // 内容变化时调整高度
  useEffect(() => {
    adjustHeight();
  }, [adjustHeight]);

  return { textareaRef, adjustHeight };
}
