/**
 * 右侧栏内容类型定义
 */
export interface RightSidebarContent {
  type: 'preview' | 'diff';
  content: string;
  filePath: string;
}
