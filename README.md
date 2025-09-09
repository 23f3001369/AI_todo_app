
# AI To-Do (Streamlit)

A simple To-Do list app with optional AI features powered by OpenAI:
- Parse natural language descriptions into task fields (title, due, priority, tags)
- Break a task into actionable subtasks
- (Optional) AI prioritization

If `OPENAI_API_KEY` is not set, the app still works as a normal To-Do list.

## Local Run

```bash
pip install -r requirements.txt
# Set your key (PowerShell):
$env:OPENAI_API_KEY="sk-..."
# macOS/Linux:
export OPENAI_API_KEY="sk-..."
streamlit run app.py
