# Task 4 – Tools for agents

The implementation is in `tools.py`; `agent.py` runs the tool-calling loop. The agent's
workspace is a disposable copy of the supplied `tinyledger` fixture.

```bash
python reset_workspace.py
python agent.py --mock
python agent.py
git -C workspace diff > final.diff
```

Every tool validates arguments against its JSON schema, returns bounded structured output,
logs calls in `logs/trace.jsonl`, and confines file access to the workspace. `edit_file`
only writes existing regular files below `src/`. Subprocesses use fixed Python module
commands, a minimal environment, captured bounded output, and a timeout.
