#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
本机开发环境检测脚本
输出已安装工具链的版本与路径，供 AI 与用户确认环境状态。
用法: & "C:\Program Files\Python313\python.exe" env_check.py
"""
import os
import shutil
import subprocess
import sys


def run(cmd, label):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or r.stderr).strip().splitlines()
        return out[0] if out else "?"
    except Exception:
        return "无法调用"


def exists(p):
    return os.path.isfile(p)


def main():
    print("=" * 52)
    print("  本机开发环境检测  |  Windows")
    print("=" * 52)

    # Python
    py = r"C:\Program Files\Python313\python.exe"
    print(f"\n[Python]")
    print(f"  路径: {py}  存在: {exists(py)}")
    if exists(py):
        print(f"  版本: {run([py, '--version'], 'python')}")

    # Git
    git = r"C:\Program Files\Git\cmd\git.exe"
    print(f"\n[Git]")
    print(f"  路径: {git}  存在: {exists(git)}")
    if exists(git):
        print(f"  版本: {run([git, '--version'], 'git')}")

    # Go
    go = r"C:\Program Files\Go\bin\go.exe"
    print(f"\n[Go]")
    print(f"  路径: {go}  存在: {exists(go)}")
    if exists(go):
        print(f"  版本: {run([go, 'version'], 'go')}")

    # Rust
    cargo = os.path.join(os.environ.get("USERPROFILE", ""), ".cargo", "bin", "cargo.exe")
    rustc = os.path.join(os.environ.get("USERPROFILE", ""), ".cargo", "bin", "rustc.exe")
    print(f"\n[Rust]")
    print(f"  rustc: {rustc}  存在: {exists(rustc)}")
    if exists(rustc):
        print(f"  版本: {run([rustc, '--version'], 'rustc')}")

    # Java
    import glob
    jdks = glob.glob(r"C:\Program Files\Eclipse Adoptium\jdk-*\bin\java.exe")
    print(f"\n[Java]")
    if jdks:
        java = jdks[0]
        print(f"  路径: {java}")
        print(f"  版本: {run([java, '-version'], 'java')}")
    else:
        print("  未找到 JDK")

    # MSVC
    msvc = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC"
    msvc_versions = []
    if os.path.isdir(msvc):
        msvc_versions = [d for d in os.listdir(msvc) if d.replace(".", "").isdigit()]
    print(f"\n[MSVC C++]")
    print(f"  BuildTools 存在: {os.path.isdir(msvc)}")
    if msvc_versions:
        print(f"  版本目录: {msvc_versions}")

    # VS Code
    vscode = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                          "Programs", "Microsoft VS Code", "Code.exe")
    print(f"\n[VS Code]")
    print(f"  路径: {vscode}  存在: {exists(vscode)}")

    # PyInstaller
    print(f"\n[PyInstaller]")
    if exists(py):
        print(f"  版本: {run([py, '-m', 'PyInstaller', '--version'], 'pyinstaller')}")

    # GitHub Code Analyzer 项目定位
    print(f"\n[GitHub 代码分析工具]")
    candidates = []
    base = os.path.join(os.environ.get("USERPROFILE", ""), "Doubao", "chats")
    if os.path.isdir(base):
        for d in os.listdir(base):
            p = os.path.join(base, d, "new-chat", "GitHubCodeAnalyzer")
            if os.path.isfile(os.path.join(p, "analyzer.py")):
                candidates.append(p)
    if candidates:
        for c in candidates:
            print(f"  找到: {c}")
    else:
        print("  未在默认位置找到（可用 Glob 搜索 analyzer.py）")

    print("\n" + "=" * 52)
    print("检测完成")


if __name__ == "__main__":
    main()
