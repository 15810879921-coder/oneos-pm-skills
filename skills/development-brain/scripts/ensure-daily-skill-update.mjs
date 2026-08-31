#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import { closeSync, mkdirSync, openSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const TARGET_SKILLS = [
  'YunxiaoPM',
  'yunxiao-development-delivery',
  'development-brain',
  'YunxiaoQA',
  'yunxiao-release-operations',
];
const LOCK_STALE_MS = 10 * 60 * 1000;
const FAILURE_COOLDOWN_MS = 30 * 60 * 1000;
const UPDATE_TIMEOUT_MS = 120 * 1000;

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith('--')) continue;
    const name = key.slice(2);
    const value = argv[index + 1];
    if (value && !value.startsWith('--')) {
      result[name] = value;
      index += 1;
    } else {
      result[name] = true;
    }
  }
  return result;
}

function localDate(now) {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function defaultStateDir() {
  if (process.platform === 'win32' && process.env.LOCALAPPDATA) {
    return path.join(process.env.LOCALAPPDATA, 'OneOS', 'skill-updater');
  }
  if (process.env.XDG_STATE_HOME) {
    return path.join(process.env.XDG_STATE_HOME, 'oneos', 'skill-updater');
  }
  return path.join(os.homedir(), '.local', 'state', 'oneos', 'skill-updater');
}

function readJson(filePath) {
  try {
    return JSON.parse(readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function safeMessage(value) {
  return String(value ?? '')
    .replace(/\u001b\[[0-9;]*m/g, '')
    .replace(/[\r\n]+/g, ' ')
    .trim()
    .slice(-800);
}

function emit(action, extra = {}) {
  process.stdout.write(`${JSON.stringify({ action, ...extra })}\n`);
}

function writeState(filePath, state) {
  const temporary = `${filePath}.${process.pid}.tmp`;
  writeFileSync(temporary, `${JSON.stringify(state, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
  renameSync(temporary, filePath);
}

function acquireLock(lockPath, now) {
  try {
    const descriptor = openSync(lockPath, 'wx', 0o600);
    writeFileSync(descriptor, JSON.stringify({ pid: process.pid, startedAt: now.toISOString() }));
    closeSync(descriptor);
    return true;
  } catch (error) {
    if (error?.code !== 'EEXIST') throw error;
  }

  try {
    if (now.getTime() - statSync(lockPath).mtimeMs > LOCK_STALE_MS) {
      rmSync(lockPath, { force: true });
      return acquireLock(lockPath, now);
    }
  } catch {
    return acquireLock(lockPath, now);
  }
  return false;
}

function runUpdater(args, stateDir) {
  if (args['mock-result']) {
    return args['mock-result'] === 'success'
      ? { status: 0, message: 'mock update succeeded' }
      : { status: 1, message: 'mock update failed' };
  }

  const updateArgs = ['-y', 'skills@latest', 'update', ...TARGET_SKILLS, '-g', '-y'];
  const options = {
    cwd: stateDir,
    encoding: 'utf8',
    env: { ...process.env, NO_COLOR: '1', FORCE_COLOR: '0' },
    maxBuffer: 4 * 1024 * 1024,
    timeout: UPDATE_TIMEOUT_MS,
    windowsHide: true,
  };
  let result;
  if (process.platform === 'win32') {
    result = spawnSync(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', 'npx', ...updateArgs], options);
  } else {
    result = spawnSync('npx', updateArgs, options);
  }

  const message = safeMessage(result.stderr || result.stdout || result.error?.message);
  if (result.error?.code === 'ENOENT') return { status: null, message: 'npx is unavailable' };
  if (result.error?.code === 'ETIMEDOUT') return { status: 1, message: 'skill update timed out' };
  return { status: result.status, message };
}

const args = parseArgs(process.argv.slice(2));
const currentSkill = String(args['current-skill'] || '').trim();
const now = args.now ? new Date(args.now) : new Date();
if (Number.isNaN(now.getTime())) {
  emit('failed', { reason: 'invalid --now value' });
  process.exitCode = 2;
} else {
  const date = localDate(now);
  const stateDir = path.resolve(String(args['state-dir'] || defaultStateDir()));
  mkdirSync(stateDir, { recursive: true });
  const statePath = path.join(stateDir, 'daily-update.json');
  const lockPath = path.join(stateDir, 'daily-update.lock');
  const previous = readJson(statePath);

  if (previous?.status === 'success' && previous.date === date) {
    emit('skipped-today', { date, completedAt: previous.completedAt });
  } else if (
    previous?.status === 'failed'
    && previous.date === date
    && Date.parse(previous.nextRetryAfter || '') > now.getTime()
  ) {
    emit('cooldown', { date, nextRetryAfter: previous.nextRetryAfter, message: previous.message });
  } else if (!acquireLock(lockPath, now)) {
    emit('in-progress', { date });
  } else {
    try {
      const startedAt = now.toISOString();
      const result = runUpdater(args, stateDir);
      if (result.status === 0) {
        const state = {
          schemaVersion: 1,
          date,
          status: 'success',
          startedAt,
          completedAt: new Date().toISOString(),
          currentSkill,
          skills: TARGET_SKILLS,
          exitCode: 0,
          message: result.message,
        };
        writeState(statePath, state);
        emit('updated', { date, currentSkill, skills: TARGET_SKILLS, reloadCurrentSkill: true });
      } else {
        const nextRetryAfter = new Date(now.getTime() + FAILURE_COOLDOWN_MS).toISOString();
        const action = result.status === null ? 'unavailable' : 'failed';
        const state = {
          schemaVersion: 1,
          date,
          status: 'failed',
          startedAt,
          completedAt: new Date().toISOString(),
          currentSkill,
          skills: TARGET_SKILLS,
          exitCode: result.status,
          nextRetryAfter,
          message: result.message,
        };
        writeState(statePath, state);
        emit(action, { date, nextRetryAfter, message: result.message });
      }
    } catch (error) {
      emit('failed', { date, message: safeMessage(error?.message || error) });
      process.exitCode = 1;
    } finally {
      rmSync(lockPath, { force: true });
    }
  }
}
