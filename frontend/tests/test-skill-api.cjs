#!/usr/bin/env node

/**
 * Skill API 实现验证脚本
 *
 * 验证 Skill 数据模型和 API 接口的完整性
 */

const fs = require('fs');
const path = require('path');

const baseDir = path.join(__dirname, 'src');

// 颜色输出
const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

let totalScore = 0;
let maxScore = 0;

// ==================== 1. 检查文件结构 ====================

function checkFileStructure() {
  log('\n📁 检查文件结构...', 'blue');
  maxScore += 3;

  const requiredFiles = [
    'shared/types/models.ts',
    'core/api/skillApi.ts',
    'tests/skillApi.test.ts',
  ];

  let fileCount = 0;
  requiredFiles.forEach(file => {
    const filePath = path.join(baseDir, file);
    if (fs.existsSync(filePath)) {
      log(`  ✓ ${file}`, 'green');
      fileCount++;
    } else {
      log(`  ✗ ${file} 缺失`, 'red');
    }
  });

  totalScore += fileCount;
  log(`  文件结构: ${fileCount}/${requiredFiles.length}`, fileCount === requiredFiles.length ? 'green' : 'yellow');
}

// ==================== 2. 检查类型定义 ====================

function checkTypeDefinitions() {
  log('\n📝 检查类型定义...', 'blue');
  maxScore += 2;

  const modelsPath = path.join(baseDir, 'shared/types/models.ts');

  if (!fs.existsSync(modelsPath)) {
    log('  ✗ models.ts 不存在', 'red');
    return;
  }

  const content = fs.readFileSync(modelsPath, 'utf-8');

  const requiredTypes = [
    { name: 'Skill', pattern: /export interface Skill\s*\{[\s\S]*?name:\s*string[\s\S]*?description:\s*string[\s\S]*?\}/ },
    { name: 'RoleSkill', pattern: /export interface RoleSkill\s*\{[\s\S]*?id:\s*string[\s\S]*?name:\s*string[\s\S]*?description:\s*string[\s\S]*?\}/ },
  ];

  let typeCount = 0;
  requiredTypes.forEach(type => {
    if (type.pattern.test(content)) {
      log(`  ✓ ${type.name} 类型定义正确`, 'green');
      typeCount++;
    } else {
      log(`  ✗ ${type.name} 类型定义缺失或不正确`, 'red');
    }
  });

  totalScore += typeCount;
  log(`  类型定义: ${typeCount}/${requiredTypes.length}`, typeCount === requiredTypes.length ? 'green' : 'yellow');
}

// ==================== 3. 检查 API 接口 ====================

function checkApiInterfaces() {
  log('\n🔌 检查 API 接口...', 'blue');
  maxScore += 4;

  const apiPath = path.join(baseDir, 'core/api/skillApi.ts');

  if (!fs.existsSync(apiPath)) {
    log('  ✗ skillApi.ts 不存在', 'red');
    return;
  }

  const content = fs.readFileSync(apiPath, 'utf-8');

  const requiredFunctions = [
    'listSkills',
    'getSkill',
    'deleteSkill',
    'addSkill',
  ];

  let functionCount = 0;
  requiredFunctions.forEach(func => {
    const pattern = new RegExp(`export\\s+async\\s+function\\s+${func}`);
    if (pattern.test(content)) {
      log(`  ✓ ${func} 函数存在`, 'green');
      functionCount++;
    } else {
      log(`  ✗ ${func} 函数缺失`, 'red');
    }
  });

  totalScore += functionCount;
  log(`  API 接口: ${functionCount}/${requiredFunctions.length}`, functionCount === requiredFunctions.length ? 'green' : 'yellow');
}

// ==================== 4. 检查 Mock 数据支持 ====================

function checkMockSupport() {
  log('\n🎭 检查 Mock 数据支持...', 'blue');
  maxScore += 3;

  const apiPath = path.join(baseDir, 'core/api/skillApi.ts');

  if (!fs.existsSync(apiPath)) {
    log('  ✗ skillApi.ts 不存在', 'red');
    return;
  }

  const content = fs.readFileSync(apiPath, 'utf-8');

  const checks = [
    { name: 'MOCK_SKILLS 常量', pattern: /const\s+MOCK_SKILLS\s*[:=]/ },
    { name: 'MOCK_SKILL 常量', pattern: /const\s+MOCK_SKILL\s*[:=]/ },
    { name: 'mockableRequest 使用', pattern: /mockableRequest\s*\(/ },
  ];

  let mockCount = 0;
  checks.forEach(check => {
    if (check.pattern.test(content)) {
      log(`  ✓ ${check.name}`, 'green');
      mockCount++;
    } else {
      log(`  ✗ ${check.name} 缺失`, 'red');
    }
  });

  totalScore += mockCount;
  log(`  Mock 支持: ${mockCount}/${checks.length}`, mockCount === checks.length ? 'green' : 'yellow');
}

// ==================== 5. 检查导出 ====================

function checkExports() {
  log('\n📤 检查导出...', 'blue');
  maxScore += 2;

  const indexPath = path.join(baseDir, 'core/api/index.ts');

  if (!fs.existsSync(indexPath)) {
    log('  ✗ core/api/index.ts 不存在', 'red');
    return;
  }

  const content = fs.readFileSync(indexPath, 'utf-8');

  const checks = [
    { name: 'skillApi 导出', pattern: /from\s+['"]\.\/skillApi['"]/ },
    { name: 'listSkills 导出', pattern: /listSkills/ },
  ];

  let exportCount = 0;
  checks.forEach(check => {
    if (check.pattern.test(content)) {
      log(`  ✓ ${check.name}`, 'green');
      exportCount++;
    } else {
      log(`  ✗ ${check.name} 缺失`, 'red');
    }
  });

  totalScore += exportCount;
  log(`  导出检查: ${exportCount}/${checks.length}`, exportCount === checks.length ? 'green' : 'yellow');
}

// ==================== 6. 检查测试文件 ====================

function checkTestFile() {
  log('\n🧪 检查测试文件...', 'blue');
  maxScore += 2;

  const testPath = path.join(baseDir, 'tests/skillApi.test.ts');

  if (!fs.existsSync(testPath)) {
    log('  ✗ skillApi.test.ts 不存在', 'red');
    return;
  }

  const content = fs.readFileSync(testPath, 'utf-8');

  const checks = [
    { name: 'testListSkills 测试', pattern: /export\s+async\s+function\s+testListSkills/ },
    { name: 'runSkillApiTests 测试套件', pattern: /export\s+async\s+function\s+runSkillApiTests/ },
  ];

  let testCount = 0;
  checks.forEach(check => {
    if (check.pattern.test(content)) {
      log(`  ✓ ${check.name}`, 'green');
      testCount++;
    } else {
      log(`  ✗ ${check.name} 缺失`, 'red');
    }
  });

  totalScore += testCount;
  log(`  测试文件: ${testCount}/${checks.length}`, testCount === checks.length ? 'green' : 'yellow');
}

// ==================== 7. 检查文档 ====================

function checkDocumentation() {
  log('\n📚 检查文档...', 'blue');
  maxScore += 1;

  const readmePath = path.join(__dirname, 'README.md');

  if (!fs.existsSync(readmePath)) {
    log('  ✗ README.md 不存在', 'red');
    return;
  }

  const content = fs.readFileSync(readmePath, 'utf-8');

  if (content.includes('Skill 管理 API') && content.includes('listSkills')) {
    log('  ✓ README 包含 Skill API 文档', 'green');
    totalScore += 1;
  } else {
    log('  ✗ README 缺少 Skill API 文档', 'red');
  }
}

// ==================== 运行所有检查 ====================

function main() {
  log('='.repeat(60), 'blue');
  log('  Skill API 实现验证', 'blue');
  log('='.repeat(60), 'blue');

  checkFileStructure();
  checkTypeDefinitions();
  checkApiInterfaces();
  checkMockSupport();
  checkExports();
  checkTestFile();
  checkDocumentation();

  // 总结
  log('\n' + '='.repeat(60), 'blue');
  const percentage = Math.round((totalScore / maxScore) * 100);
  const color = percentage === 100 ? 'green' : percentage >= 80 ? 'yellow' : 'red';
  log(`  总分: ${totalScore}/${maxScore} (${percentage}%)`, color);

  if (percentage === 100) {
    log('\n🚀 Skill API 实现验证通过！', 'green');
  } else if (percentage >= 80) {
    log('\n⚠️  Skill API 基本完成，但有部分内容缺失', 'yellow');
  } else {
    log('\n❌ Skill API 实现不完整，请检查上述错误', 'red');
  }

  log('='.repeat(60), 'blue');
}

main();
