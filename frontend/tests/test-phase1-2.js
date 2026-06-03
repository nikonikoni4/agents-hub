#!/usr/bin/env node

/**
 * 简易测试脚本 - 验证 Phase 1-2 实现
 *
 * 由于前端项目尚未完全初始化，此脚本用于验证代码结构和类型定义
 */

const fs = require('fs');
const path = require('path');

console.log('🧪 开始验证 Phase 1-2 实现...\n');

// ==================== 测试 1：检查文件是否存在 ====================

const requiredFiles = [
  // 类型定义
  'src/shared/types/models.ts',
  'src/shared/types/api.ts',
  'src/shared/types/websocket.ts',
  'src/shared/types/index.ts',

  // API Client
  'src/core/api/client.ts',
  'src/core/api/groupChatApi.ts',
  'src/core/api/roleApi.ts',
  'src/core/api/index.ts',

  // WebSocket
  'src/core/websocket/WebSocketManager.ts',

  // 其他
  'src/core/index.ts',
  'src/tests/integration.test.ts',
  '.env.development',
  'README.md',
];

console.log('📁 测试 1: 检查文件结构');
let allFilesExist = true;

requiredFiles.forEach((file) => {
  const exists = fs.existsSync(file);
  const status = exists ? '✅' : '❌';
  console.log(`  ${status} ${file}`);
  if (!exists) allFilesExist = false;
});

if (!allFilesExist) {
  console.log('\n❌ 部分文件缺失！');
  process.exit(1);
}

console.log('\n✅ 所有必需文件都已创建\n');

// ==================== 测试 2：检查类型定义 ====================

console.log('📝 测试 2: 检查类型定义');

const modelsContent = fs.readFileSync('src/shared/types/models.ts', 'utf-8');
const apiContent = fs.readFileSync('src/shared/types/api.ts', 'utf-8');
const wsContent = fs.readFileSync('src/shared/types/websocket.ts', 'utf-8');

const requiredTypes = [
  // models.ts
  'AgentPlatform',
  'RoleType',
  'GroupChatType',
  'Message',
  'Role',
  'GroupChat',
  'GroupChatMember',
  'Skill',

  // api.ts
  'CreateGroupChatRequest',
  'SendMessageRequest',
  'CreateRoleRequest',
  'UpdateRoleRequest',

  // websocket.ts
  'RefreshSignal',
  'WebSocketEventType',
  'WebSocketState',
];

let allTypesExist = true;

requiredTypes.forEach((type) => {
  let found = false;

  if (modelsContent.includes(type) ||
      apiContent.includes(type) ||
      wsContent.includes(type)) {
    found = true;
  }

  const status = found ? '✅' : '❌';
  console.log(`  ${status} ${type}`);
  if (!found) allTypesExist = false;
});

if (!allTypesExist) {
  console.log('\n❌ 部分类型定义缺失！');
  process.exit(1);
}

console.log('\n✅ 所有类型定义都已实现\n');

// ==================== 测试 3：检查 API 接口 ====================

console.log('🔌 测试 3: 检查 API 接口');

const groupChatApiContent = fs.readFileSync('src/core/api/groupChatApi.ts', 'utf-8');
const roleApiContent = fs.readFileSync('src/core/api/roleApi.ts', 'utf-8');

const requiredApis = [
  // 群聊 API
  { name: 'createGroupChat', file: 'groupChatApi' },
  { name: 'getGroupChatInfo', file: 'groupChatApi' },
  { name: 'listGroupChats', file: 'groupChatApi' },
  { name: 'getMessages', file: 'groupChatApi' },
  { name: 'getMembers', file: 'groupChatApi' },
  { name: 'sendMessage', file: 'groupChatApi' },
  { name: 'updateMemberDockerMode', file: 'groupChatApi' },
  { name: 'deleteGroupChat', file: 'groupChatApi' },

  // 角色 API
  { name: 'createRole', file: 'roleApi' },
  { name: 'getRoleInfo', file: 'roleApi' },
  { name: 'listRoles', file: 'roleApi' },
  { name: 'updateRole', file: 'roleApi' },
  { name: 'deleteRole', file: 'roleApi' },
  { name: 'getRoleSkills', file: 'roleApi' },
  { name: 'addSkillToRole', file: 'roleApi' },
  { name: 'removeSkillFromRole', file: 'roleApi' },
  { name: 'listAvatars', file: 'roleApi' },
];

let allApisExist = true;

requiredApis.forEach((api) => {
  const content = api.file === 'groupChatApi' ? groupChatApiContent : roleApiContent;
  const found = content.includes(`export async function ${api.name}`);

  const status = found ? '✅' : '❌';
  console.log(`  ${status} ${api.name} (${api.file})`);
  if (!found) allApisExist = false;
});

if (!allApisExist) {
  console.log('\n❌ 部分 API 接口缺失！');
  process.exit(1);
}

console.log('\n✅ 所有 API 接口都已实现\n');

// ==================== 测试 4：检查 WebSocket 功能 ====================

console.log('🔗 测试 4: 检查 WebSocket 功能');

const wsManagerContent = fs.readFileSync('src/core/websocket/WebSocketManager.ts', 'utf-8');

const requiredWsFeatures = [
  'class WebSocketManager',
  'static getInstance',
  'connect',
  'disconnect',
  'send',
  'on(',
  'off(',
  'reconnect',
  'messageQueue',
  'maxReconnectAttempts',
];

let allWsFeaturesExist = true;

requiredWsFeatures.forEach((feature) => {
  const found = wsManagerContent.includes(feature);
  const status = found ? '✅' : '❌';
  console.log(`  ${status} ${feature}`);
  if (!found) allWsFeaturesExist = false;
});

if (!allWsFeaturesExist) {
  console.log('\n❌ 部分 WebSocket 功能缺失！');
  process.exit(1);
}

console.log('\n✅ WebSocket 管理器功能完整\n');

// ==================== 测试 5：检查 Mock 支持 ====================

console.log('🎭 测试 5: 检查 Mock 支持');

const clientContent = fs.readFileSync('src/core/api/client.ts', 'utf-8');

const mockFeatures = [
  'USE_MOCK',
  'mockableRequest',
  'ApiError',
];

let allMockFeaturesExist = true;

mockFeatures.forEach((feature) => {
  const foundInClient = clientContent.includes(feature);
  const foundInGroupChat = groupChatApiContent.includes(feature);
  const foundInRole = roleApiContent.includes(feature);

  const found = foundInClient || foundInGroupChat || foundInRole;
  const status = found ? '✅' : '❌';
  console.log(`  ${status} ${feature}`);
  if (!found) allMockFeaturesExist = false;
});

if (!allMockFeaturesExist) {
  console.log('\n❌ 部分 Mock 功能缺失！');
  process.exit(1);
}

console.log('\n✅ Mock 支持完整\n');

// ==================== 测试 6：检查环境配置 ====================

console.log('⚙️  测试 6: 检查环境配置');

const envContent = fs.readFileSync('.env.development', 'utf-8');

const requiredEnvVars = [
  'VITE_API_BASE_URL',
  'VITE_WS_BASE_URL',
  'VITE_USE_MOCK',
  'VITE_DEBUG',
];

let allEnvVarsExist = true;

requiredEnvVars.forEach((envVar) => {
  const found = envContent.includes(envVar);
  const status = found ? '✅' : '❌';
  console.log(`  ${status} ${envVar}`);
  if (!found) allEnvVarsExist = false;
});

if (!allEnvVarsExist) {
  console.log('\n❌ 部分环境变量缺失！');
  process.exit(1);
}

console.log('\n✅ 环境配置完整\n');

// ==================== 测试 7：代码质量检查 ====================

console.log('🔍 测试 7: 代码质量检查');

let qualityScore = 0;

// 检查是否有注释
const hasComments = modelsContent.includes('/**') &&
                    apiContent.includes('/**') &&
                    clientContent.includes('/**');
console.log(`  ${hasComments ? '✅' : '⚠️ '} 代码注释`);
if (hasComments) qualityScore++;

// 检查是否有类型导出
const hasExports = modelsContent.includes('export') &&
                   apiContent.includes('export') &&
                   wsContent.includes('export');
console.log(`  ${hasExports ? '✅' : '❌'} 类型导出`);
if (hasExports) qualityScore++;

// 检查是否有错误处理
const hasErrorHandling = clientContent.includes('ApiError') &&
                         clientContent.includes('catch');
console.log(`  ${hasErrorHandling ? '✅' : '❌'} 错误处理`);
if (hasErrorHandling) qualityScore++;

// 检查是否有 Mock 数据
const hasMockData = groupChatApiContent.includes('MOCK_') &&
                    roleApiContent.includes('MOCK_');
console.log(`  ${hasMockData ? '✅' : '❌'} Mock 数据`);
if (hasMockData) qualityScore++;

console.log(`\n代码质量得分: ${qualityScore}/4\n`);

// ==================== 总结 ====================

console.log('=' .repeat(50));
console.log('🎉 验证完成！');
console.log('=' .repeat(50));
console.log('');
console.log('✅ 文件结构: 完整');
console.log('✅ 类型定义: 完整 (15+ 类型)');
console.log('✅ API 接口: 完整 (17 个接口)');
console.log('✅ WebSocket: 完整 (单例 + 重连 + 队列)');
console.log('✅ Mock 支持: 完整');
console.log('✅ 环境配置: 完整');
console.log(`✅ 代码质量: ${qualityScore}/4`);
console.log('');
console.log('🚀 Phase 1-2 实现验证通过！');
console.log('');
console.log('下一步:');
console.log('  1. 初始化前端项目 (npm install)');
console.log('  2. 配置 TypeScript 和 Vite');
console.log('  3. 开始开发 UI 组件');
console.log('');
