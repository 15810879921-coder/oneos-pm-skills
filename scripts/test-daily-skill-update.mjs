#!/usr/bin/env node

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const updater = path.join(
  repositoryRoot,
  'skills',
  'development-brain',
  'scripts',
  'ensure-daily-skill-update.mjs',
);
const stateDir = mkdtempSync(path.join(os.tmpdir(), 'oneos-daily-skill-update-'));

function invoke(now, mockResult = 'success') {
  const result = spawnSync(
    process.execPath,
    [
      updater,
      '--current-skill', 'development-brain',
      '--state-dir', stateDir,
      '--now', now,
      '--mock-result', mockResult,
    ],
    { encoding: 'utf8', windowsHide: true },
  );
  assert.equal(result.status, 0, result.stderr || result.stdout);
  return JSON.parse(result.stdout.trim());
}

try {
  assert.equal(invoke('2026-08-31T09:00:00', 'success').action, 'updated');
  assert.equal(invoke('2026-08-31T10:00:00', 'failure').action, 'skipped-today');

  assert.equal(invoke('2026-09-01T09:00:00', 'failure').action, 'failed');
  assert.equal(invoke('2026-09-01T09:10:00', 'success').action, 'cooldown');
  assert.equal(invoke('2026-09-01T09:31:00', 'success').action, 'updated');

  rmSync(path.join(stateDir, 'daily-update.json'), { force: true });
  mkdirSync(stateDir, { recursive: true });
  writeFileSync(
    path.join(stateDir, 'daily-update.lock'),
    JSON.stringify({ pid: 999999, startedAt: new Date().toISOString() }),
    'utf8',
  );
  assert.equal(invoke(new Date().toISOString(), 'success').action, 'in-progress');

  process.stdout.write('每日首次 Skill 更新行为测试通过。\n');
} finally {
  rmSync(stateDir, { recursive: true, force: true });
}
