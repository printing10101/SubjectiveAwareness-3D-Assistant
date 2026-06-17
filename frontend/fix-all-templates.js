#!/usr/bin/env node
/**
 * Batch fix Vue template comment issues and script syntax errors
 * - Remove HTML comments inside template tags (between attributes)
 * - Fix "async // comment\nfunction" -> "async function"
 * - Fix "} // comment\n catch" -> "} catch"
 * - Fix broken ref() declarations
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.join(__dirname, 'src');

// Recursively find all Vue files
function findVueFiles(dir) {
  const files = [];
  const items = fs.readdirSync(dir);
  
  for (const item of items) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);
    
    if (stat.isDirectory()) {
      files.push(...findVueFiles(fullPath));
    } else if (item.endsWith('.vue')) {
      files.push(fullPath);
    }
  }
  
  return files;
}

const vueFiles = findVueFiles(srcDir);

let fixedCount = 0;

for (const filePath of vueFiles) {
  let content = fs.readFileSync(filePath, 'utf-8');
  const original = content;
  const relPath = path.relative(__dirname, filePath);

  // 1. Fix HTML comments between template attributes
  // Pattern: lines that are ONLY HTML comments inside <template> section
  // These appear as: <!-- some comment -->\n between attributes
  const templateMatch = content.match(/<template>([\s\S]*?)<\/template>/);
  if (templateMatch) {
    let template = templateMatch[1];
    
    // Remove standalone HTML comment lines (lines that only contain comments)
    // These are comments that appear between attributes, which is invalid in Vue
    template = template.replace(/^\s*<!--[^>]*-->\s*\n/gm, '');
    
    // Also remove comments that are on the same line as attributes but before them
    // e.g., '    <!-- comment -->\n    v-if="..."'
    // This is already handled by the above regex
    
    content = content.replace(/<template>[\s\S]*?<\/template>/, `<template>${template}</template>`);
  }

  // 2. Fix "async // comment\nfunction" -> "async function"
  content = content.replace(
    /async\s+\/\/[^\n]*\n\s*function\s/g,
    'async function '
  );

  // 3. Fix "} // comment\n catch" -> "} catch"
  content = content.replace(
    /\}\s*\/\/[^\n]*\n\s*catch\s/g,
    '} catch '
  );

  // 4. Fix broken ref() declarations like:
  //    const x = // comment\n    ref(...)
  content = content.replace(
    /const\s+(\w+)\s*=\s*\/\/[^\n]*\n\s*(ref\([^)]*\))/g,
    'const $1 = $2'
  );

  // 5. Fix broken ref() declarations like:
  //    const x = // comment\n    const null)
  // This is malformed - should be: const x = ref(null)
  content = content.replace(
    /const\s+(\w+)\s*=\s*\/\/[^\n]*\n\s*const\s+null\)/g,
    'const $1 = ref(null)'
  );

  // 6. Fix broken line continuations like:
  //    chapterConfig// comment\n.forEach(
  content = content.replace(
    /(\w+)\/\/[^\n]*\n\s*\.(forEach|map|filter|reduce|find|some|every|join|includes|indexOf|slice|splice|concat|sort|flat|flatMap)\(/g,
    '$1.$2('
  );

  // 7. Fix "Array.from(x)// comment\n.map(" pattern
  content = content.replace(
    /(Array\.from\([^)]+\))\/\/[^\n]*\n\s*\.(map|filter|forEach|reduce|find|some|every)\(/g,
    '$1.$2('
  );

  if (content !== original) {
    fs.writeFileSync(filePath, content, 'utf-8');
    console.log(`FIXED: ${relPath}`);
    fixedCount++;
  }
}

console.log(`\nDone! Fixed ${fixedCount} files out of ${vueFiles.length} total.`);
