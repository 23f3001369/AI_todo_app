
# AI To-Do (Streamlit)

A simple To-Do list app with optional AI features powered by Gemini:
- Parse natural language descriptions into task fields (title, due, priority, tags)
- Break a task into actionable subtasks
- (Optional) AI prioritization


## Local Run

```bash
pip install -r requirements.txt
# Set your key (PowerShell):
$env:GEMINI_API_KEY="...."
# macOS/Linux:
export GEMINI_API_KEY="...."
streamlit run app.py
