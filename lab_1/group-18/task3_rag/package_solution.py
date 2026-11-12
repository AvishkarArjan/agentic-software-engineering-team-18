"""Create a standalone Task 3 archive; omit keys, caches and environments."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import zipfile

from dotenv import dotenv_values

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent


def main():
    output=ROOT.parent/'output/task3_team18.zip'
    output.parent.mkdir(parents=True,exist_ok=True)
    files=[p for p in HERE.rglob('*') if p.is_file() and
           not any(part in ('.cache','__pycache__','.pytest_cache') for part in p.relative_to(HERE).parts)
           and p.name not in ('.env',)]
    files += [ROOT/'common/__init__.py',ROOT/'common/llm_client.py',ROOT/'.env.example']
    source=[p for p in files if p.suffix=='.py' or 'data' in p.relative_to(ROOT).parts]
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'platform':platform.platform(),
        'configuration':json.loads((HERE/'results/best.json').read_text(encoding='utf-8')),
        'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source)},
        'excluded':['.env','.cache/','__pycache__/','.venv/','other lab tasks']}
    manifest_path=HERE/'results/reproducibility.json'
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    if manifest_path not in files:files.append(manifest_path)
    secret=dotenv_values(ROOT/'.env').get('UPB_AI_GATEWAY_KEY','')
    for path in files:
        if secret and secret.encode() in path.read_bytes():
            raise ValueError(f'Configured secret found in {path.relative_to(ROOT)}; refusing to package')
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files):archive.write(path,path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert 'task3_rag/predictions_test.jsonl' in archive.namelist()
        assert not any(n=='.env' or '/.cache/' in n or '/__pycache__/' in n for n in archive.namelist())
    print(f'Created {output} ({output.stat().st_size/1024/1024:.2f} MiB, {len(files)} files); configured key not present.')


if __name__=='__main__':main()
