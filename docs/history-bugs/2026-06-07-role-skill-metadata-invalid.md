# 角色添加 Skill 后报元数据无效

- 发现时间：2026-06-07
- 影响范围：前端角色编辑面板添加 Skill 后无法显示，后端返回 SKILL_METADATA_INVALID 错误
- 状态：已修复

## 问题描述

前端角色编辑面板添加 Skill 后出现三个问题：
1. Skill 没有被选中的效果
2. 添加 Skill 后角色卡片不显示已加载的 Skill
3. 前端控制台报错 ApiError: Skill 'grill-with-docs' 已添加但元数据无效

但 Skill 文件确实被复制到了角色的 work_root/skills/ 目录中。

## 根因

后端 Role.list_skills() 查找 skill.json 文件，但所有 Skill 实际使用 SKILL.md（YAML frontmatter）格式。add_skill() 成功创建了目录副本，但 list_skills() 因找不到 skill.json 而跳过该 Skill，导致 add_role_skill() 服务方法抛出 ValidationError。

前端 useRoleSkills hook 调用 getRoleInfo() 获取技能列表，但后端 GET /roles/{name} 的 RoleResponse 不包含 skills 字段（已修复为包含）。

## 解决方案

### 后端修改

1. agents_hub/roles/role.py：list_skills() 改为解析 SKILL.md 的 YAML frontmatter，新增 import yaml
2. agents_hub/api/schemas/roles.py：RoleResponse 新增 skills 字段，from_domain() 接受可选的 skills 参数
3. agents_hub/api/services/role_service.py：get_role()、list_roles()、update_role() 返回 (RoleInfo, list[SkillInfo]) 元组
4. agents_hub/api/routes/roles.py：路由适配新返回类型，将 skills 传递给 from_domain()

### 前端修改

1. frontend/src/features/roles/hooks/useRoleSkills.ts：移除不存在的 updateRoleInStore 调用，简化为直接用 getRoleInfo() 读取 role.skills

## 注意事项

- SKILL.md 格式：---
name: xxx
description: xxx
---
内容
- Skill 的 id 字段使用目录名（如 grill-with-docs），name 从 frontmatter 读取
- RoleResponse 现在默认包含 skills 字段（空数组），前端类型已对齐
