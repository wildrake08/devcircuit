"""Application-centered DevCircuit interface that keeps control-plane mechanics internal."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import uuid
import re
from pathlib import Path

from .autonomy import AutonomousLoop
from .guided_operator import GuidedOperator
from .intake import AUTHORITY_ROLES
from .project import PROFILES,create_project, migrate_project
from .store import read, write


PRINCIPALS=("owner","engineering-reviewer","release-owner")


class DeveloperExperience:
    def __init__(self,root):
        self.root=Path(root).resolve();self.operator=GuidedOperator(self.root);self.store=self.operator.store
        self.session_path=self.store.state/'operator/local-sessions.json'

    def authenticate_local_authorities(self,ttl=28800):
        sessions={}
        for principal in PRINCIPALS:
            key=self.store.state/'keys'/(principal+'.key')
            if not key.is_file():raise FileNotFoundError('local authority credential is missing: '+principal)
            sessions[principal]=self.operator.open_session(principal,key.read_text(),ttl)
        write(self.session_path,{"format":"DevCircuit-local-session-vault/v1","sessions":sessions,"created_at":int(time.time())});os.chmod(self.session_path,0o600)
        return {"authenticated":list(PRINCIPALS),"tokens_exposed":False,"expires_at":min(x['expires_at'] for x in sessions.values())}

    def _sessions(self):
        if not self.session_path.exists():
            self.authenticate_local_authorities()
        value=read(self.session_path);sessions=value['sessions']
        if min(item['expires_at'] for item in sessions.values())<int(time.time()):
            self.authenticate_local_authorities();sessions=read(self.session_path)['sessions']
        return sessions

    def _session(self,principal):
        value=self._sessions()[principal];return value['session_id'],value['token']

    def status(self):
        view=self.operator.status();return {"headline":view['headline'],"current_step":view['current_step'],"progress":view['progress'],"next":view['next'],"questions":view.get('intake',{}).get('questions',[]) if view.get('intake') else [],"authority_requests":view['authorization_requests'],"evidence":view['evidence']}

    def answer(self,answers):return self.operator.answer(answers)

    def _driver(self,requested=None):
        loop=AutonomousLoop(self.root);drivers=self.store.state/'drivers'
        if requested and (drivers/(requested+'.json')).exists():return requested
        if requested and requested not in ('codex','claude'):raise ValueError('requested driver is not registered: '+requested)
        candidates=[requested] if requested else ['codex','claude']
        for name in candidates:
            executable=shutil.which(name)
            if not executable:continue
            if (drivers/(name+'.json')).exists():return name
            if name=='codex':loop.register_driver(name,'generic',[executable,'exec','--sandbox','read-only','--ephemeral','--skip-git-repo-check','--output-schema','{schema}','--output-last-message','{output}','{prompt}'])
            else:loop.register_driver(name,'generic',[executable,'-p','{prompt}','--output-format','text'])
            return name
        raise RuntimeError('no supported coding agent was found; install Codex or Claude Code, or register an organization driver')

    def request_slice(self,objective,driver=None):
        if not isinstance(objective,str) or not objective.strip():raise ValueError('describe the application slice to build')
        workflow=self.operator._workflow()
        if not workflow or not self.operator._baseline_authorized(workflow):return {"state":"needs_product_baseline","message":"Complete and authorize the product baseline before engineering.","status":self.status()}
        driver=self._driver(driver);_,spec,_=self.operator.engine._spec();run_id='slice-'+time.strftime('%Y%m%d-%H%M%S',time.gmtime())+'-'+uuid.uuid4().hex[:6]
        mandate={"run_id":run_id,"objective":objective.strip(),"driver":driver,"allowed_paths":sorted(set(spec['components']+['tests/*'])),"requirements":[item['key'] for item in spec['requirements']],"max_iterations":6,"max_changes":16,"max_bytes":100000,"expires_at":int(time.time())+86400}
        session,token=self._session('engineering-reviewer');proposal=self.operator.propose_mandate(session,token,mandate)
        return {"state":"awaiting_engineering_authority","run_id":run_id,"summary":proposal['summary'],"decision_id":proposal['decision_id'],"review":"Run `devcircuit review`, then explicitly approve or reject."}

    def review(self):
        def summary(item):
            evidence=item.get('evidence',{})
            if 'product_baseline' in evidence:
                baseline=evidence['product_baseline'];return {'purpose':baseline.get('purpose'),'beneficiaries':baseline.get('beneficiaries'),'outcome':baseline.get('outcome_hypothesis'),'operating_conditions':baseline.get('operating_conditions')}
            if 'trial' in evidence:
                trial=evidence['trial'];return {'tests_passed':trial.get('passed'),'test_transcript':trial.get('transcript')}
            if 'artifact' in evidence:
                artifact=evidence['artifact'];return {'tests_passed':artifact.get('test_exit_code')==0,'test_transcript':artifact.get('test_transcript')}
            if isinstance(evidence,dict) and 'objective' in evidence:return {key:evidence.get(key) for key in ('objective','driver','allowed_paths','requirements','max_iterations','max_changes','max_bytes')}
            return {'purpose':item.get('summary')}
        packets=[]
        for principal in PRINCIPALS:
            session,token=self._session(principal)
            try:packet=self.operator.prepare_authorizations(session,token)
            except ValueError:continue
            packets.append({"principal":principal,"items":[{"decision_id":item['decision_id'],"summary":item['summary'],"evidence":summary(item)} for item in packet['items']]})
        proposals=[]
        folder=self.store.state/'copilot/decisions'
        for path in sorted(folder.glob('*.json')) if folder.exists() else []:
            pointer=read(path)
            if pointer.get('status')!='proposed':continue
            proposal=self.store.get(pointer['proposal_record'],'copilot_decision_proposal','agent')['payload']
            if proposal['kind']!='authorization':
                display={'summary':proposal['summary'],'evidence':proposal['payload']};proposals.append({"principal":proposal['required_principal'],"items":[{"decision_id":proposal['decision_id'],"summary":proposal['summary'],"evidence":summary(display)}]})
        return {"status":"awaiting_explicit_decisions" if packets or proposals else "nothing_to_decide","reviews":proposals+packets,"instruction":"Use `devcircuit approve DECISION_ID` or `devcircuit reject DECISION_ID --reason ...`. No digest copying is required."}

    def decide(self,decision_id,outcome,reason=None):
        if decision_id=='next':
            folder=self.store.state/'copilot/decisions';pending=[]
            for candidate in sorted(folder.glob('*.json')) if folder.exists() else []:
                if read(candidate).get('status')=='proposed':pending.append(candidate.stem)
            if len(pending)!=1:raise ValueError('`next` requires exactly one pending decision; run `devcircuit review`')
            decision_id=pending[0]
        path=self.store.state/'copilot/decisions'/(decision_id+'.json');pointer=read(path);proposal=self.store.get(pointer['proposal_record'],'copilot_decision_proposal','agent')['payload'];principal=proposal['required_principal'];session,token=self._session(principal);confirmation=proposal['challenge'] if outcome=='approve' else proposal['reject_challenge'];result=self.operator.decide(session,token,decision_id,outcome,confirmation,reason)
        resumed=None
        if outcome=='approve':
            runs=self.operator.copilot.status()['runs']
            run_id=(result.get('effect') or {}).get('run_id') or (runs[-1]['run_id'] if runs else None)
            if run_id:
                try:resumed=self.operator.continue_run(session,token,run_id)
                except (PermissionError,RuntimeError,ValueError) as exc:resumed={"state":"requires_attention","message":str(exc)}
        return {"decision":{"decision_id":decision_id,"outcome":outcome,"effect_applied":result.get('effect') is not None},"automatic_continuation":resumed,"status":self.status()}

    def continue_active(self):
        runs=self.operator.copilot.status()['runs']
        if not runs:return {"state":"idle","message":"Describe the next application slice."}
        session,token=self._session('engineering-reviewer');return self.operator.continue_run(session,token,runs[-1]['run_id'])

    def close_production(self,bundle,trusted_public_key):
        self._session('release-owner')
        result=self.operator.engine.close_production(bundle,trusted_public_key)
        runs=self.operator.copilot.status()['runs']
        if runs:
            path=self.store.state/'autonomy-runs'/(runs[-1]['run_id']+'.json');state=read(path);state.update({'phase':'complete','result':result,'pending':read(self.store.state/'pending.json')});write(path,state)
        return {"state":"cycle_closed","verification":result,"monitoring":"continuous change-triggered reassessment remains active"}

    @staticmethod
    def _plain_intake_answer(question,message):
        group=question['id'].split('-',1)[-1];lower=message.lower().strip()
        if group=='outcome':
            numbers=[float(value) for value in re.findall(r'\b\d+(?:\.\d+)?\b',lower)]
            if len(numbers)<2:return None
            if any(term in lower for term in ('no more than','at most','under','below','less than')):operator='<='
            elif any(term in lower for term in ('at least','no less than','minimum','or more')):operator='>='
            else:return None
            unit=next((item for item in ('seconds','minutes','milliseconds','percent','ratio','count') if item in lower),None)
            if not unit:return None
            prefix=re.split(r'\b(?:should|must|at most|at least|under|below|no more than|no less than)\b',lower,maxsplit=1)[0]
            metric=re.sub(r'[^a-z0-9]+','_',prefix).strip('_') or 'outcome'
            if unit in ('seconds','minutes','milliseconds') and not metric.endswith('_'+unit):metric+='_'+unit
            return {'outcome_statement':message.strip(),'outcome_metric':metric,'outcome_unit':unit,'outcome_operator':operator,'outcome_target':numbers[0],'outcome_baseline':numbers[1]}
        if group=='risk':
            if lower in ('none','none identified','no sensitive data'):return {'data_classes':['none identified'],'compliance_obligations':['none identified']}
            classes=[];obligations=[]
            if 'payment' in lower or 'card' in lower:classes.append('payment token and transaction data');obligations.append('payment-provider and card-data obligations')
            if 'personal' in lower or 'customer' in lower:classes.append('personal data')
            if 'health' in lower:classes.append('health data');obligations.append('health-data obligations')
            return {'data_classes':classes or [message.strip()],'compliance_obligations':obligations or ['review stated data obligations']}
        if group=='conditions':return {'operating_conditions':{'description':message.strip()}}
        if group=='authority':
            authority='project owner' if any(term in lower for term in ('me','myself','same owner','project owner','i am')) else message.strip()
            return {'authorities':{role:authority for role in AUTHORITY_ROLES}}
        return None

    def converse(self,message=None,answers=None,driver=None):
        if answers:return {"response":"I recorded the requested product facts. No authority was inferred.","view":self.answer(answers)}
        text=(message or '').strip()
        match=re.fullmatch(r'approve(?:\s+([0-9a-f-]+|next))?',text,re.I)
        if match:
            if not match.group(1):return {"response":"Approval is never inferred. Say `approve next` after reviewing the single pending decision.","review":self.review(),"authoritative":False}
            return {"response":"I applied the explicit authenticated approval and continued automatically.","result":self.decide(match.group(1),'approve'),"authoritative":True}
        match=re.fullmatch(r'reject\s+([0-9a-f-]+|next)\s*:\s*(.+)',text,re.I)
        if match:return {"response":"I recorded the explicit rejection and stopped or returned the affected work for revision.","result":self.decide(match.group(1),'reject',match.group(2)),"authoritative":True}
        view=self.status()
        if view['questions']:
            if text.startswith('{'):
                return {"response":"I recorded the requested product facts. No authority was inferred.","view":self.answer(json.loads(text)),"authoritative":False}
            if text and text.lower() not in ('status','next','help'):
                parsed=self._plain_intake_answer(view['questions'][0],text)
                if parsed:
                    updated=self.answer(parsed);remaining=updated['intake']['questions']
                    return {"response":"I recorded that as non-authoritative product input."+(" One material question remains next." if remaining else " The product baseline is ready for review."),"questions":remaining[:1],"authoritative":False}
            return {"response":"I understand the project direction. I will ask one material question at a time before proposing its product baseline.","questions":view['questions'][:1],"authoritative":False}
        if view['authority_requests']:
            return {"response":"A human decision is required. I prepared the review without granting authority.","review":self.review(),"authoritative":False}
        if message and message.strip().lower() not in ('status','next','help'):
            return {"response":"I prepared a bounded engineering proposal from your request.","proposal":self.request_slice(message,driver),"authoritative":False}
        return {"response":view['headline'],"view":view,"authoritative":False}


def _print(value):print(json.dumps(value,indent=2));return 0


def main():
    parser=argparse.ArgumentParser(prog='devcircuit',description='Create an application, describe what to build, and let DevCircuit operate the governed lifecycle')
    parser.add_argument('--root',default='.')
    sub=parser.add_subparsers(dest='command')
    item=sub.add_parser('create');item.add_argument('name');item.add_argument('--purpose');item.add_argument('--beneficiary',default='users');item.add_argument('--profile',default='python-service',choices=sorted(PROFILES))
    sub.add_parser('auth-local');sub.add_parser('status');sub.add_parser('review');sub.add_parser('run')
    item=sub.add_parser('answer');item.add_argument('--file',required=True)
    item=sub.add_parser('build');item.add_argument('request');item.add_argument('--driver')
    item=sub.add_parser('chat');item.add_argument('--message');item.add_argument('--answers');item.add_argument('--driver')
    item=sub.add_parser('approve');item.add_argument('decision_id')
    item=sub.add_parser('reject');item.add_argument('decision_id');item.add_argument('--reason',required=True)
    item=sub.add_parser('migrate');item.add_argument('--apply',action='store_true')
    item=sub.add_parser('close');item.add_argument('--evidence',required=True);item.add_argument('--trusted-public-key',required=True)
    args=parser.parse_args();command=args.command or 'chat'
    try:
        if command=='create':return _print(create_project(args.root,args.name,args.purpose,args.beneficiary,args.profile))
        if command=='migrate':return _print(migrate_project(args.root,args.apply))
        experience=DeveloperExperience(args.root)
        if command=='auth-local':result=experience.authenticate_local_authorities()
        elif command=='status':result=experience.status()
        elif command=='review':result=experience.review()
        elif command=='answer':result=experience.answer(json.loads(Path(args.file).read_text()))
        elif command=='build':result=experience.request_slice(args.request,args.driver)
        elif command=='approve':result=experience.decide(args.decision_id,'approve')
        elif command=='reject':result=experience.decide(args.decision_id,'reject',args.reason)
        elif command=='run':result=experience.continue_active()
        elif command=='close':result=experience.close_production(json.loads(Path(args.evidence).read_text()),Path(args.trusted_public_key))
        else:
            answer_value=json.loads(Path(args.answers).read_text()) if args.answers else None
            if args.message is not None:return _print(experience.converse(args.message,answer_value,args.driver))
            if not sys.stdin.isatty():return _print(experience.converse('status'))
            print('DevCircuit is ready. Describe what you want to build; type status or quit.')
            while True:
                try:message=input('devcircuit> ').strip()
                except EOFError:break
                if message.lower() in ('quit','exit'):break
                print(json.dumps(experience.converse(message),indent=2))
            return 0
        return _print(result)
    except (ValueError,PermissionError,RuntimeError,FileNotFoundError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({'error':str(exc)}),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
