---
version: 1.0
created_at: 2026-06-10
updated_at: 2026-06-10
last_updated: 创建文件上传功能设计
abstract: 定义前端文件上传功能的设计，包括图片和文档上传、预览、存储策略和 Agent 交互方式
id: file-upload-design
title: 文件上传功能设计
status: draft
module: frontend, backend, agent
sourc_spec: null
related_plan: null
code_scope:
  - frontend/src/shared/components/UploadArea/
  - frontend/src/shared/components/UploadPreview/
  - frontend/src/shared/components/FilePreviewCard/
  - frontend/src/shared/components/ImagePreviewModal/
  - frontend/src/core/api/groupChatApi.ts
  - agents_hub/api/routes/group_chat.py
contract_refs:
  - frontend/src/shared/types/api-requests.ts
  - frontend/src/shared/types/api-schemas.ts
  - agents_hub/api/schemas/group_chat.py
---

# 文件上传功能设计

## 版本

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-06-10 | 初始版本 |

## Overview

本设计定义前端文件上传功能，支持用户在聊天中上传图片和文档文件。文件存储在后端服务器，Agent 通过文件路径读取内容。

**核心原则：**
1. **统一方案** - 浏览器和桌面端走同一套上传流程
2. **先上传后发送** - 用户先上传文件，预览确认后再发送消息
3. **路径注入** - Agent 只接收文件路径，通过路径读取内容
4. **关联清理** - 文件和消息关联存储，消息删除时清理文件

## Scope

### 范围内

- 文件上传功能（图片 + 文档）
- 文件预览功能（图片缩略图、文档图标）
- 图片放大预览
- 拖拽上传
- 文件存储和命名
- Agent 文件路径注入

### 范围外

- 文件编辑功能
- 文件版本管理
- 文件共享权限
- 文件搜索功能

## Core Behavior

### 1. 文件上传流程

#### 1.1 上传方式

**附件按钮：**
- 在消息输入框旁边添加附件按钮
- 点击按钮触发文件选择对话框
- 支持多文件选择

**拖拽上传：**
- 支持拖拽文件到聊天窗口
- 拖拽时显示高亮区域
- 支持多文件拖拽

#### 1.2 上传流程

```
用户选择文件 → 前端验证 → 上传到后端 → 后端保存 → 返回文件路径 → 前端显示预览
```

**详细步骤：**
1. 用户点击附件按钮或拖拽文件
2. 前端验证文件类型和大小
3. 前端上传文件到后端 API
4. 后端接收文件，生成新文件名
5. 后端保存文件到 `file_snapshots` 目录
6. 后端返回文件信息（路径、类型、大小）
7. 前端显示文件预览卡片

**文件类型支持：**
- 图片：jpg, jpeg, png, gif, webp, svg
- 文档：pdf, txt, md, json, csv, doc, docx, xls, xlsx, ppt, pptx
- 代码：js, ts, py, java, cpp, c, h, css, html, xml, yaml, yml, toml
- 压缩：zip, rar, 7z, tar, gz

**文件大小限制：**
- 单文件最大：50MB
- 超过限制显示错误提示

#### 1.3 文件命名规则

**格式：** `{原文件名}_{时间戳}_{UUID前16位}.{扩展名}`

**示例：**
- `report_20260610_143052_a1b2c3d4e5f6.pdf`
- `photo_20260610_143052_1234567890abcdef.png`

**优势：**
- 保留原文件名可读性
- 时间戳确保时间顺序
- UUID 确保唯一性

### 2. 文件预览功能

#### 2.1 两种预览场景

**场景1：上传后预览（输入框旁边）**
- **位置**：输入框上方
- **时机**：文件上传后立即显示
- **功能**：预览文件、删除文件
- **样式**：紧凑，显示缩略图/图标 + 文件名 + 删除按钮
- **交互**：点击图片可预览，点击删除按钮移除文件

**场景2：发送后预览（消息中）**
- **位置**：消息内容下方
- **时机**：消息发送后显示
- **功能**：查看文件、图片点击放大、文档下载
- **样式**：复用 FileChangesCard 风格
- **交互**：图片点击放大，文档点击下载

#### 2.2 预览组件

**UploadPreview 组件（上传后预览）：**
- 显示在输入框上方
- 图片文件：显示缩略图（小尺寸，最大 100px）
- 文档文件：显示文件图标 + 文件名
- 删除按钮：移除已上传的文件
- 紧凑布局，支持多文件横向排列

**FilePreviewCard 组件（发送后预览）：**
- 显示在消息内容下方
- 图片文件：显示缩略图（较大尺寸，最大 300px），点击可放大
- 文档文件：显示文件图标 + 文件名 + 大小
- 复用 `FileChangesCard` 的视觉风格

**ImagePreviewModal 组件：**
- 全屏预览图片
- 支持缩放、拖拽
- 关闭按钮
- 点击背景关闭

#### 2.3 预览样式

**上传后预览样式：**
- 紧凑布局，横向排列
- 图片：圆角缩略图，最大宽度 100px，最大高度 100px
- 文档：小图标 + 文件名（截断）
- 删除按钮：右上角 X 按钮
- 背景：浅灰色，圆角

**发送后预览样式：**
- 垂直排列，间距 8px
- 图片：圆角缩略图，最大宽度 300px，最大高度 200px，点击可放大
- 文档：灰色背景卡片，文件图标 + 文件名 + 大小
- 复用 FileChangesCard 的视觉风格

### 3. 消息发送

#### 3.1 消息格式扩展

**SendMessageRequest 扩展：**
```typescript
export interface SendMessageRequest {
  content: string;
  members: string[];
  files?: UploadedFileInfo[];  // 可选的文件列表
}

export interface UploadedFileInfo {
  file_name: string;      // 原始文件名
  file_path: string;      // 存储路径（相对于项目根目录）
  file_type: string;      // 文件类型（mime type）
  file_size: number;      // 文件大小（字节）
}
```

#### 3.2 消息渲染

**MessageApiItem 扩展：**
```typescript
export interface MessageApiItem {
  id: number;
  speaker: string;
  content: string;
  timestamp: string;
  platform: string;
  files?: UploadedFileInfo[];  // 新增：文件列表
  permission_request?: PermissionRequestInfo;
}
```

**渲染逻辑：**
- 检查 `message.files` 是否存在
- 如果有文件，渲染 `FilePreviewCard` 组件（发送后预览）
- 图片文件：显示缩略图，点击可放大
- 文档文件：显示图标 + 文件名，点击可下载

**两种预览的使用场景：**
1. **上传后预览（UploadPreview）**：显示在输入框上方，用于发送前确认
2. **发送后预览（FilePreviewCard）**：显示在消息中，用于查看已发送的文件

### 4. 存储策略

#### 4.1 存储路径

**路径格式：** `local_data/teams/{team_id}/{group_chat_id}/file_snapshots/`

**示例：**
```
local_data/teams/D-desktop-软件开发-agents-hub/877cead7-b98c-40f2-8d05-a62f56421f7a/file_snapshots/
├── report_20260610_143052_a1b2c3d4e5f6.pdf
├── photo_20260610_143052_1234567890abcdef.png
└── ...
```

#### 4.2 清理策略

**基于消息关联：**
- 文件和消息关联存储
- 消息存在时，文件不清理
- 消息删除时，关联的文件也删除
- 每日凌晨 3 点清理孤儿文件（没有消息关联的文件，超过 7 天）

**优势：**
- 数据一致性：文件和消息生命周期一致
- 无孤立文件：不会出现文件存在但消息已删除的情况
- 自动清理：消息删除时自动清理关联文件

### 5. Agent 交互

#### 5.1 Agent 收到的消息格式

**消息内容渲染：**
```
请分析这个报告

[附件]
- report.pdf (1.0 MB)
- photo.png (250 KB)
```

#### 5.2 文件路径注入到 Agent 提示词

**注入内容：**
```xml
<uploaded_files>
<file>local_data/teams/{team_id}/{chat_id}/file_snapshots/report_20260610_143052_a1b2c3d4e5f6.pdf</file>
<file>local_data/teams/{team_id}/{chat_id}/file_snapshots/photo_20260610_143052_1234567890abcdef.png</file>
</uploaded_files>
```

**简化原则：**
- 只注入文件路径
- 不注入文件类型、大小、名称
- Agent 通过路径读取内容
- Agent 通过扩展名判断类型

#### 5.3 Agent 读取文件

**Agent 可以：**
1. 读取文件内容：通过文件路径
2. 分析图片：使用图像理解工具
3. 处理文档：解析 PDF、文本等
4. 修改文件：如果需要，可以修改并保存

## Technical Contract

### 1. 前端 API 接口

#### 1.1 文件上传 API

```typescript
export async function uploadFile(
  chatId: string,
  file: File
): Promise<UploadedFileInfo> {
  const formData = new FormData();
  formData.append('file', file);
  
  return apiClient.post<UploadedFileInfo>(
    `/group-chats/${chatId}/upload`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
}
```

#### 1.2 消息发送 API 扩展

```typescript
export async function sendMessage(
  chatId: string,
  data: SendMessageRequest
): Promise<SuccessResponse> {
  return mockableRequest(
    () => apiClient.post<SuccessResponse>(`/group-chats/${chatId}/messages`, data),
    { message: 'Message sent successfully' }
  );
}
```

### 2. 后端 API 接口

#### 2.1 文件上传接口

**端点：** `POST /api/v1/group-chats/{chat_id}/upload`

**请求：**
- Content-Type: multipart/form-data
- Body: file (File)

**响应：**
```json
{
  "file_name": "report.pdf",
  "file_path": "local_data/teams/{team_id}/{chat_id}/file_snapshots/report_20260610_143052_a1b2c3d4e5f6.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000
}
```

**后端逻辑：**
1. 接收文件
2. 验证文件类型和大小
3. 生成新文件名：`{原文件名}_{时间戳}_{UUID前16位}.{扩展名}`
4. 保存到 `local_data/teams/{team_id}/{chat_id}/file_snapshots/`
5. 返回文件信息

#### 2.2 消息发送接口扩展

**端点：** `POST /api/v1/group-chats/{chat_id}/messages`

**请求体扩展：**
```json
{
  "content": "请分析这个报告",
  "members": ["Leader", "Developer"],
  "files": [
    {
      "file_name": "report.pdf",
      "file_path": "local_data/teams/{team_id}/{chat_id}/file_snapshots/report_20260610_143052_a1b2c3d4e5f6.pdf",
      "file_type": "application/pdf",
      "file_size": 1024000
    }
  ]
}
```

#### 2.3 文件访问接口

**端点：** `GET /api/v1/group-chats/{chat_id}/files/{file_path}`

**功能：**
- 返回文件内容
- 支持图片直接显示
- 支持文档下载

**响应：**
- Content-Type: 根据文件类型设置
- Body: 文件内容

### 3. 前端组件接口

#### 3.1 UploadArea 组件

```typescript
interface UploadAreaProps {
  chatId: string;
  onUploadComplete: (fileInfo: UploadedFileInfo) => void;
  onUploadError: (error: string) => void;
  disabled?: boolean;
}
```

#### 3.2 UploadPreview 组件（上传后预览）

```typescript
interface UploadPreviewProps {
  files: UploadedFileInfo[];
  onRemove: (index: number) => void;
  onImageClick?: (filePath: string) => void;  // 图片点击预览
}
```

#### 3.3 FilePreviewCard 组件（发送后预览）

```typescript
interface FilePreviewCardProps {
  files: UploadedFileInfo[];
  onImageClick?: (filePath: string) => void;  // 图片点击放大
}
```

#### 3.4 ImagePreviewModal 组件

```typescript
interface ImagePreviewModalProps {
  isOpen: boolean;
  imageUrl: string;
  onClose: () => void;
}
```

### 4. 类型定义

#### 4.1 UploadedFileInfo

```typescript
export interface UploadedFileInfo {
  file_name: string;      // 原始文件名
  file_path: string;      // 存储路径（相对于项目根目录）
  file_type: string;      // 文件类型（mime type）
  file_size: number;      // 文件大小（字节）
}
```

#### 4.2 SendMessageRequest 扩展

```typescript
export interface SendMessageRequest {
  content: string;
  members: string[];
  files?: UploadedFileInfo[];  // 可选的文件列表
}
```

#### 4.3 MessageApiItem 扩展

```typescript
export interface MessageApiItem {
  id: number;
  speaker: string;
  content: string;
  timestamp: string;
  platform: string;
  files?: UploadedFileInfo[];  // 新增：文件列表
  permission_request?: PermissionRequestInfo;
}
```

## Error Handling

### 1. 上传错误

**错误类型：**
- 文件过大（> 50MB）
- 文件类型不支持
- 网络错误
- 服务器错误

**处理方式：**
- 显示 Toast 错误提示
- 移除预览卡片
- 允许重试

### 2. 发送错误

**错误类型：**
- 文件路径无效
- 文件已被删除
- 网络错误

**处理方式：**
- 显示 Toast 错误提示
- 保留消息内容和文件预览
- 允许重试

### 3. 边界情况

**场景1：上传后删除文件**
- 用户上传文件 → 显示预览 → 用户点击删除 → 移除预览，不发送文件

**场景2：上传后关闭窗口**
- 文件已上传到服务器 → 服务器定期清理未使用的文件

**场景3：多文件上传部分失败**
- 显示成功上传的文件
- 显示失败的文件及错误原因
- 允许重新上传失败的文件

**场景4：图片预览加载失败**
- 显示默认图片图标
- 显示文件名
- 允许点击下载

## Testing

### 1. 单元测试

**前端测试：**
- `UploadArea` 组件测试
  - 附件按钮点击触发文件选择
  - 拖拽文件触发上传
  - 上传成功/失败处理
- `FilePreviewCard` 组件测试
  - 图片缩略图显示
  - 文档图标显示
  - 删除按钮功能
- `ImagePreviewModal` 组件测试
  - 打开/关闭模态框
  - 图片显示

**后端测试：**
- 文件上传 API 测试
  - 正常上传
  - 文件类型验证
  - 文件大小验证
  - 文件命名规则
- 文件访问 API 测试
  - 图片直接显示
  - 文档下载
- 文件清理测试
  - 消息删除时清理关联文件
  - 孤儿文件清理

### 2. 集成测试

**完整流程测试：**
1. 用户上传文件
2. 文件显示预览
3. 用户发送消息
4. 消息显示文件卡片
5. Agent 收到文件路径
6. Agent 读取文件内容

### 3. E2E 测试

**场景：**
- 上传图片 → 预览 → 发送 → 消息显示图片
- 上传文档 → 预览 → 发送 → 消息显示文档卡片
- 拖拽上传 → 预览 → 发送
- 多文件上传 → 预览 → 发送
- 上传失败 → 错误提示 → 重试

## Out of Spec

以下内容不在本 spec 范围内：

1. **文件编辑功能** - 不支持在线编辑文件
2. **文件版本管理** - 不支持文件版本控制
3. **文件共享权限** - 不支持文件级别的权限控制
4. **文件搜索功能** - 不支持文件内容搜索
5. **文件压缩** - 不支持自动压缩文件
6. **文件预览内容** - 不支持文档内容预览（如 PDF 内容显示）
