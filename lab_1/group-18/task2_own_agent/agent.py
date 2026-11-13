"""Task 2: Custom JSON-action website coding agent (no native tool calling).

Run from the repository root:
    python lab_1/group-18/task2_own_agent/agent.py
"""

import json
import re
import sys
import base64
from datetime import datetime
from pathlib import Path
from io import BytesIO
from PIL import Image

from dotenv import load_dotenv

TASK_DIR = Path(__file__).resolve().parent
GROUP_DIR = TASK_DIR.parent
CONTENT_DIR = GROUP_DIR / "task1_opencode" / "content"
IMAGES_DIR = CONTENT_DIR / "images"
SITE_PATH = TASK_DIR / "site" / "index.html"
LOG_DIR = TASK_DIR / "logs"

sys.path.insert(0, str(GROUP_DIR))
load_dotenv(GROUP_DIR / ".env")

from common.llm_client import LLMClient  # noqa: E402
from common.site_checker import check_site  # noqa: E402
from common.embed_images import image_to_data_uri  # noqa: E402
from rag import search  # noqa: E402

CHAT_MODEL = "openai.gpt-6-luna"
MAX_STEPS = 15
MAX_INITIAL_SEARCHES = 5
MAX_REVISION_SEARCHES = 2
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

SYSTEM_PROMPT = """You are a custom autonomous coding agent building a team website.

Return exactly ONE valid JSON object, with no code fences or extra prose.
You have four actions (these are JSON actions, NOT native tool calls):
  {"action":"read_profiles"}
  {"action":"search_style_guide","query":"specific design question","k":3}
  {"action":"write_site","html":"<!DOCTYPE html>...complete HTML..."}
  {"action":"finish","message":"Website completed"}

Workflow:
- Read profiles once. Use ALL their real information; do not invent details.
- Retrieve style rules through search_style_guide. Prefer ACTIVE over DEPRECATED.
- Search at most five times before your first write_site action.
- Then WRITE the COMPLETE website, not a placeholder or shortened example.
- After checker failures, search at most twice for the missing rules and REWRITE
  the complete HTML. Your next action after those searches must be write_site.
- Call finish ONLY when the full checker passes.

HTML requirements:
- Single-file HTML with inline CSS/JS; responsive, accessible, day/night theme.
- Exactly one member card and one <img> per provided profile.
- The image path must be EXACTLY images/<photo> from the read_profiles result.
  Do not change the file extension (.jpg, .jpeg, .png, or .webp).
- Include each member's hot take, and use style-guide rules for layout, color,
  typography, theme behavior, sections, and footer.
- write_site automatically embeds the referenced local images as data URIs.
- Correct failed checks using the returned validation feedback. Do not repeatedly
  search the same topic or restart the task.
- Never call native function/tool calling or use an agent framework.
"""


def get_profiles():
    """Read team profiles and match images by filename stem."""
    if not CONTENT_DIR.is_dir():
        raise FileNotFoundError(f"Missing content folder: {CONTENT_DIR}")

    images = sorted(
        (p for p in IMAGES_DIR.iterdir()
         if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES),
        key=lambda p: p.name.lower(),
    ) if IMAGES_DIR.is_dir() else []

    profiles = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        markdown = path.read_text(encoding="utf-8-sig")
        if not markdown.strip():
            continue
        photo = next(
            (p.name for p in images if p.stem.lower() == path.stem.lower()),
            None,
        )
        heading = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        profiles.append({
            "file": path.name,
            "name": heading.group(1).strip() if heading else path.stem.capitalize(),
            "photo": photo,
            "markdown": markdown,
        })
    return profiles

def optimized_image_data_uri(image_path):
    """Compress images before embedding without modifying originals."""

    with Image.open(image_path) as image:
        image = image.convert("RGB")
        image.thumbnail((400, 400))

        buffer = BytesIO()
        image.save(
            buffer,
            format="JPEG",
            quality=80,
            optimize=True
        )

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def embed_site_images(html):
    """Replace quoted local <img src> paths with data URIs."""
    pattern = re.compile(
        r'''(\bsrc\s*=\s*)(["'])(?:\./)?(?:images/)?([^"'<>/\\]+\.(?:jpg|jpeg|png|webp))\2''',
        re.IGNORECASE,
    )

    def replace(match):
        image_path = IMAGES_DIR / match.group(3)
        if not image_path.is_file():
            return match.group(0)
        uri = optimized_image_data_uri(image_path)
        quote = match.group(2)
        return f"{match.group(1)}{quote}{uri}{quote}"

    return pattern.sub(replace, html)


def parse_action(response):
    """Read exactly one JSON action, tolerating a single fenced JSON block."""
    text = response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()

    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON ({exc.msg} at position {exc.pos}). "
            "Reply again with ONE JSON object only."
        ) from exc

    if not isinstance(obj, dict) or not isinstance(obj.get("action"), str):
        raise ValueError("Response must be a JSON object with an 'action' string.")
    return obj


def execute_action(action, state):
    """Execute one of the four actions and return a serializable observation."""
    name = action["action"]

    if name == "read_profiles":
        profiles = get_profiles()
        if not profiles:
            return {"error": "No member Markdown profiles found."}
        state["profiles_read"] = True
        return {"count": len(profiles), "profiles": profiles}

    if name == "search_style_guide":
        query = action.get("query")
        if not isinstance(query, str) or not query.strip():
            return {"error": "Provide a nonempty search query."}
        try:
            k = max(1, min(5, int(action.get("k", 3))))
        except (ValueError, TypeError):
            return {"error": "k must be an integer."}

        limit = MAX_REVISION_SEARCHES if state["site_written"] else MAX_INITIAL_SEARCHES
        if state["search_count"] >= limit:
            return {
                "error": "Search limit reached. Your NEXT action must be write_site. "
                         "Use the rules and checker feedback already provided."
            }
        results = search(query, k=k)
        state["search_count"] += 1
        state["guide_searched"] = True
        return {"results": results}

    if name == "write_site":
        if not (state["profiles_read"] and state["guide_searched"]):
            return {"error": "Call read_profiles and search_style_guide first."}

        html = action.get("html")
        if not isinstance(html, str) or not re.search(r"<html\b", html, re.I):
            return {"error": "Supply a complete HTML document in the html field."}

        profiles = get_profiles()
        if not profiles:
            return {"error": "There are no profiles to render."}

        # Validate actual src attributes before writing anything to disk.
        srcs = re.findall(r'''\bsrc\s*=\s*["']([^"']+)["']''', html, re.I)
        for profile in profiles:
            photo = profile["photo"]
            if photo is None:
                return {"error": f"No local photo exists for {profile['name']}."}
            expected = f"images/{photo}"
            if expected not in srcs:
                return {"error": (
                    f"Missing or incorrect photo for {profile['name']}. "
                    f"Include <img src=\"{expected}\" alt=\"...\"> exactly. "
                    f"The image must use its original filename."
                )}

        embedded_html = embed_site_images(html)
        if re.search(r'''\bsrc\s*=\s*["'](?:\./)?images/''', embedded_html, re.I):
            return {"error": "At least one local image was not embedded. Verify the filename."}

        # Check before saving; preserve the last existing file if an attempt fails
        # preliminary validation. Save fully generated candidates for inspection.
        SITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SITE_PATH.write_text(embedded_html, encoding="utf-8")
        report = check_site(
            embedded_html,
            mode="full",
            member_names=[p["name"] for p in profiles],
            file_size=SITE_PATH.stat().st_size,
        )
        state["site_written"] = True
        state["checks_passed"] = report.passed
        state["search_count"] = 0  # Allow two targeted RAG searches per revision.
        print("\nWebsite checker:\n" + report.summary())
        failures = [{"name": r.name, "message": r.message} for r in report.failures()]
        return {
            "saved_to": str(SITE_PATH),
            "passed": report.passed,
            "summary": f"{len(report.results) - len(failures)}/{len(report.results)} checks passed",
            "failures": failures,
        }

    if name == "finish":
        if not state["checks_passed"] or not state["site_written"]:
            return {"error": "Cannot finish until the full website checker passes."}
        state["finished"] = True
        return {"success": True, "message": str(action.get("message", "Done"))}

    return {"error": f"Unknown action: {name}"}


def run_agent():
    """Run the custom LLM -> JSON action -> observation loop."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_log = LOG_DIR / f"agent_run_{timestamp}.jsonl"
    llm = LLMClient(
        model=CHAT_MODEL,
        log_path=LOG_DIR / f"agent_llm_{timestamp}.jsonl",
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            "Build and validate the complete team website using available "
            "profiles and retrieved style-guide rules. Start with read_profiles."
        )},
    ]
    state = {
        "profiles_read": False,
        "guide_searched": False,
        "site_written": False,
        "checks_passed": False,
        "finished": False,
        "search_count": 0,
    }

    step = 0
    total_steps = 0
    while not state["finished"]:
        if step >= MAX_STEPS:
            print(f"\nReached the limit of {MAX_STEPS} steps.")
            try:
                feedback = input("Enter feedback to continue, or type 'stop': ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if feedback.lower() in {"", "stop", "quit", "exit"}:
                break
            messages.append({"role": "user", "content": "Human feedback: " + feedback})
            step = 0
            continue

        step += 1
        total_steps += 1
        print(f"\n--- Agent step {total_steps} ---")
        try:
            response = llm.chat(messages, model=CHAT_MODEL, max_tokens=16384)
        except Exception as exc:
            print(f"Gateway error: {exc}")
            break

        action = {}
        try:
            action = parse_action(response)
            print("Action:", action["action"])
            observation = execute_action(action, state)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            observation = {"error": str(exc)}
            print("Action error:", exc)

        # Store full responses in the local run log, but not huge base64 data URIs.
        with run_log.open("a", encoding="utf-8") as output:
            output.write(json.dumps({
                "step": total_steps,
                "action": action.get("action", "invalid_json"),
                "response": response,
                "observation": observation,
            }, ensure_ascii=False) + "\n")

        if state["finished"]:
            print("\nAgent finished successfully!")
            break

        # The assistant message must remain in the conversation for coherent
        # JSON-action rounds. Compact older write_site actions to avoid context
        # growing with multiple complete HTML copies; the full record is logged.
        if action.get("action") == "write_site" and isinstance(action.get("html"), str):
            messages.append({
                "role": "assistant",
                "content": json.dumps({
                    "action": "write_site",
                    "html": "[complete HTML saved to site/index.html; see tool feedback]",
                }),
            })
        else:
            messages.append({"role": "assistant", "content": response[:30000]})

        feedback = json.dumps(observation, ensure_ascii=False)
        instruction = "Choose the next valid JSON action."
        if action.get("action") == "write_site" and observation.get("passed") is False:
            instruction = (
                "The checker failed. Search at most twice for missing rules, "
                "then return a corrected COMPLETE HTML in write_site. "
                "Do not repeat the previous errors."
            )
        elif observation.get("error"):
            instruction = "Correct the tool error. Return exactly one valid JSON action."
        elif action.get("action") == "write_site" and observation.get("passed"):
            instruction = "The full checker passed. Call finish now."

        # Always append observations. In the original code this was incorrectly
        # indented under the failed write_site branch, hiding search results.
        messages.append({
            "role": "user",
            "content": "Tool observation:\n" + feedback + "\n" + instruction,
        })

    print("\nRun log:", run_log)
    print("Usage:", llm.usage_summary())


if __name__ == "__main__":
    run_agent()
