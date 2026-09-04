#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const skillDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const knowledgeDir = path.join(skillDir, 'knowledge');
const indexPath = path.join(knowledgeDir, 'knowledge-index.md');
const sources = [
  {
    key: 'confirmed',
    expectedStatus: 'confirmed',
    path: path.join(knowledgeDir, 'confirmed-constraints.md'),
  },
  {
    key: 'candidate',
    expectedStatus: 'candidate',
    path: path.join(knowledgeDir, 'retrospective-candidates.md'),
  },
];

function fail(message) {
  process.stderr.write(`knowledge-index-error: ${message}\n`);
  process.exit(1);
}

function sha256(content) {
  return createHash('sha256').update(content).digest('hex');
}

function parseRecords(source) {
  const records = [];
  const pattern = /```text\s*\r?\n([\s\S]*?)\r?\n```/g;
  let match;
  while ((match = pattern.exec(source.content)) !== null) {
    const body = match[1].trim();
    const id = body.match(/^ID：([^\r\n]+)$/m)?.[1]?.trim();
    const status = body.match(/^状态：([^\r\n]+)$/m)?.[1]?.trim();
    if (!id) continue;
    if (!status) fail(`${source.path} 中 ${id} 缺少状态`);
    records.push({ id, status, body, source: path.basename(source.path) });
  }
  return records;
}

function parseIndexRows(indexContent) {
  const rows = [];
  for (const line of indexContent.split(/\r?\n/)) {
    if (!/^\|\s*DB-[A-Z]-\d{3}\s*\|/.test(line)) continue;
    const cells = line.split('|').slice(1, -1).map((cell) => cell.trim());
    rows.push({ id: cells[0], status: cells[1], source: cells[5] });
  }
  return rows;
}

function parseArgs(argv) {
  const result = { check: false, ids: [] };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--check') {
      result.check = true;
    } else if (argv[index] === '--ids') {
      const value = argv[index + 1];
      if (!value || value.startsWith('--')) fail('--ids 缺少记录 ID');
      result.ids.push(...value.split(',').map((item) => item.trim()).filter(Boolean));
      index += 1;
    } else {
      fail(`未知参数 ${argv[index]}`);
    }
  }
  return result;
}

const indexContent = readFileSync(indexPath);
const indexText = indexContent.toString('utf8');
const allRecords = [];

for (const source of sources) {
  const content = readFileSync(source.path);
  const expectedHash = indexText.match(
    new RegExp('`' + source.key + '_sha256`:\\s*`([a-f0-9]{64})`'),
  )?.[1];
  if (!expectedHash) fail(`索引缺少 ${source.key}_sha256`);
  const actualHash = sha256(content);
  if (actualHash !== expectedHash) {
    fail(`${path.basename(source.path)} 哈希不匹配，索引必须与知识源同步更新`);
  }
  const parsed = parseRecords({ ...source, content: content.toString('utf8') });
  for (const record of parsed) {
    if (record.status !== source.expectedStatus) {
      fail(`${record.id} 状态为 ${record.status}，与源文件类别 ${source.expectedStatus} 不一致`);
    }
  }
  allRecords.push(...parsed);
}

const rows = parseIndexRows(indexText);
const recordMap = new Map();
for (const record of allRecords) {
  if (recordMap.has(record.id)) fail(`知识源存在重复 ID ${record.id}`);
  recordMap.set(record.id, record);
}
const rowMap = new Map();
for (const row of rows) {
  if (rowMap.has(row.id)) fail(`索引存在重复 ID ${row.id}`);
  rowMap.set(row.id, row);
  const record = recordMap.get(row.id);
  if (!record) fail(`索引 ${row.id} 在知识源中不存在`);
  if (row.status !== record.status || row.source !== record.source) {
    fail(`索引 ${row.id} 的状态或源文件与完整记录不一致`);
  }
}
for (const record of allRecords) {
  if (!rowMap.has(record.id)) fail(`知识源 ${record.id} 未进入索引`);
}

const args = parseArgs(process.argv.slice(2));
if (!args.check && args.ids.length === 0) {
  fail('请使用 --check 或 --ids <ID[,ID...]>');
}

if (args.check) {
  const confirmedCount = allRecords.filter((record) => record.status === 'confirmed').length;
  const candidateCount = allRecords.filter((record) => record.status === 'candidate').length;
  process.stdout.write(`knowledge-index-ok confirmed=${confirmedCount} candidate=${candidateCount}\n`);
}

if (args.ids.length > 0) {
  const selected = [];
  const fence = '```';
  for (const id of [...new Set(args.ids)]) {
    const record = recordMap.get(id);
    if (!record) fail(`未知记录 ID ${id}`);
    selected.push(
      '来源：knowledge/' + record.source + '\n\n' + fence + 'text\n'
        + record.body + '\n' + fence,
    );
  }
  process.stdout.write(`${selected.join('\n\n')}\n`);
}
