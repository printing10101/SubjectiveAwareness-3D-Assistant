#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Files to fix
const filesToFix = [
  'src/components/ui/AnimatedNumber.vue',
  'src/components/ui/AnimatedProgress.vue',
  'src/components/analysis/EvidenceLayerPanel.vue',
  'src/components/analysis/MultiSubjectPanel.vue',
  'src/components/analysis/BoundaryAlertBanner.vue',
  'src/components/analysis/StandardPathBadge.vue',
  'src/views/ReportView.vue',
  'src/views/WelcomeView.vue'
];

function fixVueFile(filePath) {
  const fullPath = path.join(__dirname, filePath);

  if (!fs.existsSync(fullPath)) {
    console.log(`跳过不存在的文件：${filePath}`);
    return;
  }

  let content = fs.readFileSync(fullPath, 'utf-8');
  let originalContent = content;

  // 1. Fix broken ref() declarations in script section
  // Pattern: "const xxx = // comment\nconst value)" -> "const xxx = ref(value)"
  content = content.replace(
    /const\s+(\w+)\s*=\s*\/\/\s*定义响应式引用\s*\nconst\s+([^)]+)\)/g,
    (match, varName, value) => {
      // Determine if it needs ref() or reactive()
      if (value.trim().startsWith('new ') || value.trim().startsWith('{') || value.trim().startsWith('[')) {
        return `const ${varName} = ref(${value.trim()})`;
      }
      return `const ${varName} = ref(${value.trim()})`;
    }
  );

  // 2. Remove all HTML comments from template section
  const templateMatch = content.match(/<template>([\s\S]*)<\/template>/);
  if (templateMatch) {
    let template = templateMatch[1];

    // Remove all HTML comments
    template = template.replace(/<!--[\s\S]*?-->/g, '');

    // Remove extra blank lines
    template = template.replace(/\n\s*\n\s*\n/g, '\n\n');

    // Rebuild template
    content = content.replace(/<template>[\s\S]*<\/template>/, `<template>${template}</template>`);
  }

  // 3. Fix specific broken patterns
  // Fix: "const displayValue = // comment\nconst 0)" -> "const displayValue = ref(0)"
  content = content.replace(
    /const\s+displayValue\s*=\s*\/\/[^\n]*\nconst\s+0\)/g,
    'const displayValue = ref(0)'
  );

  // Fix: "const activeTab = // comment\nconst 'layer1')" -> "const activeTab = ref('layer1')"
  content = content.replace(
    /const\s+activeTab\s*=\s*\/\/[^\n]*\nconst\s+'layer1'\)/g,
    "const activeTab = ref('layer1')"
  );

  // Fix: "const expandedSubjects = // comment\nconst new Set())" -> "const expandedSubjects = ref(new Set())"
  content = content.replace(
    /const\s+expandedSubjects\s*=\s*\/\/[^\n]*\nconst\s+new\s+Set\(\)\)/g,
    'const expandedSubjects = ref(new Set())'
  );

  if (content !== originalContent) {
    fs.writeFileSync(fullPath, content, 'utf-8');
    console.log(`✓ 已修复：${filePath}`);
  } else {
    console.log(`- 无需修改：${filePath}`);
  }
}

console.log('开始修复 Vue 文件...\n');
filesToFix.forEach(file => {
  fixVueFile(file);
});
console.log('\n修复完成！');
