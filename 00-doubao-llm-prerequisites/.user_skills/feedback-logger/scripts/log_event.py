# -*- coding: utf-8 -*-
"""追加一行事件到 F:\\自动化验证工具\\09-feedback\\timeline.jsonl（append-only）

用法：
  # 当前事件（ts=系统当前时间，ts_source=system）
  python log_event.py --type fix --subject "修复xxx" --evidence-path "F:\\x\\file.py" --git-commit 05ab9fc --action "修改" --result "成功"

  # 过往事件回填（ts=文件修改时间，ts_source=fs；evidence 记录 created/modified/accessed + sha256）
  python log_event.py --type incident --subject "历史事件" --evidence-path "F:\\x\\file.py" --use-file-time

参数：
  --subject        必填。事件主题
  --type          incident/action/decision/fix/result，默认 action
  --evidence-path 可选。文件路径：记录 created/modified/accessed 三时间 + sha256
  --use-file-time 可选。ts 取 evidence-path 的修改时间（过往事件）；否则取系统当前时间
  --git-commit    可选。git commit hash
  --action        可选。采取的动作
  --result        可选。结果
  --notes         可选。备注
"""
import argparse, datetime, hashlib, json, os, sys

TIMELINE = r"F:\自动化验证工具\09-feedback\timeline.jsonl"


def file_evidence(path):
    st = os.stat(path)
    def iso(t):
        return datetime.datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")
    ev = {
        "path": path,
        "created": iso(st.st_ctime),
        "modified": iso(st.st_mtime),
        "accessed": iso(st.st_atime),
    }
    try:
        with open(path, "rb") as f:
            ev["sha256"] = hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        ev["sha256_error"] = str(e)
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--type", choices=["incident", "action", "decision", "fix", "result"], default="action")
    ap.add_argument("--evidence-path", default="")
    ap.add_argument("--use-file-time", action="store_true")
    ap.add_argument("--git-commit", default="")
    ap.add_argument("--action", default="")
    ap.add_argument("--result", default="")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    if args.use_file_time and not args.evidence_path:
        print("ERROR: --use-file-time 需要 --evidence-path")
        sys.exit(1)

    evidence = {}
    if args.evidence_path:
        evidence = file_evidence(args.evidence_path)

    if args.use_file_time and evidence.get("modified"):
        ts = evidence["modified"]
        ts_source = "fs"
    else:
        ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        ts_source = "system"

    rec = {
        "ts": ts,
        "ts_source": ts_source,
        "type": args.type,
        "subject": args.subject,
        "evidence": evidence,
        "action": args.action,
        "result": args.result,
        "git_commit": args.git_commit,
        "notes": args.notes,
    }
    os.makedirs(os.path.dirname(TIMELINE), exist_ok=True)
    with open(TIMELINE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("appended:", json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    main()
