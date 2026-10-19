"""Application-centered project creation and safe legacy-template migration."""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from .engine import Engine
from .store import digest, read, write


def _identifier(value):
    value=re.sub(r"[^a-z0-9-]+","-",value.strip().lower()).strip("-")
    if not value:raise ValueError("project name must contain letters or numbers")
    return value


PROFILES={"python-service":"base-production","point-of-sale":"point-of-sale","web-saas":"saas","rest-api":"base-production","worker":"base-production"}


def _python_files(system_id,profile):
    feature={
        'python-service':'def application():\n    return {"service": "ready"}\n',
        'point-of-sale':'def catalog():\n    return {"products": []}\n',
        'web-saas':'def render_home():\n    return "<main>Application ready</main>"\n',
        'rest-api':'def route(path):\n    return ({"healthy": True}, 200) if path == "/health" else ({"error": "not_found"}, 404)\n',
        'worker':'def process(message):\n    return {"processed": True, "message": message}\n',
    }[profile]
    service='''"""Application entry point for %s."""\nimport argparse\nimport json\n\n\ndef health():\n    return {"healthy": True, "system": %r}\n\n\ndef main():\n    parser=argparse.ArgumentParser(prog=%r)\n    parser.add_argument("--self-test",action="store_true")\n    args=parser.parse_args()\n    result=health()\n    print(json.dumps(result))\n    return 0 if result["healthy"] else 1\n\n\nif __name__=="__main__":\n    raise SystemExit(main())\n''' % (system_id,system_id,system_id)
    service=service.replace('\n\ndef main():','\n\n'+feature+'\ndef main():')
    test='''import sys\nimport unittest\nfrom pathlib import Path\n\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))\nfrom service import health\n\n\nclass HealthTest(unittest.TestCase):\n    def test_application_is_healthy(self):\n        self.assertTrue(health()["healthy"])\n\n\nif __name__=="__main__":\n    unittest.main()\n'''
    return {'src/service.py':service,'tests/test_service.py':test}


def create_project(root,name,purpose=None,beneficiary="users",profile="python-service"):
    root=Path(root).resolve();system_id=_identifier(name)
    if profile not in PROFILES:raise ValueError("unknown application profile: "+profile)
    purpose=purpose or "Provide " + system_id.replace("-"," ")
    allow_starter=False
    if root.exists() and any(root.iterdir()):
        marker=root/'.devcircuit-template.json'
        if not marker.is_file():raise ValueError('target is not empty and is not a DevCircuit thin application starter')
        value=read(marker)
        if value!={"format":"DevCircuit-thin-starter/v1","kernel":"external","version":"1.0.0"}:raise ValueError('thin application starter marker is invalid')
        allowed={'.git','.github','.gitignore','README.md','.devcircuit-template.json'}
        unexpected={item.name for item in root.iterdir()}-allowed
        if unexpected:raise ValueError('thin starter contains unexpected top-level entries: '+','.join(sorted(unexpected)))
        allow_starter=True
    result=Engine(root).init(system_id=system_id,purpose=purpose,beneficiary=beneficiary,application_files=_python_files(system_id,profile),allow_thin_starter=allow_starter)
    metadata={"format":"DevCircuit-project/v2","system_id":system_id,"profile":profile,"kernel":{"package":"devcircuit","version":"1.0.0"},"created_at":int(time.time())}
    write(root/'.devcircuit/project.json',metadata)
    (root/'.github/workflows').mkdir(parents=True,exist_ok=True)
    (root/'.github/workflows/quality.yml').write_text('''name: quality\non: [push, pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.12"\n      - run: python -m unittest discover -s tests -v\n''')
    (root/'.gitignore').write_text('.venv/\n__pycache__/\n*.pyc\nbuild/\ndist/\n*.egg-info/\n.devcircuit/keys/\n.devcircuit/operator/local-sessions.json\n*.key\n*.pem\n*.p12\n*.pfx\n')
    (root/'pyproject.toml').write_text('[project]\nname = '+json.dumps(system_id)+'\nversion = "0.1.0"\nrequires-python = ">=3.10"\n\n[tool.devcircuit]\nprofile = '+json.dumps(profile)+'\n')
    (root/'README.md').write_text('# '+system_id+'\n\n'+purpose+'\n\n## Develop\n\nRun `devcircuit` and describe the next application slice.\n\n## Test\n\n```sh\npython -m unittest discover -s tests -v\n```\n')
    (root/'AGENTS.md').write_text('# Application engineering instructions\n\nFocus on this application. DevCircuit lifecycle state is managed under `.devcircuit/`; do not edit it directly.\n')
    marker=root/'.devcircuit-template.json'
    if marker.exists():marker.unlink()
    from .guided_operator import GuidedOperator
    from .discovery import discover_environment
    discovery=discover_environment(root);write(root/'.devcircuit/environment-discovery.json',discovery)
    lifecycle_profile=PROFILES[profile]
    view=GuidedOperator(root).begin(lifecycle_profile,{"facts":{"system_name":name,"system_id":system_id,"problem":purpose,"purpose":purpose,"beneficiaries":[beneficiary]}})
    return {**result,"root":str(root),"profile":profile,"experience":"ready_for_conversation","environment_discovered":True,"questions":view['intake']['questions'][:1],"next":"Run `devcircuit --root . chat`."}


LEGACY_FRAMEWORK_ROOTS={"clses_mvas_v1","kernel_tests","verification","examples","scripts","clses_general_assurance_kernel.egg-info","clses_platform.egg-info"}
FRAMEWORK_FILES={"ARCHITECTURE.md","AUTONOMY_PROTOCOL.md","CONFORMANCE_REPORT_4.6.0.md","CONFORMANCE_REPORT_4.6.1.md","CONFORMANCE_REPORT_4.6.2.md","CONFORMANCE_REPORT_4.6.3.md","COPILOT_GUIDE.md","GENERAL_ASSURANCE_GUIDE.md","GITHUB_TEMPLATE_GUIDE.md","MINIMAL_VIABILITY_INTAKE.md","NORMATIVE.md","ONBOARDING_AND_VISUAL_OPERATOR.md","OPERATOR_GUIDE.md","OUTCOME_ASSURANCE.md","PRECONFIGURED_PRODUCTION_ADAPTERS.md","PRODUCTION_PROFILE.md","SOFTWARE_QUALITY_PROFILE.md","UX_ENGINEERING_PROFILE.md","independent_verify.py","build.py"}


def migration_plan(root):
    root=Path(root).resolve();modern=root/'.devcircuit'
    if modern.exists():raise ValueError("project already uses the DevCircuit state directory")
    legacy_v5=root/'.clses';legacy_v4=root/'.clses-v1'
    source=legacy_v5 if legacy_v5.is_dir() else legacy_v4 if legacy_v4.is_dir() else None
    if source is None:raise ValueError("legacy CLSES state directory was not found")
    generation='external-kernel-v5' if source==legacy_v5 else 'embedded-template-v4'
    if generation=='external-kernel-v5':
        return {"format":"DevCircuit-migration-plan/v1","from":generation,"to":"devcircuit-1.0.0","state_move":{"from":source.name,"to":".devcircuit"},"remove":[],"preserve_conflicts":[],"preserve":[".git",".github/CODEOWNERS","src","tests"],"safe":True}
    manifest_path=root/'.clses-template/template-manifest.json'
    if not manifest_path.is_file():raise ValueError("signed CLSES legacy template manifest was not found")
    manifest=read(manifest_path);indexed={x['path']:x for x in manifest.get('entries',[])}
    removals=[];conflicts=[]
    candidates=[]
    for first in LEGACY_FRAMEWORK_ROOTS:
        path=root/first
        if path.exists():candidates.extend(x for x in path.rglob('*') if x.is_file() and not x.is_symlink())
    candidates.extend(root/name for name in FRAMEWORK_FILES if (root/name).is_file())
    for path in sorted(set(candidates)):
        relative=str(path.relative_to(root));expected=indexed.get(relative)
        if expected and expected.get('sha256')==digest(path.read_bytes()):removals.append(relative)
        else:conflicts.append(relative)
    return {"format":"DevCircuit-migration-plan/v1","from":generation,"to":"devcircuit-1.0.0","state_move":{"from":source.name,"to":".devcircuit"},"remove":removals,"preserve_conflicts":conflicts,"preserve":[".git",".github/CODEOWNERS","src","tests"],"safe":not conflicts}


def migrate_project(root,apply=False):
    root=Path(root).resolve();plan=migration_plan(root)
    if not apply:return {**plan,"applied":False}
    if not plan['safe']:raise ValueError("migration has modified framework-file conflicts; review the plan before applying")
    backup=root/'.devcircuit-migration-backup'
    if backup.exists():raise ValueError("migration backup already exists")
    source=root/plan['state_move']['from']
    shutil.copytree(source,backup)
    for relative in plan['remove']:(root/relative).unlink()
    if plan['from']=='embedded-template-v4':
        for first in LEGACY_FRAMEWORK_ROOTS:
            path=root/first
            if path.exists():shutil.rmtree(path)
    shutil.move(str(source),str(root/'.devcircuit'))
    write(root/'.devcircuit/migration.json',{**plan,"applied":True,"applied_at":int(time.time()),"backup":str(backup)})
    project={"format":"DevCircuit-project/v2","system_id":Engine(root)._spec()[1]['system_id'],"profile":"migrated","kernel":{"package":"devcircuit","version":"1.0.0"},"created_at":int(time.time())}
    write(root/'.devcircuit/project.json',project)
    return {**plan,"applied":True,"backup":str(backup),"next":"Run `devcircuit --root . status`."}
