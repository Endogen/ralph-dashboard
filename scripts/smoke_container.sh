#!/usr/bin/env bash
# Exercise the installed artifact, including its runner, without paid API calls.
set -euo pipefail
IMAGE="${1:-ralph-dashboard:reliability}"
docker run --rm -i --entrypoint python "$IMAGE" - <<'PY'
import json, os, pathlib, subprocess, sys, tempfile
from app.control.models import LoopConfig
from app.config import Settings
from pydantic import ValidationError
try:
    Settings()
except ValidationError:
    pass
else:
    raise AssertionError('Missing signing key was accepted')
for cli in ('codex', 'claude'):
    subprocess.run([cli, '--version'], check=True, timeout=20)
with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    (root / '.ralph').mkdir()
    (root / 'PROMPT.md').write_text('Container fixture')
    binary = root / 'fixture-agent'
    binary.write_text('#!/usr/local/bin/python\nimport pathlib,json\npathlib.Path("IMPLEMENTATION_PLAN.md").write_text("STATUS: COMPLETE\\n")\nprint(json.dumps({"type":"result","result":"Container runner works","usage":{"input_tokens":5,"output_tokens":2}}))\n')
    binary.chmod(0o755)
    (root / '.ralph/config.json').write_text(LoopConfig(cli=str(binary), max_iterations=1).model_dump_json())
    subprocess.run(['git','init'],cwd=root,check=True,capture_output=True)
    subprocess.run([sys.executable,'-m','app.runner'],cwd=root,check=True,timeout=20,start_new_session=True)
    record=json.loads((root / '.ralph/iterations.jsonl').read_text())
    assert record['status']=='success' and record['tokens']==0.007
    assert (root / '.ralph/ralph.log').read_text().count('Container runner works')==1
print('Packaged runner and installed CLIs passed')
PY
CONTAINER="ralph-smoke-$$"
trap 'docker rm -f "$CONTAINER" >/dev/null 2>&1 || true' EXIT
docker run -d --name "$CONTAINER" -p 127.0.0.1::8420 \
  -e RALPH_SECRET_KEY=container-smoke-test-only-key-with-32-characters "$IMAGE" >/dev/null
PORT="$(docker port "$CONTAINER" 8420/tcp | awk -F: '{print $NF}')"
for attempt in {1..30}; do
  if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null; then
    curl -fsS "http://127.0.0.1:$PORT/" >/dev/null
    echo "Container API and frontend passed"
    exit 0
  fi
  sleep 1
done
docker logs "$CONTAINER"
exit 1
