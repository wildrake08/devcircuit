import base64,copy,json,subprocess,tempfile,time,unittest
from pathlib import Path
from devcircuit.engine import Engine
from devcircuit.production import inventory
from devcircuit.store import canonical,digest,read,write

class EngineTest(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.engine=Engine(self.root);self.engine.init(system_id='test-system')
    def tearDown(self):self.temp.cleanup()
    def change(self,work_id='w1'):
        content='import unittest\nclass T(unittest.TestCase):\n def test_added(self):self.assertTrue(True)\n';request=self.engine.request(work_id,'Add governed test','tests/test_added.py',content,['test_pass_rate']);self.engine.authorize(request['authorization_scope'],'engineering','engineering-reviewer','agent');self.engine.execute(work_id);return self.engine.plan()
    def built(self):
        plan=self.change();self.engine.authorize(plan['build_scope'],'engineering','engineering-reviewer','agent');return self.engine.build()
    def test_initial_state_is_not_assessed(self):self.assertFalse(self.engine.verify()['valid'])
    def test_manual_change_is_rejected(self):
        (self.root/'src/service.py').write_text((self.root/'src/service.py').read_text()+'#manual\n')
        with self.assertRaises(PermissionError):self.engine.plan()
    def test_unknown_trace_is_rejected(self):
        with self.assertRaises(ValueError):self.engine.request('x','x','tests/x.py','x',['missing'])
    def test_undeclared_source_component_is_rejected(self):
        with self.assertRaises(ValueError):self.engine.request('x','x','src/hidden.py','x',['test_pass_rate'])
    def test_work_id_cannot_be_reused(self):
        self.engine.request('x','x','tests/x.py','x',['test_pass_rate'])
        with self.assertRaises(ValueError):self.engine.request('x','changed','tests/y.py','y',['test_pass_rate'])
    def test_duplicate_authorization_is_rejected(self):
        self.engine.authorize('work:x','engineering','engineering-reviewer','agent')
        with self.assertRaises(ValueError):self.engine.authorize('work:x','engineering','engineering-reviewer','agent')
    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):self.engine.request('x','x','../x.py','x',['test_pass_rate'])
    def test_execution_needs_exact_approval(self):
        self.engine.request('x','x','tests/x.py','x',['test_pass_rate'])
        with self.assertRaises(PermissionError):self.engine.execute('x')
    def test_build_needs_exact_change_set_approval(self):
        self.change()
        with self.assertRaises(PermissionError):self.engine.build()
    def test_release_needs_acceptance(self):
        pending=self.built();self.engine.authorize(pending['release_scope'],'release','release-owner','operator')
        with self.assertRaises(PermissionError):self.engine.complete()
    def test_release_needs_deployment_authorization(self):
        pending=self.built();self.engine.authorize(pending['acceptance_scope'],'release','release-owner','operator')
        with self.assertRaises(PermissionError):self.engine.complete()
    def test_full_cycle_is_intrinsic_and_explicitly_local(self):
        pending=self.built();self.engine.authorize(pending['acceptance_scope'],'release','release-owner','operator');self.engine.authorize(pending['release_scope'],'release','release-owner','operator');result=self.engine.complete();self.assertTrue(result['valid']);self.assertEqual(result['intrinsic'],'conformant');self.assertEqual(result['relational'],'locally_demonstrated_not_production_adequacy')
    def test_accept_deploy_monitor_and_production_close_are_durable_stages(self):
        spec=self.engine._spec()[1];spec['outcomes']=[{'key':'checkout_seconds','variable':'checkout_seconds','op':'<=','threshold':45,'unit':'seconds','source':'observe','measurement_key':'checkout_seconds'}]
        proposal=self.engine.propose_spec('production-outcome',spec);self.engine.authorize(proposal['engineering_scope'],'engineering','engineering-reviewer','agent');self.engine.authorize(proposal['acceptance_scope'],'release','release-owner','operator');self.engine.apply_spec('production-outcome')
        pending=self.built();self.engine.authorize(pending['acceptance_scope'],'release','release-owner','operator');accepted=self.engine.accept();self.assertEqual(accepted['phase'],'accepted');self.assertNotIn('deployment_digest',accepted)
        self.engine.authorize(pending['release_scope'],'release','release-owner','operator');monitoring=self.engine.deploy();self.assertEqual(monitoring['phase'],'monitoring')
        with self.assertRaisesRegex(RuntimeError,'production evidence'):self.engine.close_local()
        now=int(time.time());entries=inventory(self.root/'.devcircuit/deployment');d='a'*64;_,active_spec,spec_digest=self.engine._spec();observations=[]
        for item in active_spec['requirements']+active_spec['outcomes']:
            value=1.0 if item['key']=='test_pass_rate' else 30
            observations.append({'criterion_key':item['key'],'measurement_key':item['measurement_key'],'value':value,'unit':item['unit'],'coverage':1.0,'source':item['source'],'method':'signed target measurement','adapter_digest':d,'raw_evidence_sha256':digest(item['key'].encode()),'observed_at':now-1,'expires_at':now+600,'environment_id':'production'})
        evidence={'format':'DevCircuit-production-evidence/v1','system_id':active_spec['system_id'],'spec_digest':spec_digest,'assessed_at':now,'artifact':{'digest':pending['artifact_digest'],'entries':entries},'acceptance':{'artifact_digest':pending['artifact_digest'],'passed':True,'actor':'release-owner','decision_digest':monitoring['acceptance_digest'],'evidence_digest':d},'deployment':{'artifact_digest':pending['artifact_digest'],'environment_id':'production','current_inventory':entries,'deployment_digest':monitoring['deployment_digest'],'authorization_digest':monitoring['release_authorization'],'deployed_at':monitoring['deployed_at']},'observations':observations,'outcome_periods':[{'criterion_key':'checkout_seconds','minimum_sustained_periods':2,'periods':[{'start':now-400,'end':now-300,'value':35,'raw_evidence_sha256':'b'*64},{'start':now-200,'end':now-100,'value':30,'raw_evidence_sha256':'c'*64}]}],'change_monitors':[{'domain':name,'status':'current','checked_at':now-1,'expires_at':now+600,'evidence_digest':d} for name in ('source','dependencies','infrastructure','runtime','security','regulatory')],'supply_chain':{'sbom_digest':d,'provenance_digest':d,'dependency_lock_digest':d,'vulnerability_scan_digest':d,'license_scan_digest':d,'critical_vulnerabilities':0,'policy_passed':True},'recovery':{'rollback_tested':True,'restore_tested':True,'rollback_evidence_digest':d,'restore_evidence_digest':d},'operations':{'monitoring_active':True,'open_critical_incidents':0,'observed_from':now-500,'observed_until':now-1,'telemetry_digest':d},'closure':{'decision':'closed_verified','artifact_digest':pending['artifact_digest'],'spec_digest':spec_digest,'actor':'outcome-authority','decision_digest':d}}
        private=self.root/'private.pem';public=self.root/'public.pem';data=self.root/'production-evidence';signature=self.root/'production-signature';subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(private)],check=True,capture_output=True);subprocess.run(['openssl','pkey','-in',str(private),'-pubout','-out',str(public)],check=True,capture_output=True);data.write_bytes(canonical(evidence));subprocess.run(['openssl','dgst','-sha256','-sign',str(private),'-out',str(signature),str(data)],check=True,capture_output=True);bundle={'evidence':evidence,'evidence_sha256':digest(evidence),'signature_base64':base64.b64encode(signature.read_bytes()).decode()}
        result=self.engine.close_production(bundle,public);self.assertTrue(result['valid']);self.assertEqual(result['relational'],'adequate_for_declared_production_conditions')
    def test_deployment_tamper_invalidates_cycle(self):
        pending=self.built();self.engine.authorize(pending['acceptance_scope'],'release','release-owner','operator');self.engine.authorize(pending['release_scope'],'release','release-owner','operator');self.engine.complete();(self.root/'.devcircuit/deployment/service.py').write_text('tampered')
        self.assertFalse(self.engine.verify()['checks']['deployment_current'])
    def test_post_build_change_stops_release(self):
        pending=self.built();self.engine.authorize(pending['acceptance_scope'],'release','release-owner','operator');self.engine.authorize(pending['release_scope'],'release','release-owner','operator');(self.root/'src/service.py').write_text((self.root/'src/service.py').read_text()+'#manual\n')
        with self.assertRaises(PermissionError):self.engine.complete()
    def test_tampered_ledger_fails_verification(self):
        path=self.root/'.devcircuit/ledger.jsonl';lines=path.read_text().splitlines();value=json.loads(lines[0]);value['kind']='altered';lines[0]=json.dumps(value);path.write_text('\n'.join(lines)+'\n');self.assertFalse(self.engine.verify()['checks']['ledger_valid'])
    def test_tampered_signed_object_is_rejected(self):
        pointer=read(self.root/'.devcircuit/refs/spec.json');path=self.root/'.devcircuit/objects'/(pointer['digest']+'.json');value=read(path);value['payload']['spec']['purpose']='tampered';write(path,value)
        with self.assertRaises(ValueError):self.engine.verify()
    def test_spec_change_requires_engineering_and_acceptance(self):
        spec=read(self.root/'.devcircuit/objects'/(read(self.root/'.devcircuit/refs/spec.json')['digest']+'.json'))['payload']['spec'];spec['constraints'].append('new control');proposal=self.engine.propose_spec('s1',spec);self.engine.authorize(proposal['engineering_scope'],'engineering','engineering-reviewer','agent')
        with self.assertRaises(PermissionError):self.engine.apply_spec('s1')
        self.engine.authorize(proposal['acceptance_scope'],'release','release-owner','operator');self.assertTrue(self.engine.apply_spec('s1')['reassessment_required'])
    def test_stale_spec_proposal_is_rejected(self):
        original=read(self.root/'.devcircuit/objects'/(read(self.root/'.devcircuit/refs/spec.json')['digest']+'.json'))['payload']['spec'];one=json.loads(json.dumps(original));one['constraints'].append('one');two=json.loads(json.dumps(original));two['constraints'].append('two');p1=self.engine.propose_spec('s1',one);p2=self.engine.propose_spec('s2',two)
        for change,p in [('s1',p1),('s2',p2)]:self.engine.authorize(p['engineering_scope'],'engineering','engineering-reviewer','agent');self.engine.authorize(p['acceptance_scope'],'release','release-owner','operator')
        self.engine.apply_spec('s1')
        with self.assertRaises(PermissionError):self.engine.apply_spec('s2')
if __name__=='__main__':unittest.main()
