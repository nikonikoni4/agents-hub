/**
 * 群聊成员 hook（转发 shared 层）
 *
 * 实际实现位于 shared/hooks/useGroupChatMembers.ts
 * 此处仅为 feature 内部提供便捷导入
 */

export {
  useGroupChatMembers as useSingleChatMembers,
  type MemberWithRole,
} from '@/shared/hooks/useGroupChatMembers';
