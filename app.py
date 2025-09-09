import os
import json
import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional

import streamlit as st
import google.generativeai as genai

# --------------------------- App Config ---------------------------
APP_TITLE = "AI To-Do"
st.set_page_config(page_title=APP_TITLE, page_icon="📝", layout="wide")

DATA_FILE = "tasks.json"


# Sidebar for API key input
st.sidebar.header("🔑 API Key")
user_api_key = st.sidebar.text_input("Enter your Gemini API Key:", type="password")

if user_api_key:
    genai.configure(api_key=user_api_key)
    GEMINI_AVAILABLE = True
else:
    GEMINI_AVAILABLE = False


# --------------------------- Data Layer ---------------------------
def load_tasks() -> List[Dict[str, Any]]:
    if "tasks" in st.session_state:
        return st.session_state["tasks"]
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except Exception:
            tasks = []
    else:
        tasks = []
    st.session_state["tasks"] = tasks
    return tasks


def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    st.session_state["tasks"] = tasks
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False, default=str)
    except Exception:
        pass


def new_task_dict(title: str, due: Optional[date], priority: str, tags: List[str]) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "title": title.strip(),
        "done": False,
        "created_at": datetime.now().isoformat(),
        "due": due.isoformat() if due else None,
        "priority": priority,
        "tags": tags,
        "subtasks": []
    }


# --------------------------- AI Helpers ---------------------------

def ai_parse_task(prompt: str) -> Dict[str, Any]:
    """Parse a natural language prompt into a task dict fields."""
    if not GEMINI_AVAILABLE:
        return {"title": prompt.strip(), "priority": "Medium", "due": None, "tags": []}
        
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(
            f"""
            Extract a to-do item from: \"\"\"{prompt}\"\"\".
            Return JSON with keys:
            - title (short string)
            - priority (High/Medium/Low)
            - due (YYYY-MM-DD or null)
            - tags (array of short tags)
            Only output valid JSON.
            """
        )
        content = resp.text.strip()
        import json as pyjson, re
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            data = pyjson.loads(match.group(0))
            return {
                "title": data.get("title", prompt.strip()),
                "priority": (data.get("priority") or "Medium").title(),
                "due": data.get("due"),
                "tags": data.get("tags") or []
            }
    except Exception as e:
        print("Gemini parse error:", e)

    return {"title": prompt.strip(), "priority": "Medium", "due": None, "tags": []}


def ai_breakdown(title: str) -> List[str]:
    """Break a task into 3–6 actionable subtasks."""
    if not GEMINI_AVAILABLE:
        st.sidebar.warning("⚠️ Gemini API key not set. AI features disabled.")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(
            f"Break the task into 3-6 concise subtasks (bullet list, one line each): {title!r}"
        )
        lines = [ln.strip("-• ").strip() for ln in resp.text.splitlines() if ln.strip()]
        return [ln for ln in lines if 0 < len(ln) <= 140][:6]
    except Exception as e:
        print("Gemini breakdown error:", e)
        return []


def ai_prioritize(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reassign priorities based on urgency/impact using Gemini."""
    if not GEMINI_AVAILABLE or not tasks:
        return tasks

    try:
        descriptions = [
            f"{i+1}. {t['title']} (due: {t.get('due')}, priority: {t.get('priority')}, done: {t.get('done')})"
            for i, t in enumerate(tasks)
        ]
        prompt = (
            "Reassign each task a priority of High/Medium/Low. "
            "Return JSON array with objects: {title, priority}.\n" + "\n".join(descriptions)
        )

        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        content = resp.text.strip()

        import json as pyjson, re
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            updates = pyjson.loads(match.group(0))
            mapping = {item["title"]: item["priority"].title() for item in updates if "title" in item}
            for t in tasks:
                if t["title"] in mapping:
                    t["priority"] = mapping[t["title"]]
        return tasks
    except Exception as e:
        print("Gemini prioritize error:", e)
        return tasks


# --------------------------- UI ---------------------------
st.title("📝 AI To-Do")
st.caption("Add tasks normally or let AI extract details, break down work, and help prioritize.")

# Sidebar
with st.sidebar:
    st.header("Settings")
    st.write("**AI status:**", "✅ Enabled" if GEMINI_AVAILABLE else "❌ Disabled")
    st.write("Set `GEMINI_API_KEY` as a secret to enable AI features.")
    st.divider()
    st.write("Filters")
    show_only_open = st.checkbox("Show only open tasks", value=False)
    selected_priority = st.multiselect("Filter by priority", ["High", "Medium", "Low"], default=[])
    tag_filter = st.text_input("Filter by tag (single tag)", value="").strip()

tasks = load_tasks()

# Add task form
with st.container(border=True):
    st.subheader("Add a task")
    col1, col2, col3 = st.columns([4, 2, 2])
    with col1:
        title = st.text_input("Title", placeholder="e.g., Finish MAD project report")
    with col2:
        due = st.date_input("Due date", value=None)
    with col3:
        priority = st.selectbox("Priority", ["Medium", "High", "Low"], index=0)
    tags = st.text_input("Tags (comma-separated)", placeholder="work, project, school").strip()
    ai_prompt = st.text_input("Or describe it and let AI parse:", placeholder="Draft report by Friday 5 PM, high priority, tag: project")
    c1, c2, c3 = st.columns([1, 1, 6])
    with c1:
        if st.button("Add"):
            if title.strip():
                t = new_task_dict(title, due, priority, [t.strip() for t in tags.split(",") if t.strip()])
                tasks.append(t)
                save_tasks(tasks)
                st.success("Task added.")
            else:
                st.warning("Title cannot be empty.")
    with c2:
        if st.button("AI Add"):
            if ai_prompt.strip():
                parsed = ai_parse_task(ai_prompt.strip())
                parsed_due = None
                try:
                    if parsed.get("due"):
                        parsed_due = date.fromisoformat(parsed["due"])
                except Exception:
                    parsed_due = None
                t = new_task_dict(parsed.get("title", ai_prompt.strip()),
                                  parsed_due,
                                  parsed.get("priority", "Medium"),
                                  parsed.get("tags", []))
                tasks.append(t)
                save_tasks(tasks)
                st.success("AI-parsed task added.")
            else:
                st.warning("Please provide a description for AI to parse.")

st.divider()

# Task List
def task_matches_filters(t: Dict[str, Any]) -> bool:
    if show_only_open and t["done"]:
        return False
    if selected_priority and t.get("priority") not in selected_priority:
        return False
    if tag_filter:
        return tag_filter in (t.get("tags") or [])
    return True


open_tasks = [t for t in tasks if task_matches_filters(t)]

st.subheader(f"Tasks ({len(open_tasks)}/{len(tasks)})")
for t in open_tasks:
    with st.expander(f"{'✅' if t['done'] else '⬜️'}  {t['title']}"):
        c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 5])
        with c1:
            t['done'] = st.checkbox("Done", value=t['done'], key=f"done_{t['id']}")
        with c2:
            t['priority'] = st.selectbox("Priority", ["High", "Medium", "Low"],
                                         index=["High", "Medium", "Low"].index(t.get("priority", "Medium")),
                                         key=f"prio_{t['id']}")
        with c3:
            due_str = t.get("due")
            new_due = st.date_input("Due", value=(date.fromisoformat(due_str) if due_str else None),
                                    key=f"due_{t['id']}")
            t['due'] = new_due.isoformat() if new_due else None
        with c4:
            tags_csv = ",".join(t.get("tags", []))
            new_tags = st.text_input("Tags (csv)", value=tags_csv, key=f"tags_{t['id']}")
            t['tags'] = [x.strip() for x in new_tags.split(",") if x.strip()]

        # Subtasks
        st.markdown("**Subtasks:**")
        for idx, stask in enumerate(t.get("subtasks", [])):
            sc1, sc2 = st.columns([0.1, 0.9])
            with sc1:
                stask["done"] = st.checkbox("", value=stask.get("done", False), key=f"sub_{t['id']}_{idx}")
            with sc2:
                stask["title"] = st.text_input("", value=stask["title"], key=f"sub_title_{t['id']}_{idx}")
        sc1, sc2, sc3 = st.columns([1, 1, 6])
        with sc1:
            if st.button("➕ Add subtask", key=f"add_sub_{t['id']}"):
                t.setdefault("subtasks", []).append({"title": "New subtask", "done": False})
        with sc2:
            if st.button("🧠 AI breakdown", key=f"ai_bd_{t['id']}"):
                parts = ai_breakdown(t['title'])
                for p in parts:
                    t.setdefault("subtasks", []).append({"title": p, "done": False})
                st.toast(f"Added {len(parts)} AI-generated subtasks.")

        if st.button("🗑️ Delete task", type="secondary", key=f"del_{t['id']}"):
            tasks = [x for x in tasks if x["id"] != t["id"]]
            save_tasks(tasks)
            st.rerun()

save_tasks(tasks)

st.divider()
lc1, lc2, lc3 = st.columns([1, 1, 6])
with lc1:
    if st.button("🧠 AI prioritize all"):
        tasks = ai_prioritize(tasks)
        save_tasks(tasks)
        st.success("Priorities updated (where possible).")
with lc2:
    if st.button("✅ Mark all done"):
        for t in tasks:
            t["done"] = True
        save_tasks(tasks)
        st.success("All tasks marked as done.")

st.caption("Tip: On Streamlit Cloud, the filesystem resets on redeploy. For persistence, connect a DB (e.g., Supabase) or Google Drive API.")
