/**
 * 群聊相关 API 接口
 *
 * 提供群聊的 CRUD 操作和消息管理
 */

import apiClient, { mockableRequest } from './client';
import type {
  AddMembersRequest,
  GroupChatApiResponse,
  GroupChatInfoApiResponse,
  GroupChatMemberApiItem,
  MessageApiItem,
  CreateGroupChatRequest,
  SendMessageRequest,
  UpdateDockerModeRequest,
  SuccessResponse,
  PinnedMessageInfo,
  PinMessageRequest,
  PinOperationResponse,
  AgentCallInfo,
  TaskListInfo,
  UploadedFileInfo,
  CompressApiResponse,
  CompressAllApiResponse,
} from '@/shared/types';

// ==================== Mock 数据 ====================

const MOCK_GROUP_CHAT: GroupChatApiResponse = {
  group_chat_id: 'mock-chat-001',
  group_chat_name: 'Test Chat',
  project_path: '/home/user/project',
  created_at: '2026-06-03T10:00:00Z',
  group_type: 'sequence_execute',
  is_active: true,
};

const MOCK_GROUP_CHATS: GroupChatApiResponse[] = [
  {
    group_chat_id: 'mock-chat-001',
    group_chat_name: 'Frontend Development Team',
    project_path: '/home/user/projects/frontend-app',
    created_at: '2026-06-03T10:00:00Z',
    group_type: 'manager_orchestrate',
    is_active: true,
  },
  {
    group_chat_id: 'mock-chat-002',
    group_chat_name: 'Backend API Team',
    project_path: '/home/user/projects/backend-api',
    created_at: '2026-06-02T15:30:00Z',
    group_type: 'sequence_execute',
    is_active: true,
  },
  {
    group_chat_id: 'mock-chat-003',
    group_chat_name: 'Code Review Session',
    project_path: '/home/user/projects/legacy-system',
    created_at: '2026-06-01T09:15:00Z',
    group_type: 'manager_orchestrate',
    is_active: false,
  },
  {
    group_chat_id: 'mock-chat-004',
    group_chat_name: 'Database Migration',
    project_path: '/home/user/projects/db-migration',
    created_at: '2026-05-31T14:20:00Z',
    group_type: 'sequence_execute',
    is_active: true,
  },
  {
    group_chat_id: 'mock-chat-005',
    group_chat_name: 'Testing & QA',
    project_path: '/home/user/projects/test-automation',
    created_at: '2026-05-30T08:45:00Z',
    group_type: 'manager_orchestrate',
    is_active: false,
  },
];

const MOCK_GROUP_CHAT_INFOS: GroupChatInfoApiResponse[] = [
  {
    group_chat_id: 'mock-chat-001',
    group_chat_name: 'Frontend Development Team',
    project_path: '/home/user/projects/frontend-app',
    created_at: '2026-06-03T10:00:00Z',
    group_type: 'manager_orchestrate',
    is_active: true,
    last_speaker: 'Leader',
    last_message: '前端组件已完成开发，准备提交代码审查',
    last_update_at: '2026-06-03T11:30:00Z',
  },
  {
    group_chat_id: 'mock-chat-002',
    group_chat_name: 'Backend API Team',
    project_path: '/home/user/projects/backend-api',
    created_at: '2026-06-02T15:30:00Z',
    group_type: 'sequence_execute',
    is_active: true,
    last_speaker: 'Developer',
    last_message: 'API 接口文档已更新，包含新的认证端点',
    last_update_at: '2026-06-02T16:45:00Z',
  },
  {
    group_chat_id: 'mock-chat-003',
    group_chat_name: 'Code Review Session',
    project_path: '/home/user/projects/legacy-system',
    created_at: '2026-06-01T09:15:00Z',
    group_type: 'manager_orchestrate',
    is_active: false,
    last_speaker: 'user',
    last_message: '请检查认证模块的安全性问题',
    last_update_at: '2026-06-01T10:00:00Z',
  },
  {
    group_chat_id: 'mock-chat-004',
    group_chat_name: 'Database Migration',
    project_path: '/home/user/projects/db-migration',
    created_at: '2026-05-31T14:20:00Z',
    group_type: 'sequence_execute',
    is_active: true,
    last_speaker: 'Leader',
    last_message: '迁移脚本已准备就绪，建议在低峰期执行',
    last_update_at: '2026-05-31T15:30:00Z',
  },
  {
    group_chat_id: 'mock-chat-005',
    group_chat_name: 'Testing & QA',
    project_path: '/home/user/projects/test-automation',
    created_at: '2026-05-30T08:45:00Z',
    group_type: 'manager_orchestrate',
    is_active: false,
    last_speaker: 'Tester',
    last_message: '单元测试覆盖率已达到 85%',
    last_update_at: '2026-05-30T09:15:00Z',
  },
];

// 按 chatId 分组的 mock 消息数据
const MOCK_MESSAGES_BY_CHAT: Record<string, MessageApiItem[]> = {
  'mock-chat-001': [
    {
      id: 1,
      speaker: 'user',
      content: '我们需要开发一个新的用户仪表板页面，包含数据可视化组件。',
      timestamp: '2026-06-03T10:00:00Z',
      platform: 'user',
    },
    {
      id: 2,
      speaker: 'Leader',
      content: '好的，我来负责前端组件开发。建议使用 Recharts 库来实现图表功能。',
      timestamp: '2026-06-03T10:00:05Z',
      platform: 'claude',
    },
    {
      id: 3,
      speaker: 'Developer',
      content: '我可以处理后端 API 接口，提供用户统计数据。',
      timestamp: '2026-06-03T10:00:12Z',
      platform: 'codex',
    },
  ],
  'mock-chat-002': [
    {
      id: 1,
      speaker: 'user',
      content: '请帮我设计用户认证系统的 API 接口。',
      timestamp: '2026-06-02T15:30:00Z',
      platform: 'user',
    },
    {
      id: 2,
      speaker: 'Leader',
      content: '我建议采用 JWT + Refresh Token 的方案，access token 设置 15 分钟过期。',
      timestamp: '2026-06-02T15:30:05Z',
      platform: 'claude',
    },
    {
      id: 3,
      speaker: 'user',
      content: '好的，请输出完整的 API 文档。',
      timestamp: '2026-06-02T15:31:00Z',
      platform: 'user',
    },
    {
      id: 4,
      speaker: 'Leader',
      content: 'API 文档已更新，包含登录、注册、刷新 token、登出四个端点。',
      timestamp: '2026-06-02T16:45:00Z',
      platform: 'claude',
    },
  ],
  'mock-chat-003': [
    {
      id: 1,
      speaker: 'user',
      content: '请检查认证模块的安全性问题。',
      timestamp: '2026-06-01T09:15:00Z',
      platform: 'user',
    },
    {
      id: 2,
      speaker: 'Leader',
      content:
        '已发现几个安全问题：1. 密码验证过于简单 2. JWT token 过期时间过长 3. refresh token 存储在 localStorage',
      timestamp: '2026-06-01T09:15:10Z',
      platform: 'claude',
    },
    {
      id: 3,
      speaker: 'Designer',
      content: '建议使用 httpOnly cookie 存储 refresh token，并添加 CSRF 保护。',
      timestamp: '2026-06-01T09:15:20Z',
      platform: 'codex',
    },
  ],
};

// 默认 mock 消息（用于未匹配的 chatId）
const MOCK_MESSAGES_DEFAULT: MessageApiItem[] = [
  {
    id: 1,
    speaker: 'user',
    content: '开始新会话。',
    timestamp: '2026-06-03T10:00:00Z',
    platform: 'user',
  },
  {
    id: 2,
    speaker: 'Leader',
    content: '收到，准备就绪。',
    timestamp: '2026-06-03T10:00:05Z',
    platform: 'claude',
  },
  {
    id: 3,
    speaker: 'Leader',
    content: '[权限请求] 文件系统读取权限',
    timestamp: '2026-06-03T10:01:00Z',
    platform: 'claude',
    permission_request: {
      request_id: 'perm-req-001',
      title: '文件系统读取权限',
      content: '请求读取项目目录 ~/projects/agents-hub 下的文件，用于分析代码结构并生成架构文档。',
      status: 'pending',
      requested_by: 'Leader',
    },
  },
  {
    id: 4,
    speaker: 'Developer',
    content: '[权限请求] 执行终端命令',
    timestamp: '2026-06-03T10:02:00Z',
    platform: 'codex',
    permission_request: {
      request_id: 'perm-req-002',
      title: '执行终端命令',
      content: '需要执行 npm run build 来验证构建是否成功。',
      status: 'pending',
      requested_by: 'Developer',
    },
  },
];

const MOCK_MEMBERS: Record<string, GroupChatMemberApiItem[]> = {
  'mock-chat-001': [
    {
      name: 'Leader',
      main_session: 'session-leader-001',
      btw_session: [],
      cwd: '/home/user/projects/frontend-app',
      use_docker: false,
      status: 'idle',
      context_usage: null,
    },
    {
      name: 'Developer',
      main_session: 'session-dev-001',
      btw_session: [],
      cwd: '/home/user/projects/frontend-app',
      use_docker: true,
      status: 'busy',
      context_usage: null,
    },
  ],
  'mock-chat-002': [
    {
      name: 'Leader',
      main_session: 'session-leader-002',
      btw_session: [],
      cwd: '/home/user/projects/backend-api',
      use_docker: false,
      status: 'idle',
      context_usage: null,
    },
    {
      name: 'Developer',
      main_session: 'session-dev-002',
      btw_session: ['session-dev-002-btw'],
      cwd: '/home/user/projects/backend-api',
      use_docker: true,
      status: 'busy',
      context_usage: null,
    },
    {
      name: 'Tester',
      main_session: 'session-tester-001',
      btw_session: [],
      cwd: '/home/user/projects/backend-api',
      use_docker: false,
      status: 'idle',
      context_usage: null,
    },
  ],
  'mock-chat-003': [
    {
      name: 'Leader',
      main_session: 'session-leader-003',
      btw_session: [],
      cwd: '/home/user/projects/legacy-system',
      use_docker: false,
      status: 'idle',
      context_usage: null,
    },
    {
      name: 'Designer',
      main_session: 'session-designer-001',
      btw_session: [],
      cwd: '/home/user/projects/legacy-system',
      use_docker: false,
      status: 'idle',
      context_usage: null,
    },
  ],
};

const MOCK_PINNED_MESSAGES: PinnedMessageInfo[] = [];

const MOCK_PIN_OPERATION: PinOperationResponse = { ok: true };

const MOCK_PIN_RESULT: PinnedMessageInfo = {
  message_id: 0,
  speaker: '',
  content: '',
  timestamp: '',
  platform: '',
  pinned_at: '',
};

const MOCK_AGENT_CALLS: AgentCallInfo[] = [
  {
    call_id: 'call-001',
    send_from: 'Leader',
    send_to: 'Developer',
    content: '请帮我分析这个数据集的特征分布',
    message_type: 'task',
    status: 'running',
    created_at: '2026-06-07T10:00:00Z',
    started_at: '2026-06-07T10:00:02Z',
    completed_at: null,
    error: null,
  },
  {
    call_id: 'call-002',
    send_from: 'Leader',
    send_to: 'Tester',
    content: '等待确认测试方案',
    message_type: 'notification',
    status: 'pending',
    created_at: '2026-06-07T10:01:00Z',
    started_at: null,
    completed_at: null,
    error: null,
  },
  {
    call_id: 'call-003',
    send_from: 'Developer',
    send_to: 'Leader',
    content: '数据分析完成，结果已提交',
    message_type: 'task',
    status: 'completed',
    created_at: '2026-06-07T09:58:00Z',
    started_at: '2026-06-07T09:58:01Z',
    completed_at: '2026-06-07T09:58:05Z',
    error: null,
  },
  {
    call_id: 'call-004',
    send_from: 'Tester',
    send_to: 'Leader',
    content: '超时未响应',
    message_type: 'notification',
    status: 'failed',
    created_at: '2026-06-07T09:55:00Z',
    started_at: '2026-06-07T09:55:01Z',
    completed_at: '2026-06-07T09:55:09Z',
    error: 'Agent response timeout',
  },
  {
    call_id: 'call-005',
    send_from: 'Leader',
    send_to: 'Designer',
    content: '请设计用户仪表板的 UI 原型',
    message_type: 'task',
    status: 'completed',
    created_at: '2026-06-07T09:40:00Z',
    started_at: '2026-06-07T09:40:01Z',
    completed_at: '2026-06-07T09:42:30Z',
    error: null,
  },
  {
    call_id: 'call-006',
    send_from: 'Developer',
    send_to: 'Tester',
    content: '请对新增的 API 端点进行单元测试',
    message_type: 'task',
    status: 'completed',
    created_at: '2026-06-07T09:30:00Z',
    started_at: '2026-06-07T09:30:02Z',
    completed_at: '2026-06-07T09:35:10Z',
    error: null,
  },
  {
    call_id: 'call-007',
    send_from: 'Tester',
    send_to: 'Developer',
    content: '发现登录接口返回 500 错误',
    message_type: 'notification',
    status: 'completed',
    created_at: '2026-06-07T09:20:00Z',
    started_at: '2026-06-07T09:20:01Z',
    completed_at: '2026-06-07T09:20:03Z',
    error: null,
  },
];

const MOCK_TASK_LIST: TaskListInfo = {
  list_id: 'tasklist-001',
  status: 'active',
  tasks: [
    {
      task_id: 'task-001',
      owner: 'Developer',
      content: '数据清洗',
      status: 'completed',
      created_by: 'Leader',
      created_at: '2026-06-07T09:00:00Z',
      updated_at: '2026-06-07T09:30:00Z',
    },
    {
      task_id: 'task-002',
      owner: 'Developer',
      content: '特征工程',
      status: 'completed',
      created_by: 'Leader',
      created_at: '2026-06-07T09:00:00Z',
      updated_at: '2026-06-07T09:45:00Z',
    },
    {
      task_id: 'task-003',
      owner: 'Developer',
      content: '模型训练',
      status: 'running',
      created_by: 'Leader',
      created_at: '2026-06-07T09:00:00Z',
      updated_at: '2026-06-07T10:00:00Z',
    },
    {
      task_id: 'task-004',
      owner: 'Tester',
      content: '结果验证',
      status: 'pending',
      created_by: 'Leader',
      created_at: '2026-06-07T09:00:00Z',
      updated_at: '2026-06-07T09:00:00Z',
    },
    {
      task_id: 'task-005',
      owner: 'Leader',
      content: '报告撰写',
      status: 'pending',
      created_by: 'Leader',
      created_at: '2026-06-07T09:00:00Z',
      updated_at: '2026-06-07T09:00:00Z',
    },
  ],
  created_at: '2026-06-07T09:00:00Z',
};

// ==================== API 接口 ====================

/**
 * 创建并启动新群聊
 */
export async function createGroupChat(data: CreateGroupChatRequest): Promise<GroupChatApiResponse> {
  return mockableRequest(
    () => apiClient.post<GroupChatApiResponse>('/group-chats', data),
    MOCK_GROUP_CHAT
  );
}

/**
 * 获取群聊详细信息
 */
export async function getGroupChatInfo(chatId: string): Promise<GroupChatApiResponse> {
  return mockableRequest(
    () => apiClient.get<GroupChatApiResponse>(`/group-chats/${chatId}`),
    MOCK_GROUP_CHAT
  );
}

/**
 * 列出所有群聊
 *
 * @param isActiveOnly - 是否只返回活跃群聊
 */
export async function listGroupChats(
  isActiveOnly: boolean = false
): Promise<GroupChatApiResponse[]> {
  return mockableRequest(
    () =>
      apiClient.get<GroupChatApiResponse[]>('/group-chats', {
        params: { is_active_only: isActiveOnly },
      }),
    isActiveOnly ? MOCK_GROUP_CHATS.filter((c) => c.is_active) : MOCK_GROUP_CHATS
  );
}

/**
 * 列出所有群聊（包含 Session 列表扩展信息）
 *
 * 返回包含 last_speaker、last_message、last_update_at 的完整信息
 * 用于 Session 列表展示
 *
 * @param isActiveOnly - 是否只返回活跃群聊
 */
export async function listGroupChatInfos(
  isActiveOnly: boolean = false
): Promise<GroupChatInfoApiResponse[]> {
  return mockableRequest(
    () =>
      apiClient.get<GroupChatInfoApiResponse[]>('/group-chats', {
        params: { is_active_only: isActiveOnly, include_info: true },
      }),
    isActiveOnly ? MOCK_GROUP_CHAT_INFOS.filter((c) => c.is_active) : MOCK_GROUP_CHAT_INFOS
  );
}

/**
 * 获取消息历史
 *
 * @param chatId - 群聊 ID
 * @param limit - 返回消息数量上限（1-500，默认 30）
 * @param before - 游标时间戳，返回此时间之前的消息
 */
export async function getMessages(
  chatId: string,
  limit: number = 30,
  before?: string
): Promise<MessageApiItem[]> {
  return mockableRequest(
    () =>
      apiClient.get<MessageApiItem[]>(`/group-chats/${chatId}/messages`, {
        params: { limit, ...(before ? { before } : {}) },
      }),
    MOCK_MESSAGES_BY_CHAT[chatId] ?? MOCK_MESSAGES_DEFAULT
  );
}

/**
 * 获取群聊成员列表
 */
export async function getMembers(chatId: string): Promise<GroupChatMemberApiItem[]> {
  return mockableRequest(
    () => apiClient.get<GroupChatMemberApiItem[]>(`/group-chats/${chatId}/members`),
    MOCK_MEMBERS[chatId] ?? []
  );
}

/**
 * 向群聊发送消息
 */
export async function sendMessage(
  chatId: string,
  data: SendMessageRequest
): Promise<SuccessResponse> {
  return mockableRequest(
    () => apiClient.post<SuccessResponse>(`/group-chats/${chatId}/messages`, data),
    { message: 'Message sent successfully' }
  );
}

/**
 * 切换成员 Docker 沙箱模式
 */
export async function updateMemberDockerMode(
  chatId: string,
  memberName: string,
  useDocker: boolean
): Promise<GroupChatMemberApiItem> {
  const data: UpdateDockerModeRequest = { use_docker: useDocker };
  return mockableRequest(
    () =>
      apiClient.put<GroupChatMemberApiItem>(
        `/group-chats/${chatId}/${memberName}/use-docker`,
        data
      ),
    {
      ...MOCK_MEMBERS[0],
      name: memberName,
      use_docker: useDocker,
      main_session: null,
      btw_session: [],
      cwd: null,
      status: 'idle',
      context_usage: null,
    }
  );
}

/**
 * 删除群聊
 *
 * @param chatId - 群聊 ID
 * @param keepData - true=仅从内存移除，false=完全删除（默认）
 */
export async function deleteGroupChat(
  chatId: string,
  keepData: boolean = false
): Promise<SuccessResponse> {
  return mockableRequest(
    () =>
      apiClient.delete<SuccessResponse>(`/group-chats/${chatId}`, {
        params: { keep_data: keepData },
      }),
    { message: `Group chat ${chatId} deleted successfully` }
  );
}

/**
 * 获取置顶消息列表
 */
export async function getPinnedMessages(chatId: string): Promise<PinnedMessageInfo[]> {
  return mockableRequest(
    () => apiClient.get<PinnedMessageInfo[]>(`/group-chats/${chatId}/pinned-messages`),
    MOCK_PINNED_MESSAGES
  );
}

/**
 * 置顶消息
 */
export async function pinMessage(
  chatId: string,
  data: PinMessageRequest
): Promise<PinnedMessageInfo> {
  return mockableRequest(
    () => apiClient.post<PinnedMessageInfo>(`/group-chats/${chatId}/pinned-messages`, data),
    MOCK_PIN_RESULT
  );
}

/**
 * 取消置顶消息
 */
export async function unpinMessage(
  chatId: string,
  data: PinMessageRequest
): Promise<PinOperationResponse> {
  return mockableRequest(
    () =>
      apiClient.delete<PinOperationResponse>(`/group-chats/${chatId}/pinned-messages`, {
        params: data,
      }),
    MOCK_PIN_OPERATION
  );
}

/**
 * 添加群成员
 */
export async function addGroupChatMembers(
  chatId: string,
  data: AddMembersRequest
): Promise<GroupChatMemberApiItem[]> {
  return mockableRequest(
    () => apiClient.post<GroupChatMemberApiItem[]>(`/group-chats/${chatId}/members`, data),
    []
  );
}

/**
 * 删除群成员
 */
export async function removeGroupChatMember(
  chatId: string,
  memberName: string
): Promise<GroupChatMemberApiItem[]> {
  return mockableRequest(
    () =>
      apiClient.delete<GroupChatMemberApiItem[]>(`/group-chats/${chatId}/members/${memberName}`),
    []
  );
}

/**
 * 获取 Agent 调用状态列表
 */
export async function getAgentCalls(chatId: string): Promise<AgentCallInfo[]> {
  return mockableRequest(
    () => apiClient.get<AgentCallInfo[]>(`/group-chats/${chatId}/agent-calls`),
    MOCK_AGENT_CALLS
  );
}

/**
 * 获取活跃任务列表
 */
export async function getActiveTasks(chatId: string): Promise<TaskListInfo | null> {
  return mockableRequest(
    () => apiClient.get<TaskListInfo | null>(`/group-chats/${chatId}/tasks`),
    MOCK_TASK_LIST
  );
}

/**
 * 获取文件快照内容
 */
export async function getFileSnapshotContent(
  groupChatId: string,
  snapshotId: string
): Promise<string> {
  const data = await apiClient.get<{ content: string }>(
    `/group-chats/${groupChatId}/files/${snapshotId}/content`
  );
  return data.content;
}

/**
 * 获取文件快照 diff
 */
export async function getFileSnapshotDiff(
  groupChatId: string,
  snapshotId: string
): Promise<string> {
  const data = await apiClient.get<{ diff: string }>(
    `/group-chats/${groupChatId}/files/${snapshotId}/diff`
  );
  return data.diff;
}

/**
 * 更新权限请求状态
 */
export async function updatePermissionStatus(
  chatId: string,
  messageId: number,
  status: 'approved' | 'rejected'
): Promise<{ ok: boolean; message_id: number; new_status: string }> {
  return mockableRequest(
    () =>
      apiClient.patch<{ ok: boolean; message_id: number; new_status: string }>(
        `/group-chats/${chatId}/messages/${messageId}/permission`,
        { status }
      ),
    { ok: true, message_id: messageId, new_status: status }
  );
}

/**
 * 上传文件
 *
 * 注意：不使用 mockableRequest，因为文件上传没有有意义的 mock 等价物
 *
 * @param chatId - 群聊 ID
 * @param file - 文件对象
 * @returns 上传文件信息
 */
export async function uploadFile(chatId: string, file: File): Promise<UploadedFileInfo> {
  const formData = new FormData();
  formData.append('file', file);

  return apiClient.post<UploadedFileInfo>(`/group-chats/${chatId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * 压缩指定 Agent 的上下文
 */
export async function compressAgentContext(
  chatId: string,
  agentName: string
): Promise<CompressApiResponse> {
  return apiClient.post<CompressApiResponse>(
    `/group-chats/${chatId}/members/${agentName}/compress`
  );
}

/**
 * 全量压缩所有 Agent 的上下文
 */
export async function compressAllAgents(chatId: string): Promise<CompressAllApiResponse> {
  return apiClient.post<CompressAllApiResponse>(`/group-chats/${chatId}/compress-all`);
}
