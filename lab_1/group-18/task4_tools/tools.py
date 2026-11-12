"""Validated, bounded tools for the Task 4 debugging agent."""

from __future__ import annotations

import difflib
import fnmatch
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tool_contract import (
    DEFAULT_TIMEOUT_S,
    MAX_LIST_ENTRIES,
    MAX_OUTPUT_CHARS,
    MAX_READ_LINES,
    MAX_SEARCH_RESULTS,
    ToolRegistryBase,
    ToolResult,
)


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties,
                       "required": required, "additionalProperties": False},
    }}


class ToolRegistry(ToolRegistryBase):
    def __init__(self, workspace: Path, timeout_s: float = DEFAULT_TIMEOUT_S,
                 log_path: Path | None = None) -> None:
        super().__init__(Path(workspace).resolve(), timeout_s)
        self.log_path = Path(log_path) if log_path else Path("/tmp/task4_registry_trace.jsonl")
        self._specs = {
            "list_files": _tool("list_files", "List workspace files under a relative directory; results are capped.", {
                "path": {"type": "string", "default": "."}, "pattern": {"type": "string"}}, []),
            "read_file": _tool("read_file", "Read numbered lines from a workspace file (at most 200 lines).", {
                "path": {"type": "string"}, "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1}}, ["path"]),
            "search_code": _tool("search_code", "Search workspace files using a regular expression.", {
                "pattern": {"type": "string"}, "glob": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_SEARCH_RESULTS}}, ["pattern"]),
            "run_tests": _tool("run_tests", "Run pytest in the workspace and return a structured test summary.", {
                "target": {"type": "string"}}, []),
            "edit_file": _tool("edit_file", "Replace one unique exact text match in an existing file below src/.", {
                "path": {"type": "string"}, "old_str": {"type": "string", "minLength": 1},
                "new_str": {"type": "string"}}, ["path", "old_str", "new_str"]),
            "run_cli": _tool("run_cli", "Run tinyledger report, balances, or settle with workspace data.", {
                "args": {"type": "array", "items": {"type": "string"}, "maxItems": 12}}, ["args"]),
        }

    def schemas(self) -> list[dict]:
        return list(self._specs.values())

    def _path(self, value: str) -> Path:
        if not value or "\x00" in value:
            raise ValueError("path must be a non-empty relative workspace path")
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("path must stay inside the workspace")
        resolved = (self.workspace / candidate).resolve()
        if not resolved.is_relative_to(self.workspace):
            raise ValueError("path resolves outside the workspace")
        return resolved

    def _run(self, command: list[str]) -> tuple[int, str, str, bool]:
        env = {"PATH": os.defpath, "PYTHONPATH": "src", "PYTHONDONTWRITEBYTECODE": "1",
               "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
        if os.name == "nt":
            env.update({k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR") if k in os.environ})
        process = subprocess.Popen(command, cwd=self.workspace, env=env, shell=False,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=(os.name != "nt"))
        chunks: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
        truncated = [False]

        def drain(name: str, stream) -> None:
            while True:
                data = stream.read(8192)
                if not data:
                    break
                room = MAX_OUTPUT_CHARS - len(chunks[name])
                if room > 0:
                    chunks[name].extend(data[:room])
                if len(data) > room:
                    truncated[0] = True

        readers = [threading.Thread(target=drain, args=(name, stream), daemon=True)
                   for name, stream in (("stdout", process.stdout), ("stderr", process.stderr))]
        for thread in readers:
            thread.start()
        try:
            code = process.wait(timeout=self.timeout_s)
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            process.wait()
            code = -signal.SIGKILL
            chunks["stderr"].extend(b"\nProcess timed out.")
        for thread in readers:
            thread.join()
        decode = lambda b: bytes(b).decode("utf-8", errors="replace")
        return code, decode(chunks["stdout"]), decode(chunks["stderr"]), truncated[0]

    def _call(self, name: str, args: dict[str, Any]) -> tuple[ToolResult, bool]:
        if name == "list_files":
            root = self._path(args.get("path", "."))
            if not root.is_dir():
                raise ValueError("path is not a directory")
            pattern = args.get("pattern", "*")
            found = []
            for path in sorted(root.rglob("*")):
                if path.is_symlink():
                    continue
                if path.is_file() and fnmatch.fnmatch(path.name, pattern):
                    if path.resolve().is_relative_to(self.workspace):
                        found.append(path.relative_to(self.workspace).as_posix())
                if len(found) > MAX_LIST_ENTRIES:
                    break
            clipped = len(found) > MAX_LIST_ENTRIES
            return ToolResult(True, found[:MAX_LIST_ENTRIES], truncated=clipped), clipped

        if name == "read_file":
            path = self._path(args["path"])
            if not path.is_file():
                raise ValueError("path is not a file")
            start = args.get("start_line", 1)
            end = args.get("end_line")
            if end is not None and end < start:
                raise ValueError("end_line must be greater than or equal to start_line")
            requested_end = end if end is not None else start + MAX_READ_LINES - 1
            end = min(requested_end, start + MAX_READ_LINES - 1)
            output = []
            cut = requested_end > end
            with path.open(encoding="utf-8", errors="replace") as stream:
                for number, line in enumerate(stream, 1):
                    if number < start:
                        continue
                    if number > end:
                        cut = args.get("end_line") is None or args["end_line"] > end
                        break
                    rendered = f"{number}: {line.rstrip()}"
                    if sum(map(len, output)) + len(rendered) > MAX_OUTPUT_CHARS - 256:
                        cut = True
                        break
                    output.append(rendered)
            return ToolResult(True, "\n".join(output), truncated=cut), cut

        if name == "search_code":
            regex = re.compile(args["pattern"])
            limit = min(args.get("max_results", MAX_SEARCH_RESULTS), MAX_SEARCH_RESULTS)
            glob = args.get("glob", "**/*")
            matches = []
            for path in sorted(self.workspace.glob(glob)):
                if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(self.workspace):
                    continue
                try:
                    with path.open(encoding="utf-8", errors="replace") as stream:
                        for number, line in enumerate(stream, 1):
                            if regex.search(line):
                                matches.append(f"{path.relative_to(self.workspace).as_posix()}:{number}: {line.rstrip()}")
                                if len(matches) > limit:
                                    return ToolResult(True, "\n".join(matches[:limit]), truncated=True), True
                except (OSError, UnicodeError):
                    continue
            return ToolResult(True, "\n".join(matches)), False

        if name == "run_tests":
            target = args.get("target")
            command = [sys.executable, "-m", "pytest", "-q", "--tb=short"]
            if target:
                if not isinstance(target, str) or target.startswith(("-", "/")) or ".." in Path(target).parts:
                    raise ValueError("target must be a workspace pytest path or node id")
                target_path = target.split("::", 1)[0]
                if not target_path.startswith("tests/") or not self._path(target_path).is_file():
                    raise ValueError("target must name an existing test under tests/")
                command.append(target)
            code, stdout, stderr, cut = self._run(command)
            text = (stdout + "\n" + stderr)[-MAX_OUTPUT_CHARS:]
            passed = re.search(r"(\d+) passed", text)
            failed = re.search(r"(\d+) failed", text)
            failures = re.findall(r"(?:FAILED|ERROR)\s+([^\s]+)", text)
            traces = []
            for block in re.findall(r"_{3,} .*?_{3,}\n(.*?)(?=\n_{3,} |\n=+ short test summary|\Z)", text, re.S):
                traces.append(block[-700:].strip())
            output = {"passed": int(passed.group(1)) if passed else 0,
                      "failed": int(failed.group(1)) if failed else (1 if code else 0),
                      "failing_tests": failures[:30], "tracebacks": traces[:5], "exit_code": code}
            return ToolResult(True, output, truncated=cut), cut

        if name == "run_cli":
            values = args["args"]
            if not values or values[0] not in {"report", "balances", "settle"}:
                raise ValueError("first argument must be report, balances, or settle")
            if len(values) < 2:
                raise ValueError("a CSV file path inside the workspace is required")
            csv_path = self._path(values[1])
            if not csv_path.is_file():
                raise ValueError("CSV path must name an existing workspace file")
            values = list(values)
            values[1] = csv_path.relative_to(self.workspace).as_posix()
            code, stdout, stderr, cut = self._run([sys.executable, "-m", "tinyledger", *values])
            return ToolResult(code == 0, {"exit_code": code, "stdout": stdout, "stderr": stderr},
                              None if code == 0 else "CLI returned a non-zero exit code", cut), cut

        if name == "edit_file":
            path = self._path(args["path"])
            src = (self.workspace / "src").resolve()
            if not path.is_relative_to(src) or path.is_symlink() or not path.is_file():
                raise ValueError("edit_file only changes existing regular files below src/")
            if len(args["old_str"]) + len(args["new_str"]) > MAX_OUTPUT_CHARS:
                raise ValueError("replacement text exceeds the tool limit")
            original = path.read_text(encoding="utf-8")
            if original.count(args["old_str"]) != 1:
                raise ValueError("old_str must match exactly once")
            updated = original.replace(args["old_str"], args["new_str"], 1)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                                 prefix=f".{path.name}.", delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(updated)
                os.replace(temporary, path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            diff = "".join(difflib.unified_diff(
                original.splitlines(keepends=True), updated.splitlines(keepends=True),
                fromfile=f"a/{path.relative_to(self.workspace).as_posix()}",
                tofile=f"b/{path.relative_to(self.workspace).as_posix()}",
            ))
            return ToolResult(True, diff), False

        raise ValueError(f"Unknown tool: {name}")

    def execute(self, name: str, arguments: str) -> ToolResult:
        started = time.monotonic()
        result = ToolResult(False, error="Invalid tool call")
        try:
            if name not in self._specs:
                raise ValueError(f"Unknown tool: {name}")
            parsed = json.loads(arguments)
            if not isinstance(parsed, dict):
                raise ValueError("arguments must be a JSON object")
            errors = sorted(Draft202012Validator(self._specs[name]["function"]["parameters"]).iter_errors(parsed),
                            key=lambda e: list(map(str, e.absolute_path)))
            if errors:
                error = errors[0]
                field = ".".join(map(str, error.absolute_path)) or "arguments"
                raise ValueError(f"Invalid {field}: {error.message}")
            result, _ = self._call(name, parsed)
        except Exception as exc:
            result = ToolResult(False, error=f"{type(exc).__name__}: {str(exc)[:500]}")
        payload = result.to_content()
        if len(payload) > MAX_OUTPUT_CHARS:
            content = result.output if isinstance(result.output, str) else json.dumps(result.output, ensure_ascii=False)
            result.output = content[:MAX_OUTPUT_CHARS - 512]
            result.truncated = True
            while len(result.to_content()) > MAX_OUTPUT_CHARS:
                result.output = result.output[:-256]
        entry = {"name": name, "arguments": str(arguments)[:2000], "ok": result.ok,
                 "error": result.error, "truncated": result.truncated,
                 "duration": round(time.monotonic() - started, 4)}
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as log:
                log.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass
        return result
