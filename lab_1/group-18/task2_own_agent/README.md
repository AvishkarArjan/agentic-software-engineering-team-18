# Task 2 — Own Agent

## Run

1. Install the required Python dependencies and configure the UPB AI Gateway credentials in a local `.env` file. 

2. Test the RAG System

python lab_1/group-18/task2_own_agent/rag.py

3. From the repository root, run:

python lab_1/group-18/task2_own_agent/agent.py

4. Validate the Generated Website

python lab_1/group-18/common/site_checker.py lab_1/group-18/task2_own_agent/site/index.html --full --content lab_1/group-18/task1_opencode/content

5. Open the Generated Website

The generated HTML file is located at:

lab_1/group-18/task2_own_agent/site/index.html

6. The generated website is saved to:

`task2_own_agent/site/index.html`

7. Execution logs are saved in:

`task2_own_agent/logs/`


## Results

The agent successfully generated a website using available team profiles.

In the successful run, the checker scores improved from 18/25 to 22/25, 23/25, 24/25, and finally 25/25.

The agent completed execution after 18 model calls.

The final generated website was also checked independently and passed all 25 validation checks.

(Still need to test with all memeber profiles and images)