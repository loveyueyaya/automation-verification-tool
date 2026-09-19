# -*- coding: utf-8 -*-
"""追加一行决策日志到技能决策日志权威源（decision-log/decisions.jsonl，并同步 log.txt 可读镜像）

用法：
  python log_decision.py --task "改分支名+写文档" --keywords "改分支名,写文档" ^
      --hit-rules "R7,R3" --strategy serial --reason "R7 最严格" ^
      --cache-created yes --cache-path "F:\\x" --result success --duration-s 12.5 --notes ""
"""
import argparse, datetime, json, os

LOG_FILE = r"F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\parallel-serial-decider\decision-log\decisions.jsonl"
LOG_TXT = r"F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\parallel-serial-decider\log.txt"  # 可读镜像，供用户手动核查
MAX_BYTES = 10 * 1024 * 1024  # 10MB 滚动


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--keywords", default="")
    ap.add_argument("--hit-rules", default="")
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--reason", default="")
    ap.add_argument("--cache-created", choices=["yes", "no"], default="no")
    ap.add_argument("--cache-path", default="")
    ap.add_argument("--result", default="")
    ap.add_argument("--duration-s", type=float, default=0.0)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # 滚动：超过 10MB 归档
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_BYTES:
        archive = LOG_FILE.replace(".jsonl", "_%s.jsonl" % datetime.date.today().strftime("%Y%m%d"))
        os.replace(LOG_FILE, archive)

    rec = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "task": args.task,
        "keywords": [k.strip() for k in args.keywords.split(",") if k.strip()],
        "hit_rules": [k.strip() for k in args.hit_rules.split(",") if k.strip()],
        "final_strategy": args.strategy,
        "reason": args.reason,
        "cache_created": args.cache_created == "yes",
        "cache_path": args.cache_path,
        "result": args.result,
        "duration_s": args.duration_s,
        "notes": args.notes,
    }
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    # 同步追加到 log.txt（可读镜像，供用户手动核查；滚动时同步重建）
    if os.path.exists(LOG_TXT) and os.path.getsize(LOG_TXT) > MAX_BYTES:
        archive_txt = LOG_TXT.replace(".txt", "_%s.txt" % datetime.date.today().strftime("%Y%m%d"))
        os.replace(LOG_TXT, archive_txt)
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, encoding="utf-8") as f:
                with open(LOG_TXT, "w", encoding="utf-8") as g:
                    g.write(f.read())
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(line)
    print("决策日志已写入: %s" % LOG_FILE)
    print("已同步 log.txt: %s" % LOG_TXT)
    print(json.dumps(rec, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
