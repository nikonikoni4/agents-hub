#!/usr/bin/env node

/**
 * 前端静态检查验证脚本
 *
 * 用法：node frontend/verify-setup.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const REQUIRED_FILES = [
  'package.json',
  'tsconfig.json',
  'eslint.config.js',
  '.prettierrc.json',
  'vite.config.ts',
  'vitest.config.ts',
  '.gitignore',
];

const REQUIRED_SCRIPTS = [
  'lint',
  'type-check',
  'format:check',
  'test',
  'ci',
];

console.log('🔍 验证前端静态检查配置...\n');

let success = true;

// 检查配置文件
console.log('📁 检查配置文件：');
REQUIRED_FILES.forEach((file) => {
  const filePath = path.join(__dirname, file);
  const exists = fs.existsSync(filePath);
  console.log(`  ${exists ? '✅' : '❌'} ${file}`);
  if (!exists) success = false;
});

// 检查 package.json scripts
console.log('\n📜 检查 package.json scripts：');
const packageJson = JSON.parse(fs.readFileSync(path.join(__dirname, 'package.json'), 'utf8'));
REQUIRED_SCRIPTS.forEach((script) => {
  const exists = packageJson.scripts && packageJson.scripts[script];
  console.log(`  ${exists ? '✅' : '❌'} npm run ${script}`);
  if (!exists) success = false;
});

// 检查源代码目录
console.log('\n📂 检查源代码目录：');
const srcExists = fs.existsSync(path.join(__dirname, 'src'));
console.log(`  ${srcExists ? '✅' : '❌'} src/`);
if (!srcExists) success = false;

console.log('\n' + '='.repeat(50));
if (success) {
  console.log('✅ 所有配置检查通过！');
  console.log('\n📋 下一步：');
  console.log('  1. 安装依赖: cd frontend && npm install');
  console.log('  2. 类型检查: npm run type-check');
  console.log('  3. 代码检查: npm run lint');
  console.log('  4. 格式检查: npm run format:check');
  console.log('  5. 运行测试: npm run test');
  console.log('  6. 完整 CI: npm run ci');
} else {
  console.log('❌ 配置检查失败，请检查缺失的文件');
  process.exit(1);
}
