/**
 * 右侧栏内容类型定义
 */
export type RightSidebarContent =
  | { type: 'preview'; content: string; filePath: string }
  | { type: 'diff'; content: string; filePath: string }
  | { type: 'web'; url: string; title?: string };
