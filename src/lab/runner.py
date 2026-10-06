"""GUIDE Phần 1 - Chạy một tác vụ (task) và ghi kết quả.   >>> SINH VIÊN CÀI ĐẶT run_task <<<

Pseudo-code: guides/pseudocode/03_runner.md
Kiểm tra:    pytest tests/test_03_runner.py
Chạy thật:   python -m lab.runner --condition baseline --tasks learn
"""
import argparse
import json
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.callbacks import UsageMetadataCallbackHandler
import time
import tempfile
import shutil
import datetime

from .grading import grade
from .tasks import ROOT, get_task, hash_dir, list_tasks, prepare_sandbox
from .agent import build_agent

# Ba điều kiện thí nghiệm (condition). `skills_dir` là thư mục skill nguồn (tính từ thư mục gốc của lab).
CONDITIONS = {
    "baseline": {"mode": "single", "skills_dir": None},
    "subagents": {"mode": "subagents", "skills_dir": None},
    "skills-auto": {"mode": "single", "skills_dir": "skills/auto"},
}


def render_trace(messages) -> str:
    """CÓ SẴN, KHÔNG SỬA. Chuyển danh sách message của luồng chính thành Markdown (vết - trace).

    Lưu ý: chỉ gồm luồng chính. Việc subagent làm bên trong KHÔNG hiện trong vết;
    chỉ thấy lệnh gọi `task` và báo cáo cuối của subagent.
    """
    home = str(Path.home())

    def clean(text) -> str:
        return str(text).replace(home, "~")[:1500]

    parts = []
    for m in messages:
        if isinstance(m, AIMessage):
            if m.content:
                parts.append(f"### Assistant\n{clean(m.content)}")
            for tc in m.tool_calls:
                parts.append(f"### Tool call: {tc['name']}\n{clean(json.dumps(tc['args'], ensure_ascii=False))}")
        elif isinstance(m, ToolMessage):
            parts.append(f"### Tool result\n{clean(m.content)}")
        else:
            parts.append(f"### {m.type.capitalize()}\n{clean(m.content)}")
    return "\n\n".join(parts)


def run_task(task_id: str, condition: str, results_dir="results", model=None, recursion_limit: int = 60) -> dict:
    cfg = CONDITIONS[condition]
    task = get_task(task_id)
    skills_dir = ROOT / cfg["skills_dir"] if cfg["skills_dir"] else None
    out = Path(results_dir) / condition / task_id
    out.mkdir(parents=True, exist_ok=True)
    
    sandbox = Path(tempfile.mkdtemp())
    record = {
        "task": task_id,
        "condition": condition,
        "role": task.role,
        "error": None,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    try:
        prepare_sandbox(task, sandbox, skills_dir)
        hash_truoc = hash_dir(sandbox / "skills") if (sandbox / "skills").exists() else None
        record["skills_sha256"] = hash_truoc

        agent = build_agent(sandbox, mode=cfg["mode"], use_skills=(skills_dir is not None), model=model)
        usage = UsageMetadataCallbackHandler()
        t0 = time.time()
        
        messages = []
        final = ""
        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": task.instruction}]},
                config={"callbacks": [usage], "recursion_limit": recursion_limit}
            )
            messages = result.get("messages", [])
            final = messages[-1].content if messages else ""
        except Exception as e:
            record["error"] = f"{type(e).__name__}: {str(e)}"

        record["seconds"] = round(time.time() - t0, 1)
        
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        
        if hasattr(usage, "usage_metadata"):
            for v in usage.usage_metadata.values():
                input_tokens += v.get("input_tokens", 0)
                output_tokens += v.get("output_tokens", 0)
                total_tokens += v.get("total_tokens", 0)
                
        record["tokens"] = {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens
        }

        calls = []
        for m in messages:
            if isinstance(m, AIMessage) and hasattr(m, "tool_calls"):
                calls.extend(m.tool_calls)
        
        record["tool_calls"] = len(calls)
        record["subagent_calls"] = sum(1 for c in calls if c["name"] == "task")
        
        skills_read = set()
        for c in calls:
            if c["name"] == "read_file" and "file_path" in c.get("args", {}):
                path = c["args"]["file_path"]
                if "skills/" in path:
                    parts = path.split("skills/")
                    if len(parts) > 1:
                        skill_name = parts[1].split("/")[0]
                        skills_read.add(skill_name)
                        
        record["skills_read"] = len(skills_read)
        
        hash_sau = hash_dir(sandbox / "skills") if (sandbox / "skills").exists() else None
        record["skills_modified"] = (hash_sau != hash_truoc)
        record["final_message"] = final
        
        g = grade(task, sandbox / "workspace")
        record.update(g)
        
        (out / "trace.md").write_text(render_trace(messages), encoding="utf-8")
        
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
        
    with open(out / "run.json", "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
        
    return record


def main(argv=None):
    """CÓ SẴN, KHÔNG SỬA. Giao diện dòng lệnh (CLI): --condition, --tasks (id... | all | learn | eval), --results, --recursion-limit.

    In mỗi lần chạy một dòng: điều kiện, id, passed/total, token, số tool call, số giây, lỗi (nếu có).
    """
    ap = argparse.ArgumentParser(description="Run tasks under one condition.")
    ap.add_argument("--condition", required=True, choices=sorted(CONDITIONS))
    ap.add_argument("--tasks", nargs="+", default=["all"], help="task ids, or 'all', 'learn', 'eval'")
    ap.add_argument("--results", default="results")
    ap.add_argument("--recursion-limit", type=int, default=60)
    args = ap.parse_args(argv)
    if args.tasks == ["all"]:
        ids = [t.id for t in list_tasks()]
    elif args.tasks in (["learn"], ["eval"]):
        ids = [t.id for t in list_tasks(args.tasks[0])]
    else:
        ids = args.tasks
    for tid in ids:
        try:
            r = run_task(tid, args.condition, args.results, recursion_limit=args.recursion_limit)
        except Exception as exc:  # noqa: BLE001
            print(f"{args.condition:13s} {tid:11s} CRASH {type(exc).__name__}: {exc}", flush=True)
            continue
        print(f"{args.condition:13s} {tid:11s} score={r['passed']}/{r['total']} tokens={r['tokens']['total']} "
              f"calls={r['tool_calls']} {r['seconds']}s" + (f" ERROR={r['error']}" if r["error"] else ""), flush=True)


if __name__ == "__main__":
    main()
