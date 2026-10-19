import json
import sys
import tempfile
import unittest
from pathlib import Path

from devcircuit.autonomy import AutonomousLoop
from devcircuit.developer_cli import DeveloperExperience
from devcircuit.intake import AUTHORITY_ROLES
from devcircuit.engine import Engine
from devcircuit.project import create_project,migrate_project
from devcircuit.store import digest


def answers():
    return {
        "outcome_statement":"Keep the application healthy",
        "outcome_metric":"health_rate",
        "outcome_unit":"ratio",
        "outcome_operator":">=",
        "outcome_target":1.0,
        "outcome_baseline":0.0,
        "data_classes":["none identified"],
        "compliance_obligations":["none identified"],
        "operating_conditions":{"runtime":"local Python"},
        "authorities":{role:"project owner" for role in AUTHORITY_ROLES},
    }


class DeveloperExperienceTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/"application"
        create_project(self.root,"sample-application","Provide a useful sample","users")
        self.experience=DeveloperExperience(self.root)

    def tearDown(self):self.temp.cleanup()

    def decision(self,review,summary):
        return next(item["decision_id"] for group in review["reviews"] for item in group["items"] if summary in item["summary"])

    def test_generated_repository_is_application_centered(self):
        self.assertTrue((self.root/"src/service.py").is_file())
        self.assertTrue((self.root/".devcircuit/project.json").is_file())
        self.assertFalse((self.root/"devcircuit").exists())
        self.assertFalse((self.root/"kernel_tests").exists())
        self.assertFalse((self.root/"verification").exists())
        self.assertIn("sample-application",(self.root/"README.md").read_text())
        self.assertIn('.devcircuit/operator/local-sessions.json',(self.root/'.gitignore').read_text())
        self.assertIn('.devcircuit/keys/',(self.root/'.gitignore').read_text())

    def test_one_interface_operates_complete_local_slice(self):
        self.experience.answer(answers())
        review=self.experience.review();self.assertTrue(self.experience.session_path.is_file());self.assertNotIn('token',json.dumps(review).lower());self.decision(review,"product baseline")
        self.experience.converse("approve next")
        script="import json;print(json.dumps({'status':'done','summary':'current application already satisfies the slice','changes':[]}))"
        AutonomousLoop(self.root).register_driver("test-driver","generic",[sys.executable,"-c",script,"{prompt}"])
        request=self.experience.request_slice("Validate the first application slice","test-driver")
        self.assertEqual(request["state"],"awaiting_engineering_authority")
        self.decision(self.experience.review(),"bounded autonomous engineering mandate")
        after_mandate=self.experience.converse("approve next")["result"]
        self.assertEqual(after_mandate["automatic_continuation"]["result"]["phase"],"build")
        self.decision(self.experience.review(),"release-grade build")
        after_build=self.experience.converse("approve next")["result"]
        self.assertEqual(after_build["automatic_continuation"]["result"]["phase"],"artifact_acceptance")
        self.decision(self.experience.review(),"accept exact built artifact")
        after_acceptance=self.experience.converse("approve next")["result"]
        self.assertEqual(after_acceptance["automatic_continuation"]["result"]["phase"],"deployment")
        self.decision(self.experience.review(),"deploy exact accepted artifact")
        final=self.experience.converse("approve next")["result"]
        self.assertTrue(final["automatic_continuation"]["result"]["valid"])
        self.assertEqual(final["status"]["progress"]["completed"],7)

    def test_thin_github_starter_can_initialize_in_place(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'.github').mkdir();(root/'.devcircuit-template.json').write_text(json.dumps({"format":"DevCircuit-thin-starter/v1","kernel":"external","version":"1.0.0"}));(root/'README.md').write_text('starter')
            result=create_project(root,'from-template')
            self.assertEqual(result['experience'],'ready_for_conversation')
            self.assertEqual(len(result['questions']),1)
            self.assertFalse((root/'.devcircuit-template.json').exists())
            self.assertFalse((root/'devcircuit').exists())

    def test_application_archetypes_generate_distinct_clean_projects(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            expected={'point-of-sale':'catalog','web-saas':'render_home','rest-api':'route','worker':'process'}
            for profile,symbol in expected.items():
                app=root/profile;create_project(app,profile,profile+' application',profile+' users',profile);source=(app/'src/service.py').read_text();self.assertIn('def '+symbol,source);self.assertFalse((app/'devcircuit').exists());self.assertTrue((app/'.devcircuit/environment-discovery.json').is_file())

    def test_plain_language_intake_reaches_baseline_without_json(self):
        first=self.experience.converse('Checkout should take no more than 45 seconds; it currently takes 80 seconds.')
        self.assertEqual(first['questions'][0]['id'],'ask-risk')
        second=self.experience.converse('We handle payment tokens and customer transaction data.')
        self.assertEqual(second['questions'][0]['id'],'ask-conditions')
        third=self.experience.converse('It runs on a mobile coffee cart with intermittent connectivity.')
        self.assertEqual(third['questions'][0]['id'],'ask-authority')
        final=self.experience.converse('I am the project owner for all decisions in this local project.')
        self.assertEqual(final['questions'],[])
        self.assertEqual(self.experience.status()['current_step'],'authorize_product_baseline')

    def test_legacy_embedded_template_migrates_without_losing_application_or_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);Engine(root).init(system_id='legacy-application');(root/'.devcircuit').rename(root/'.clses-v1');framework=root/'clses_mvas_v1/kernel.py';framework.parent.mkdir();framework.write_text('legacy kernel\n');(root/'.clses-template').mkdir();entry={'path':'clses_mvas_v1/kernel.py','sha256':digest(framework.read_bytes()),'size':framework.stat().st_size};(root/'.clses-template/template-manifest.json').write_text(json.dumps({'entries':[entry]}));before=(root/'src/service.py').read_bytes();plan=migrate_project(root);self.assertTrue(plan['safe']);self.assertFalse(plan['applied']);self.assertEqual(plan['from'],'embedded-template-v4');result=migrate_project(root,apply=True);self.assertTrue(result['applied']);self.assertEqual((root/'src/service.py').read_bytes(),before);self.assertTrue((root/'.devcircuit/ledger.jsonl').is_file());self.assertTrue((root/'.devcircuit-migration-backup/ledger.jsonl').is_file());self.assertFalse((root/'clses_mvas_v1').exists())

    def test_external_clses_v5_project_migrates_state_without_touching_application(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);Engine(root).init(system_id='v5-application');(root/'.devcircuit').rename(root/'.clses');before=(root/'src/service.py').read_bytes();plan=migrate_project(root);self.assertEqual(plan['from'],'external-kernel-v5');self.assertEqual(plan['remove'],[]);result=migrate_project(root,apply=True);self.assertTrue(result['applied']);self.assertEqual((root/'src/service.py').read_bytes(),before);self.assertTrue((root/'.devcircuit/ledger.jsonl').is_file());self.assertTrue((root/'.devcircuit-migration-backup/ledger.jsonl').is_file());self.assertFalse((root/'.clses').exists())


if __name__=='__main__':unittest.main()
