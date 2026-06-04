/**
 * Skill API 集成测试
 *
 * 验证 Skill API 接口的调用和 Mock 数据支持
 */

import { listSkills, getSkill, deleteSkill, addSkill, USE_MOCK } from '@/core/api';

// ==================== 测试场景 1：列出所有 skills ====================

export async function testListSkills() {
  console.log('\n=== 测试列出所有 skills ===');
  console.log('Mock 模式:', USE_MOCK ? '开启' : '关闭');

  try {
    const skills = await listSkills();
    console.log(`✓ 获取到 ${skills.length} 个 skills`);
    console.log('Skills:', skills);

    // 验证数据结构
    if (skills.length > 0) {
      const firstSkill = skills[0]!;
      if (firstSkill.name && firstSkill.description) {
        console.log('✓ Skill 数据结构正确');
      } else {
        console.error('✗ Skill 数据结构错误:', firstSkill);
      }
    }
  } catch (error) {
    console.error('❌ 列出 skills 失败:', error);
  }
}

// ==================== 测试场景 2：获取单个 skill ====================

export async function testGetSkill() {
  console.log('\n=== 测试获取单个 skill ===');

  try {
    const skillName = 'code-review';
    const skill = await getSkill(skillName);
    console.log(`✓ 获取 skill '${skillName}' 成功`);
    console.log('Skill 详情:', skill);

    // 验证数据
    if (skill.name === skillName) {
      console.log('✓ Skill 名称匹配');
    } else {
      console.error('✗ Skill 名称不匹配:', skill.name, '!=', skillName);
    }
  } catch (error) {
    console.error('❌ 获取 skill 失败:', error);
  }
}

// ==================== 测试场景 3：删除 skill ====================

export async function testDeleteSkill() {
  console.log('\n=== 测试删除 skill ===');

  try {
    const skillName = 'test-skill';
    const result = await deleteSkill(skillName);
    console.log(`✓ 删除 skill '${skillName}' 成功`);
    console.log('删除结果:', result);

    // 验证消息
    if (result.message.includes(skillName)) {
      console.log('✓ 删除消息正确');
    } else {
      console.error('✗ 删除消息不包含 skill 名称:', result.message);
    }
  } catch (error) {
    console.error('❌ 删除 skill 失败:', error);
  }
}

// ==================== 测试场景 4：添加 skill ====================

export async function testAddSkill() {
  console.log('\n=== 测试添加 skill（预留接口）===');

  try {
    const newSkill = await addSkill({
      url: 'https://example.com/skill.zip',
    });
    console.log('✓ 添加 skill 成功');
    console.log('新 Skill:', newSkill);

    // 验证返回数据
    if (newSkill.name && newSkill.description) {
      console.log('✓ 返回数据结构正确');
    } else {
      console.error('✗ 返回数据结构错误:', newSkill);
    }
  } catch (error) {
    console.error('❌ 添加 skill 失败:', error);
    console.log('注意：此接口为预留功能，后端可能返回 500 错误');
  }
}

// ==================== 运行所有测试 ====================

export async function runSkillApiTests() {
  console.log('🚀 开始 Skill API 测试\n');
  console.log('当前环境:', import.meta.env.MODE);
  console.log('API Base URL:', import.meta.env.VITE_API_BASE_URL);
  console.log('Mock 模式:', USE_MOCK ? '开启' : '关闭');

  // 测试 1: 列出所有 skills
  await testListSkills();

  // 等待 1 秒
  await new Promise((resolve) => setTimeout(resolve, 1000));

  // 测试 2: 获取单个 skill
  await testGetSkill();

  // 等待 1 秒
  await new Promise((resolve) => setTimeout(resolve, 1000));

  // 测试 3: 删除 skill
  await testDeleteSkill();

  // 等待 1 秒
  await new Promise((resolve) => setTimeout(resolve, 1000));

  // 测试 4: 添加 skill
  await testAddSkill();

  console.log('\n🎉 Skill API 测试完成');
}

// ==================== 使用说明 ====================

/**
 * 在浏览器控制台中运行：
 *
 * // 导入测试函数
 * import { runSkillApiTests, testListSkills, testGetSkill } from '@/tests/skillApi.test';
 *
 * // 运行所有测试
 * runSkillApiTests();
 *
 * // 或单独运行某个测试
 * testListSkills();
 * testGetSkill();
 */
