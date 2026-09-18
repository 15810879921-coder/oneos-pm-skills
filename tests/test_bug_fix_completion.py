import argparse
import contextlib
import copy
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/yunxiao-development-delivery/scripts'
names = ['yunxiao_bug_fix_evidence', 'yunxiao_cli_bug_batch', 'yunxiao_cli_bug_delivery']
saved = {name: sys.modules.pop(name, None) for name in names}
sys.path.insert(0, str(SCRIPTS))
F, B, D = [importlib.import_module(name) for name in names]
sys.path.pop(0)
for name, old in saved.items():
    sys.modules.pop(name, None)
    if old is not None:
        sys.modules[name] = old


class BugFixCompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.snapshot = {'snapshotHash': 'snapshot', 'currentUser': {'id': 'user'}}
        self.group = dict(groupId='web', bugSerials=['ONEOS-1'], repositoryId='10', localId=12,
                          sourceBranch='fix/ONEOS-1', targetBranch='develop', result='merged',
                          state='MERGED', mergedRevision='b' * 40, expectedSourceCommit='a' * 40,
                          sourceVerifiedAtMerge=True)
        self.merge = dict(schema=F.MERGE_SCHEMA, snapshotHash='snapshot', user={'id': 'user'}, results=[self.group])
        self.report = self.root / 'validation.log'
        self.report.write_text('7 targeted regression cases passed', encoding='utf-8')
        self.row = dict(bugSerialNumber='ONEOS-1', groupId='web', status='passed', revision='a' * 40,
                        repairSummary='边界值保留原始输入', reportPath='validation.log',
                        reportSha256=hashlib.sha256(self.report.read_bytes()).hexdigest())
        self.validation = dict(schemaVersion=F.VALIDATION_SCHEMA, snapshotHash='snapshot', results=[self.row])
        self.live_mr = {**self.group, 'projectId': '10'}
        self.live = dict(id='bug', serialNumber='ONEOS-1', assignedTo={'id': 'user'}, verifier={'id': 'qa'},
                         status={'name': '处理中'}, description='用户原始描述', formatType='MARKDOWN')
        self.bug = copy.deepcopy(self.live)
        self.writes = []

    def files(self):
        self.merge['hash'] = F.digest({k: v for k, v in self.merge.items() if k != 'hash'})
        for name, value in [('merge.json', self.merge), ('validation.json', self.validation)]:
            (self.root / name).write_text(json.dumps(value), encoding='utf-8')
        return str(self.root / 'merge.json'), str(self.root / 'validation.json')

    def validate(self):
        return F.validate(*self.files(), self.snapshot, {'ONEOS-1'}, lambda *_: self.live_mr)['ONEOS-1']

    def cli(self, executable, args, **kwargs):
        if args[0] == 'projex-get-workitem':
            return copy.deepcopy(self.live)
        if args[0] == 'codeup-get-change-request':
            return self.live_mr
        if args[0] == 'projex-update-workitem':
            fields = json.loads(args[args.index('--biz-body') + 1])
            self.writes.append(fields)
            self.live.update(fields)
            self.live['status'] = {'name': '已修复'}
            return {}
        raise AssertionError('Unexpected platform call: ' + args[0])

    def update(self, record):
        with patch.object(B, 'run_devops', self.cli), patch.object(B, 'resolve_target_status', return_value='fixed'):
            return B.update_one('cli', self.bug, 'user', '已修复', {}, record)

    def test_merged_fix_without_flow_updates_and_reads_back_pending_handoff(self):
        record = self.validate()
        result = self.update(record)
        self.assertEqual(result['result'], 'updated')
        self.assertEqual(set(self.writes[0]), {'status', 'description', 'formatType'})
        self.assertIn('待部署、待交付测试', self.live['description'])
        self.assertIn('边界值保留原始输入', self.live['description'])
        self.assertIn('MR：!12', self.live['description'])
        self.assertEqual(F.existing_record(self.live['description']), record)
        self.assertFalse(record['qaReady'])
        self.assertEqual(self.update(record)['result'], 'idempotent')
        self.assertEqual(len(self.writes), 1)

    def test_invalid_development_evidence_is_rejected(self):
        original = copy.deepcopy(self.row)
        for change in ({'status': 'failed'}, {'revision': 'c' * 40}, {'repairSummary': ''},
                       {'reportPath': 'missing'}, {'reportSha256': 'wrong'}):
            with self.subTest(change=change):
                self.row.clear(); self.row.update(original); self.row.update(change)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_fresh_mr_identity_state_and_version_must_match(self):
        original = copy.deepcopy(self.live_mr)
        for change in ({'state': 'OPENED'}, {'projectId': 'other'}, {'localId': 99},
                       {'sourceBranch': 'other'}, {'targetBranch': 'master'}, {'mergedRevision': 'c' * 40}):
            with self.subTest(change=change):
                self.live_mr = {**original, **change}
                with self.assertRaises(ValueError):
                    self.validate()

    def test_old_merge_without_source_proof_requires_merged_revision_validation(self):
        self.group.pop('sourceVerifiedAtMerge')
        with self.assertRaises(ValueError):
            self.validate()
        self.row['revision'] = 'b' * 40
        self.validate()

    def test_partial_multi_repository_fix_cannot_be_marked_fixed(self):
        self.merge['results'].append({**self.group, 'groupId': 'backend', 'result': 'blocked'})
        with self.assertRaises(ValueError):
            self.validate()
        self.merge['results'][1]['result'] = 'merged'
        with self.assertRaises(ValueError):
            self.validate()  # backend lacks its own validation

    def test_missing_failed_group_scope_is_rejected(self):
        self.merge['results'].append({'groupId': 'backend', 'result': 'blocked'})
        with self.assertRaises(ValueError):
            self.validate()

    def test_receipt_tamper_and_snapshot_drift_are_rejected(self):
        paths = self.files()
        value = json.loads(Path(paths[0]).read_text())
        value['results'][0]['mergedRevision'] = 'c' * 40
        Path(paths[0]).write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            F.validate(*paths, self.snapshot, {'ONEOS-1'}, lambda *_: self.live_mr)
        self.snapshot['snapshotHash'] = 'other'
        with self.assertRaises(ValueError):
            self.validate()

    def test_owner_verifier_and_write_time_mr_drift_block_zero_writes(self):
        record = self.validate()
        original = copy.deepcopy(self.live)
        for field in ['assignedTo', 'verifier']:
            self.live = {**original, field: {'id': 'other'}}
            self.assertEqual(self.update(record)['result'], 'blocked')
        self.live = original
        self.live_mr['state'] = 'OPENED'
        self.assertEqual(self.update(record)['result'], 'blocked')
        self.assertEqual(self.writes, [])

    def test_missing_merge_or_validation_no_deployment_bypass(self):
        self.snapshot['bugs'] = [self.bug]
        args = argparse.Namespace(snapshot='unused', serial=['ONEOS-1'], target='已修复',
                                  deployment_evidence='old-deployment.json')
        with patch.object(B, 'find_aliyun', return_value='cli'), patch.object(B, 'require_auth_env'), \
             patch.object(B, 'current_user', return_value={'id': 'user'}), \
             patch.object(B, 'load_snapshot', return_value=self.snapshot), patch.object(B, 'run_devops') as remote:
            with self.assertRaises(B.AdapterError):
                B.cmd_set_status(args)
            remote.assert_not_called()

    def test_reopened_fix_preserves_history_and_html_escapes_summary(self):
        old = self.validate()
        description = F.append_record('原始描述', old, 'HTML')
        new = copy.deepcopy(old)
        new['groups'][0]['repairSummary'] = '<script>bad</script>'
        with self.assertRaises(ValueError):
            F.append_record(description, new, 'HTML')
        updated = F.append_record(description, new, 'HTML', allow_new_cycle=True)
        self.assertIn('ONEOS_BUG_FIX_HISTORY:', updated)
        self.assertIn('原始描述', updated)
        self.assertNotIn('<script>', updated)
        self.assertEqual(F.existing_record(updated), new)

    def test_no_flow_preflight_requirement(self):
        spec = {**self.group, 'associationMode': 'associated-development-branch', 'reuseExisting': True}
        plan = {'groups': [spec], 'snapshotPath': 'snapshot.json'}
        args = argparse.Namespace(plan='unused', output=str(self.root / 'preflight.json'))
        with patch.object(B, 'find_aliyun', return_value='cli'), \
             patch.object(D, 'load_plan', return_value=(plan, self.snapshot, {'id': 'user'})), \
             patch.object(D, 'repository', return_value={'id': '10'}), \
             patch.object(D, 'exact_branch', return_value={'commit': {'id': 'a' * 40}}), \
             patch.object(D, 'validate_pipeline', side_effect=AssertionError('Flow must not be read')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(D.cmd_preflight(args), 0)
        self.assertIsNone(json.loads(Path(args.output).read_text())['testPipeline'])

    def test_legacy_automatic_pipeline_entry_is_disabled_without_remote_calls(self):
        with patch.object(B, 'run_devops') as remote:
            with self.assertRaises(B.AdapterError):
                D.cmd_start_test(argparse.Namespace())
            remote.assert_not_called()

    def test_merge_action_readback_retry_and_source_drift(self):
        mrs = dict(schema=D.MR_SCHEMA, user={'id': 'user'}, snapshotHash='snapshot',
                   snapshotPath='snapshot.json', results=[self.group])
        mr_path = self.root / 'mrs.json'
        D.write_receipt(mr_path, mrs)
        args = argparse.Namespace(mrs=str(mr_path), output=str(self.root / 'merges.json'), merge_type='no-fast-forward')
        live = {**self.live_mr, 'state': 'OPENED'}
        calls = []
        def run(executable, argv, **kw):
            self.assertEqual(argv[0], 'codeup-merge-change-request')
            calls.append(argv)
            live['state'] = 'MERGED'
        with patch.object(B, 'find_aliyun', return_value='cli'), \
             patch.object(D, 'ensure_current_user', return_value={'id': 'user'}), \
             patch.object(D, 'mr_detail', side_effect=lambda *_: copy.deepcopy(live)), \
             patch.object(D, 'exact_branch', return_value={'commit': {'id': 'a' * 40}}), \
             patch.object(B, 'run_devops', side_effect=run), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(D.cmd_merge_mrs(args), 0)
            self.assertEqual(D.cmd_merge_mrs(args), 0)
        self.assertEqual(len(calls), 1)
        receipt = json.loads(Path(args.output).read_text())
        self.assertTrue(receipt['results'][0]['sourceVerifiedAtMerge'])
        self.assertEqual(receipt['results'][0]['result'], 'idempotent')
        args.output = str(self.root / 'drift.json')
        live['state'] = 'OPENED'
        with patch.object(B, 'find_aliyun', return_value='cli'), \
             patch.object(D, 'ensure_current_user', return_value={'id': 'user'}), \
             patch.object(D, 'mr_detail', return_value=live), \
             patch.object(D, 'exact_branch', return_value={'commit': {'id': 'c' * 40}}), \
             patch.object(B, 'run_devops') as remote, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(D.cmd_merge_mrs(args), 2)
            remote.assert_not_called()
        blocked = json.loads(Path(args.output).read_text())['results'][0]
        self.assertEqual(blocked['bugSerials'], ['ONEOS-1'])


if __name__ == '__main__':
    unittest.main()
