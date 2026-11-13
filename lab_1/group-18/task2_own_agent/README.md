# Task 2 – Own Coding Agent

## Overview

This project implements a Python agent that generates a single-file team website from member profiles and the supplied style guide. It uses a custom JSON action loop and RAG, without an agent framework or native tool calling.

## Requirements

- Python 3.11 or newer
- Dependencies from the lab's `requirements.txt`
- Pillow (`python -m pip install Pillow`)
- UPB AI Gateway access (university network or VPN)
- Gateway credentials in `lab_1/group-18/.env`

Do not commit the `.env` file.

## Run

Run these commands from the repository root:

1. Test style-guide retrieval:

   ```bash
   python lab_1/group-18/task2_own_agent/rag.py
   ```

2. Generate the website:

   ```bash
   python lab_1/group-18/task2_own_agent/agent.py
   ```

   If the 15-step limit is reached, enter feedback to continue or `stop` to end the run.

3. Validate the generated website:

   ```bash
   python lab_1/group-18/common/site_checker.py lab_1/group-18/task2_own_agent/site/index.html --full --content lab_1/group-18/task1_opencode/content
   ```

4. Open `lab_1/group-18/task2_own_agent/site/index.html` in a browser.

Agent logs are saved in `lab_1/group-18/task2_own_agent/logs/`.

## Implementation

**`rag.py`** loads 55 Markdown style-guide documents, splits them into chunks of up to 160 words with a 30-word overlap, and generates embeddings using `kiconnect.qwen3-embedding-8b`. It ranks chunks by cosine similarity and returns relevant text with source filenames and scores. The default retrieval count is three, the observation budget is 950 tokens, and document embeddings are cached locally.

**`agent.py`** uses `openai.gpt-6-luna` and supports four JSON actions:

- `read_profiles` — load member profiles and match their photos.
- `search_style_guide` — retrieve relevant style-guide rules.
- `write_site` — generate the HTML, embed images, and run the checker.
- `finish` — end the run only after all checks pass.

The program returns action results and checker failures to the model for the next decision. It handles invalid JSON, limits repeated style-guide searches, and requests human input at the 15-step limit. Older HTML responses are shortened in the active conversation to limit context growth.

Images are resized and compressed with Pillow before being embedded as Base64 data URIs. Original image files are not modified.

## Results

The latest run used all five member profiles and images. The website checker results across revisions were:

`19/25 → 19/25 → 20/25 → 20/25 → 23/25 → 24/25 → 25/25`

The final HTML was approximately 139 KB and passed all 25 checks. The agent finished after 26 model calls, including one human continuation at the step limit. The run also recovered from an invalid JSON response on its first step.

Run log: `logs/agent_run_20261113_133231.jsonl`

## Design Decisions and Limitations

- JSON actions keep execution under Python's control without an agent framework.
- RAG retrieves relevant rules rather than placing all 55 documents in the prompt. Retrieved results can include deprecated rules, so the model must distinguish active versions.
- Checker feedback is used to revise the generated site, but multiple revisions may be needed.
- Embedding caching avoids repeating document embedding calls.
- Image compression keeps the self-contained HTML below the file-size limit.
- The agent requires UPB AI Gateway access and does not detect every form of repeated action.
- Conversation history still grows over long runs despite shortening older HTML responses.
- Human continuation is available at the step limit; the current code does not request new feedback after a successful `finish`.