# Extension Request Sorter
**CIT AI-Native Engineering Programme · Semester 1 · Assessment 5 · Domain: Education**

## What this project does
A console-based Python tool that reads student extension requests. An LLM extracts the course, number of days and reason. Python validates those facts and applies the fixed department policy. It creates three reports for administrative use.

**Important:** the tool never approves or rejects an extension. Faculty members make every final decision.

## Files
- `main.py` — main Python program
- `requests.csv` — 20 sample student requests
- `courses.csv` — valid course codes
- `system_prompt.txt` — Authority, Exemplar, Constraint, Rubric and Metadata prompt
- `tests/test_project.py` — automated policy and validation checks
- `docs/` — specification, test plan, AI decision journal and reflection
- `.env.example` — environment-variable example; copy to `.env`

## Setup in VS Code
1. Extract the ZIP.
2. Open the extracted `extension_request_sorter_project` folder in VS Code.
3. Open Terminal and run `python -m venv .venv`.
4. Activate the environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
5. Run `pip install -r requirements.txt`.
6. Copy `.env.example` to `.env` and add your own API key. Never upload `.env` to GitHub.
7. Run `python main.py`.

## Output
The program creates:
- `results.csv` — extracted fields and recommendation; no original request text.
- `review_queue.csv` — requests needing more information, faculty review, or duplicate review. Contains original text and should be restricted to authorised faculty.
- `summary.txt` — aggregate counts only.

## Department policy (Python only)
1. Missing course or days → `needs_more_info`.
2. Days 3 or fewer AND reason is medical, family or technical → `within_policy`.
3. All other requests → `needs_faculty_review`.
4. Duplicate request text is flagged and sent to faculty review.

## Run tests
From the project folder:
```bash
python -m unittest discover -s tests -v
```

## Limitations
The tool cannot verify whether a student's explanation is true or judge the seriousness of a situation. The LLM may make extraction mistakes, so Python validates its output. Faculty must review the queue and make all final decisions.
