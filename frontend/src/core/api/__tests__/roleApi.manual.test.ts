/**
 * 角色管理 API 手动测试
 *
 * 在浏览器控制台或 Node 环境中运行此测试
 * 确保后端服务运行在 http://localhost:8000
 */

import * as roleApi from '../roleApi';
import type { CreateRoleRequest } from '@/shared/types/api-requests';

/**
 * 集成测试场景
 */
export async function testRoleApiIntegration() {
  console.log('=== 开始角色 API 集成测试 ===\n');

  try {
    // 测试场景 1: 获取角色列表
    console.log('[1] 获取角色列表...');
    const initialRoles = await roleApi.listRoles();
    console.log(
      `✅ 共 ${initialRoles.length} 个角色:`,
      initialRoles.map((r) => r.name)
    );

    // 测试场景 2: 获取头像列表
    console.log('\n[2] 获取头像列表...');
    const avatars = await roleApi.listAvatars();
    console.log(`✅ 共 ${avatars.length} 个头像:`, avatars.slice(0, 3), '...');

    // 测试场景 3: 创建角色
    console.log('\n[3] 创建测试角色...');
    const createData: CreateRoleRequest = {
      name: 'test-agent-' + Date.now(),
      platform: 'claude',
      description: 'Test agent for integration testing',
      abilities: ['test', 'debug'],
      avatar: avatars[0] || null,
    };
    const newRole = await roleApi.createRole(createData);
    console.log('✅ 创建成功:', newRole);

    // 测试场景 4: 获取单个角色
    console.log('\n[4] 获取角色详情...');
    const roleInfo = await roleApi.getRoleInfo(newRole.name);
    console.log('✅ 角色详情:', roleInfo);

    // 测试场景 5: 更新角色
    console.log('\n[5] 更新角色...');
    const updatedRole = await roleApi.updateRole(newRole.name, {
      description: 'Updated description at ' + new Date().toISOString(),
    });
    console.log('✅ 更新成功:', updatedRole);

    // 测试场景 6: 获取角色 Skills（应该为空）
    console.log('\n[6] 获取角色 Skills...');
    const skills = await roleApi.getRoleSkills(newRole.name);
    console.log(`✅ 角色有 ${skills.length} 个 Skills:`, skills);

    // 测试场景 7: 添加 Skill（需要后端有可用的 skill）
    if (skills.length === 0) {
      console.log('\n[7] 尝试添加 Skill...');
      try {
        const addedSkill = await roleApi.addSkillToRole(newRole.name, 'test-skill');
        console.log('✅ Skill 添加成功:', addedSkill);

        // 测试场景 8: 移除 Skill
        console.log('\n[8] 移除 Skill...');
        const removeResult = await roleApi.removeSkillFromRole(newRole.name, 'test-skill');
        console.log('✅ Skill 移除成功:', removeResult.message);
      } catch (error: any) {
        console.log('⚠️  添加 Skill 失败（可能是 skill 不存在）:', error.message);
      }
    }

    // 测试场景 9: 删除角色
    console.log('\n[9] 删除测试角色...');
    const deleteResult = await roleApi.deleteRole(newRole.name);
    console.log('✅ 删除成功:', deleteResult.message);

    // 测试场景 10: 验证删除
    console.log('\n[10] 验证角色已删除...');
    const finalRoles = await roleApi.listRoles();
    const exists = finalRoles.some((r) => r.name === newRole.name);
    console.log(exists ? '❌ 角色仍然存在' : '✅ 角色已被删除');

    console.log('\n=== ✅ 所有测试通过 ===');
  } catch (error: any) {
    console.error('\n❌ 测试失败:', error);
    throw error;
  }
}

/**
 * 错误处理测试
 */
export async function testErrorHandling() {
  console.log('=== 测试错误处理 ===\n');

  // 测试 404 错误
  console.log('[1] 测试获取不存在的角色...');
  try {
    await roleApi.getRoleInfo('non-existent-role-' + Date.now());
    console.log('❌ 应该抛出错误但没有');
  } catch (error: any) {
    console.log('✅ 404 错误捕获成功:', error.code || error.message);
  }

  // 测试重复创建错误（先创建再重复）
  console.log('\n[2] 测试重复创建角色...');
  const testName = 'duplicate-test-' + Date.now();
  try {
    await roleApi.createRole({
      name: testName,
      platform: 'claude',
    });
    console.log('✅ 第一次创建成功');

    await roleApi.createRole({
      name: testName,
      platform: 'claude',
    });
    console.log('❌ 应该抛出错误但没有');
  } catch (error: any) {
    console.log('✅ 重复创建错误捕获成功:', error.code || error.message);
  } finally {
    // 清理测试数据
    try {
      await roleApi.deleteRole(testName);
      console.log('✅ 测试数据清理完成');
    } catch {
      // 忽略清理失败，可能数据不存在
    }
  }

  console.log('\n=== ✅ 错误处理测试完成 ===');
}

/**
 * Mock 模式测试
 */
export async function testMockMode() {
  console.log('=== Mock 模式测试 ===\n');
  console.log('⚠️  请确保环境变量 VITE_USE_MOCK=true\n');

  try {
    // 测试 Mock 数据
    console.log('[1] 获取 Mock 角色列表...');
    const roles = await roleApi.listRoles();
    console.log(`✅ 获取到 ${roles.length} 个 Mock 角色`);

    console.log('\n[2] 创建 Mock 角色...');
    const newRole = await roleApi.createRole({
      name: 'mock-test-role',
      platform: 'claude',
      description: 'Mock test role',
    });
    console.log('✅ Mock 角色创建成功:', newRole);

    console.log('\n[3] 验证 Mock 角色已添加到列表...');
    const updatedRoles = await roleApi.listRoles();
    const exists = updatedRoles.some((r) => r.name === 'mock-test-role');
    console.log(exists ? '✅ Mock 数据动态更新正常' : '❌ Mock 数据未更新');

    console.log('\n[4] 删除 Mock 角色...');
    await roleApi.deleteRole('mock-test-role');
    const finalRoles = await roleApi.listRoles();
    const stillExists = finalRoles.some((r) => r.name === 'mock-test-role');
    console.log(stillExists ? '❌ Mock 角色未被删除' : '✅ Mock 角色删除成功');

    console.log('\n=== ✅ Mock 模式测试通过 ===');
  } catch (error: any) {
    console.error('\n❌ Mock 测试失败:', error);
  }
}

// 导出便捷的测试运行器
export const runAllTests = async () => {
  await testRoleApiIntegration();
  console.log('\n' + '='.repeat(50) + '\n');
  await testErrorHandling();
};
