# Group 18

## Members

| Name | Matriculation Number |
|------|----------------------|
| Parastoo Nasiri | |
| Annie Dcruz | 4038408 |
| Sophika Sathish Kumar | 4054633 |
| Parsa Zahedi | 4107873 |
| Avishkar Arjan | 4108203 |

## How to Run Everything

Every member needs Python 3.11+, git, and a personal UPB AI Gateway key
(https://ai-gateway.upb.de — university network or VPN). Put the key in
`group-18/.env` (see `.env.example`). Default chat model: `openai.gpt-6-luna`;
embeddings: `kiconnect.qwen3-embedding-8b`. Never commit `.env`.

### Task 1: OpenCode

See `task1_opencode/` (setup guide lives in the lab material `task1_opencode/README.md`).
Profiles and images: `task1_opencode/content/`. Site: `task1_opencode/site/index.html`.
Exported sessions and per-session cost/token stats: `task1_opencode/conversation/`.
Hello-world screenshots: `task1_opencode/screenshots/`.

### Task 2: Own agent

```bash
# from the repository root
python lab_1/group-18/task2_own_agent/rag.py      # test style-guide retrieval
python lab_1/group-18/task2_own_agent/agent.py    # generate the website end-to-end
```

Outputs: `task2_own_agent/site/index.html`, logs in `task2_own_agent/logs/`.
Design notes: `task2_own_agent/README.md`.

### Task 3: RAG

```bash
# from the repository root — see task3_rag/README.md and REPRODUCE.md
python lab_1/group-18/task3_rag/run_experiments.py
python lab_1/group-18/task3_rag/evaluate.py
```

Results: `task3_rag/results/`. Test predictions: `task3_rag/predictions_test.jsonl`.
Write-up: `task3_rag/RESULTS.md`, `task3_rag/ANALYSIS.md`.

### Task 4: Tools

```bash
# from lab_1/group-18/task4_tools/
python reset_workspace.py     # fresh workspace from the tinyledger fixture
python agent.py --mock        # scripted fake model (broken + malicious tool calls)
python agent.py               # real model via the gateway
git -C workspace diff > final.diff
```

Implementation: `tools.py`, `agent.py`. Trace: `logs/trace.jsonl`.
Run the lab's public tests from the material directory:
`pytest task4_tools/tests -v`.

## AI Usage Disclosure

AI tools were used to assist with task understanding, code generation, presentation
content preparation. All submitted content is manually reviewed team members.
