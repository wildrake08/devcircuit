import tempfile
import unittest
from pathlib import Path
from devcircuit.copilot import LifecycleCopilot
from devcircuit.engine import Engine
from devcircuit.store import digest,read,write
from devcircuit.template_edition import generate_manifest,verify_scaffold,workspace_status

SERVICE='def calculate(a,b):return a+b\n'
TEST='import unittest\nclass T(unittest.TestCase):\n def test_ok(self):self.assertTrue(True)\n'

class TemplateEditionTests(unittest.TestCase):
    def scaffold(self):
        temporary=tempfile.TemporaryDirectory();root=Path(temporary.name);(root/'src').mkdir();(root/'tests').mkdir();(root/'.devcircuit-template').mkdir();(root/'.github').mkdir();(root/'.github/CODEOWNERS').write_text('# bootstrap placeholder\n');(root/'src/service.py').write_text(SERVICE);(root/'tests/test_service.py').write_text(TEST);(root/'README.md').write_text('template\n');generate_manifest(root);return temporary,root
    def test_exact_nonempty_scaffold_is_adopted(self):
        temporary,root=self.scaffold()
        with temporary:
            result=Engine(root).init(system_id='sample',purpose='Serve users safely',beneficiary='users',template_manifest=root/'.devcircuit-template/template-manifest.json',github_owner='@example/reviewers')
            self.assertEqual(result['state'],'initialized');self.assertTrue(result['template_manifest_digest']);self.assertEqual((root/'.github/CODEOWNERS').read_text(),'* @example/reviewers\n');self.assertTrue(workspace_status(root)['valid'])
    def test_tampered_scaffold_is_rejected(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'src/service.py').write_text('tampered\n')
            with self.assertRaises(ValueError):Engine(root).init(template_manifest=root/'.devcircuit-template/template-manifest.json',github_owner='@example/reviewers')
    def test_invalid_github_owner_is_rejected(self):
        temporary,root=self.scaffold()
        with temporary:
            with self.assertRaises(ValueError):Engine(root).init(template_manifest=root/'.devcircuit-template/template-manifest.json',github_owner='not-an-owner')
    def test_extra_file_is_rejected_before_adoption(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'unexpected.txt').write_text('not released\n')
            self.assertFalse(verify_scaffold(root,strict=True)['valid'])
    def test_mutable_app_change_does_not_mask_immutable_tamper(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'src/service.py').write_text('expected future governed change\n');(root/'.github/CODEOWNERS').write_text('* @example/reviewers\n');self.assertTrue(verify_scaffold(root,strict=False)['valid'])
            (root/'README.md').write_text('tampered\n');self.assertFalse(verify_scaffold(root,strict=False)['valid'])
    def test_symlink_is_rejected(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'link').symlink_to(root/'README.md')
            self.assertFalse(verify_scaffold(root,strict=True)['valid'])
    def test_local_environment_and_build_metadata_are_safely_ignored(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'.venv/bin').mkdir(parents=True);(root/'.venv/bin/python').symlink_to('/usr/bin/python3')
            (root/'build/lib').mkdir(parents=True);(root/'build/lib/generated.py').write_text('generated\n')
            (root/'package.egg-info').mkdir();(root/'package.egg-info/PKG-INFO').write_text('metadata\n')
            self.assertTrue(verify_scaffold(root,strict=True)['valid'])
    def test_unapproved_local_directory_remains_rejected(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'private-cache').mkdir();(root/'private-cache/hidden.txt').write_text('unexpected\n')
            self.assertFalse(verify_scaffold(root,strict=True)['valid'])
    def test_symlink_outside_local_allowlist_remains_rejected(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'src/alias.py').symlink_to(root/'README.md')
            self.assertFalse(verify_scaffold(root,strict=True)['valid'])
    def test_authenticated_template_upgrade_preserves_ledger_and_requires_reassessment(self):
        temporary,root=self.scaffold()
        with temporary:
            Engine(root).init(system_id='sample',template_manifest=root/'.devcircuit-template/template-manifest.json',github_owner='@example/reviewers');store=Engine(root).store;before_count=store.verify_ledger()[1];old=store.deref('baseline','baseline','assessor')[1]['payload']['template_manifest_digest']
            engine=Engine(root);engine.mandate('old-run','pre-upgrade work','driver',['tests/*'],['test_pass_rate']);write(root/'.devcircuit/autonomy-runs/old-run.json',{'run_id':'old-run','phase':'awaiting_build','build_scope':'build:old'})
            product={'format':'DevCircuit-minimum-viable-baseline/v1','purpose':'Serve the adopted product purpose','beneficiaries':['operators'],'outcome_hypothesis':{'metric':'health_rate','operator':'>=','target':1.0,'unit':'ratio'},'operating_conditions':{'runtime':'CPython'},'compliance_obligations':[]};scope='baseline:'+digest(engine.baseline_basis(product));authorization=engine.authorize(scope,'product','owner','system');product.update({'decision':'authorized','authorization_digest':authorization['authorization_digest']});write(root/'.devcircuit/operator/workflow.json',{'intake':{'baseline':product}})
            (root/'README.md').write_text('replacement template\n');replacement=generate_manifest(root);self.assertNotEqual(old,replacement['manifest_digest'])
            copilot=LifecycleCopilot(root);credential=(root/'.devcircuit/keys/release-owner.key').read_text();session=copilot.open_session('release-owner',credential);proposal=copilot.propose_template_upgrade(session['session_id'],session['token']);self.assertEqual(proposal['payload']['from_manifest_digest'],old);self.assertEqual(proposal['payload']['to_manifest_digest'],replacement['manifest_digest'])
            result=copilot.decide(session['session_id'],session['token'],proposal['decision_id'],'approve',proposal['challenge']);self.assertTrue(result['effect']['reassessment_required']);self.assertEqual(result['effect']['affected_runs'],['old-run']);self.assertIsNotNone(result['effect']['product_binding']);self.assertTrue(workspace_status(root)['valid']);self.assertTrue(store.verify_ledger()[0]);self.assertGreater(store.verify_ledger()[1],before_count);engine.verify_product_binding(read(root/'.devcircuit/operator/workflow.json')['intake']['baseline'])
            self.assertEqual(read(root/'.devcircuit/autonomy-runs/old-run.json')['phase'],'changes_requested');self.assertEqual(read(root/'.devcircuit/mandates/old-run.json')['status'],'reassessment_required')
            with self.assertRaises(ValueError):copilot.decide(session['session_id'],session['token'],proposal['decision_id'],'approve',proposal['challenge'])
    def test_template_upgrade_rejects_wrong_principal_and_stale_scaffold(self):
        temporary,root=self.scaffold()
        with temporary:
            Engine(root).init(system_id='sample',template_manifest=root/'.devcircuit-template/template-manifest.json',github_owner='@example/reviewers');(root/'README.md').write_text('replacement one\n');generate_manifest(root);copilot=LifecycleCopilot(root)
            owner_key=(root/'.devcircuit/keys/owner.key').read_text();owner=copilot.open_session('owner',owner_key)
            with self.assertRaises(PermissionError):copilot.propose_template_upgrade(owner['session_id'],owner['token'])
            release_key=(root/'.devcircuit/keys/release-owner.key').read_text();release=copilot.open_session('release-owner',release_key);proposal=copilot.propose_template_upgrade(release['session_id'],release['token']);(root/'README.md').write_text('replacement two\n');generate_manifest(root)
            with self.assertRaisesRegex(RuntimeError,'stale'):copilot.decide(release['session_id'],release['token'],proposal['decision_id'],'approve',proposal['challenge'])
