---
name: local-dev-environment
description: "操作 Windows 本机开发环境的技能：提供已安装工具链（Python 3.13、Git 2.54、Go 1.27、Rust、Java 21 LTS、MSVC C++、VS Code、PyInstaller）的绝对路径、版本与 PowerShell 调用方式，以及在本机运行、分析、构建、打包源代码的标准工作流（含 GitHub 代码分析工具项目）。当用户要求在本机直接处理源代码（运行、修改、分析、编译、打包 EXE、克隆 GitHub 仓库、安装依赖、查询本地开发环境/工具可用性）时使用。"
---

# Local Dev Environment（本机开发环境）

## 总览

本技能记录用户 Windows 电脑上已安装的完整开发工具链，以及在本机直接处理源代码的标准流程。调用本技能后，AI 可以在本机直接执行代码运行、静态分析、构建与 EXE 打包，无需再向用户询问环境细节。

## 核心规则

- 本机命令可用 **PowerShell** 或 **Bash（Git Bash for Windows）**。**实测限制**：PowerShell 工具在本环境下 stdout 可能不回传（只返回 exit code、零输出），需要完整原始输出时改用 Bash + python。PowerShell 调用带完整路径的可执行文件必须加 `&` 前缀，例如 `& "C:\Program Files\Python313\python.exe" --version`；探测命令用 `cmd /c "where git"`。详见「平台实测坑」一节。
- Agent 会话的 PATH **不一定包含**新装工具：始终优先使用绝对路径调用工具，除非先用 `where`/`Test-Path` 验证短命令可用。
- 本机是用户真实系统（完全访问模式）：只处理用户明确要求的文件与范围；不随意删除、覆盖、移动用户的文件；写入项目输出前先确认目标目录。
- 写/改代码优先用 Read / Edit / Write 工具；执行命令、安装、构建用 Bash 工具。

## 任务并行/串行规则

本技能不再重复定义。所有并行/串行判定统一见
parallel-serial-decider 技能（R1-R23 完整版 v2.0）。

## 平台实测坑（2026-09-18 本机实测，写代码/跑命令前必读）

> 全部为本机实测结论（含退出码与报错原文），避免每轮新会话重复踩坑。
> 完整地基清单见 `F:\自动化验证工具\06-deployment\env-baseline_v1.md`。

### 坑 A：PowerShell 工具 stdout 不回传

- **现象**：执行后只返回 exit code、**零输出**（实测两次，含无管道的 `Write-Output`）。
- **规避**：需要看完整原始输出时用 Bash + python；PowerShell 只用于无需观察输出的操作。

### 坑 B：中文 Windows 外部命令输出是 GBK

- **现象**：`subprocess.run(..., text=True)` 抛 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0`。
- **规避**：显式 `encoding='gbk'` 或 `errors='replace'`；脚本开头加
  `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`。

### 坑 C：Bash 缺 coreutils（`ls`/`date`/`stat`/`head`/`tail` 全失效）

- **现象**：`ls: command not found`、`date: command not found`（退出码 127）。
- **根因**：确为 Git Bash（`MSYSTEM=MINGW64`），但系统 PATH 只挂 `C:\Program Files\Git\cmd`（仅 git.exe），coreutils 实际在 `C:\Program Files\Git\usr\bin`（372 条目）未入 PATH。
- **规避**：Bash 命令一律前置 `export PATH="/c/Program Files/Git/usr/bin:$PATH"`。
- **附带**：Bash 变量调用必须加引号 —— `"$PY" script.py`，否则含空格路径被截断为 `C:/Program: No such file or directory`（退出码 127）。
- 说明：Bash 只是外层壳，其中运行的 `python.exe` / `git.exe` 都是 Windows 原生程序。

### 坑 D：裸 `python` 解析到 3.13.12，不是项目的 3.13.14

- `shutil.which('python')` → `...\.workbuddy\binaries\python\versions\3.13.12\python.EXE`。
- **规避**：一律写绝对路径 `C:\Program Files\Python313\python.exe`。

### 坑 E：pip 安装可能撬动地基包（numpy/cv2/paddle）

- **规避**：安装时把地基包写成 `==` 钉子一并交给 pip 解析，例如
  `pip install pywinauto "numpy==2.3.5" "pillow==12.3.0"`，
  输出 `Requirement already satisfied` 即证明未漂移；装完复验版本。

## 环境速查（绝对路径）

| 工具 | 路径 / 调用方式 |
| --- | --- |
| Python 3.13.14 | `C:\Program Files\Python313\python.exe` |
| Git 2.54 | `C:\Program Files\Git\cmd\git.exe` |
| Go 1.27.1 | `C:\Program Files\Go\bin\go.exe` |
| Rust 1.98 | `%USERPROFILE%\.cargo\bin\rustc.exe` / `cargo.exe` |
| Java 21 LTS | `C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\java.exe` |
| MSVC C++ | `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat`（编译前先加载） |
| VS Code | `%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe` |
| PyInstaller | `& "C:\Program Files\Python313\python.exe" -m PyInstaller` |

版本、路径细节与更多命令见 `references/environment.md`。

## 标准工作流

### 1. 确认环境 / 排查工具问题

运行环境检测脚本，输出工具链版本与路径：

```powershell
& "C:\Program Files\Python313\python.exe" "<本技能目录>\scripts\env_check.py"
```

### 2. 运行 Python 代码

```powershell
& "C:\Program Files\Python313\python.exe" <脚本.py>
```

- 建虚拟环境：`& "C:\Program Files\Python313\python.exe" -m venv .venv`，之后用 `.venv\Scripts\python.exe`
- 安装依赖：`.venv\Scripts\pip.exe install <包名>`（或直接 `python.exe -m pip install`）

### 3. 克隆并处理 GitHub 源码

```powershell
& "C:\Program Files\Git\cmd\git.exe" clone --depth 1 https://github.com/<owner>/<repo>.git <目标目录>
```

### 4. 分析本地源代码（结构 / 语言 / 统计）

- 用 GitHub 代码分析工具的引擎做程序化分析：

```python
import sys
sys.path.insert(0, r"<GitHubCodeAnalyzer目录>")
import analyzer
result = analyzer.analyze_repo(r"<代码目录>")
# result 含: languages / total_lines / entries / deps / todos / git ...
```

- 或运行已打包的 `GitHubCodeAnalyzer.exe`（GUI，支持「打开本地目录分析」）。
- 定位该工具：在用户项目目录（形如 `C:\Users\Administrator\Doubao\chats\<会话>\new-chat\GitHubCodeAnalyzer`）用 Glob 搜索 `analyzer.py`；找不到时询问用户。

### 5. 打包 Python 程序为 EXE

```powershell
cd <项目目录>
& "C:\Program Files\Python313\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name <名称> app.py
```

- 产物在 `dist\<名称>.exe`；若提示缺 pyinstaller，先执行 `python.exe -m pip install pyinstaller`。
- GUI 程序务必加 `--windowed`（否则会带黑窗口）。

### 6. 编译 C/C++

每个新会话先加载 MSVC 环境，再编译：

```powershell
cmd /c "\"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat\" && cl <源文件>.c"
```

### 7. Go / Rust / Java

```powershell
& "C:\Program Files\Go\bin\go.exe" build ./...
& "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release
& "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\javac.exe" <源文件>.java
```

## 阶段封板流程（硬规则）

每阶段（P1/P2/P3…）收尾时必须执行，缺一不可：

1. **打 tag**：`git tag -a "ui-toolbox-P<阶段>-<日期>" -m "<阶段> 说明"`，随后 `git push origin <tag>`。
2. **准备 RELEASE_NOTES_vX.md**：从阶段文档复制生成，开头写清：Release 名 + 上传时间（精确到秒）、日期、内容、测试结果、已知偏差章节、pyc 备份位置。
3. **打包资产**：验收证据目录 → `<阶段>_acceptance_evidence.zip`；pyc 备份（如阶段内有重建且 <500MB）→ `<阶段>_pyc_backup.zip`。**资产文件名必须全英文**——中文名会被 gh CLI 截断成 `P1_.zip` 这类坏名。
4. **发 Release**：`gh release create <tag> --title "<阶段> 标题" --notes-file RELEASE_NOTES_vX.md <资产.zip>...`
5. **验证**：`gh release view <tag> --json tagName,assets` 确认 Release 存在、资产列表完整。

Release 是"最后保险"：任何代码丢失都可从 Release 资产（证据包 + pyc 备份）+ tag 指向的 commit 恢复。项目代码权威源始终在 `F:\自动化验证工具`，禁止依赖 AppData。

## 索引维护（硬规则）

任何新产物产出后（文档新版本 / 技能改动 / 新文件），**必须同步更新对应目录的索引文件**，不留欠账：

| 产物 | 对应索引 |
|---|---|
| 需求规格说明书 vX | `F:\自动化验证工具\01-requirements\requirements-index.md` |
| 技能体系改动（SKILL.md / 脚本 / 新技能） | `F:\自动化验证工具\00-doubao-llm-prerequisites\doubao-prerequisites-index.md` |
| 技能职责/依赖变化 | `F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\SKILLS_INDEX.md` |
| 审查日志 | `F:\自动化验证工具\08-review-logs\INDEX.md` |
| 反馈日志 | `F:\自动化验证工具\09-feedback\feedback-index.md` |

原则：
- 索引只记录"当前存在的产物 + 一句话职责"，产出后立即更新
- 描述过期的旧条目必须同步修正（如技能职责变化）
- 违反 = 索引欠账，视为未完成

## 资源

- `scripts/env_check.py` — 输出本机工具链版本与路径（可直接执行）。
- `references/environment.md` — 完整环境参考：各工具版本、安装路径、常用命令与注意事项（分析/构建前按需读取）。
