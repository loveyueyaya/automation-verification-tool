# 本机开发环境参考（Windows）

> 本文件是 `local-dev-environment` 技能的详细参考，按需读取。
> 机器：Windows 11（Build 22631）/ 64GB 内存。安装日期：2026-09-16。

## 1. 工具链总表

| 工具 | 版本 | 绝对路径 | 说明 |
| --- | --- | --- | --- |
| Python | 3.13.14 | `C:\Program Files\Python313\python.exe` | 全用户安装，已加 PATH；含 pip 26.x、venv |
| Git | 2.54.0.windows.1 | `C:\Program Files\Git\cmd\git.exe` | 全用户安装，已加 PATH |
| Go | 1.27.1 windows/amd64 | `C:\Program Files\Go\bin\go.exe` | MSI 安装，GOPATH 默认 `%USERPROFILE%\go` |
| Rust | 1.98.1 | `%USERPROFILE%\.cargo\bin\rustc.exe` 与 `cargo.exe` | rustup 安装（minimal profile），cargo bin 已加入用户 PATH |
| Java | Temurin 21.0.12.1 LTS | `C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\` | MSI 安装；`JAVA_HOME` 由安装器设置 |
| MSVC C++ | 14.44.35207 | `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\` | 含 Windows SDK；用 vcvars64.bat 加载环境 |
| VS Code | 最新稳定版 | `%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe` | 用户级安装 |
| Node.js | v22.23.2 | 系统已有（`node`/`npm`） | 非本次安装 |
| PyInstaller | 6.22.3 | Python313 环境内 | 打包 EXE 用 |

> CUDA 未安装。本机有 **NVIDIA GeForce RTX 4080 Laptop GPU（12GB 显存）**，可安装 CUDA Toolkit + PyTorch 做 GPU 计算（本地大模型推理/训练）。当前 GPU 基本闲置。

## 2. PowerShell 调用要点

- 带路径的可执行文件必须用 `&`：`& "C:\Program Files\Python313\python.exe" -c "print(1)"`
- 探测命令是否存在：`cmd /c "where git"` 或 `Test-Path "C:\Program Files\Git\cmd\git.exe"`
- `$env:USERPROFILE` = `C:\Users\Administrator`；`$env:LOCALAPPDATA` = `C:\Users\Administrator\AppData\Local`
- Agent 会话的 PATH 不保证含新装工具 → 优先绝对路径。

## 3. 常用命令

### Python
```powershell
# 版本 / pip
& "C:\Program Files\Python313\python.exe" --version
& "C:\Program Files\Python313\python.exe" -m pip --version

# 虚拟环境
& "C:\Program Files\Python313\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install <包>
.\.venv\Scripts\python.exe <脚本>.py

# 语法检查
& "C:\Program Files\Python313\python.exe" -m py_compile a.py b.py
```

### Git
```powershell
& "C:\Program Files\Git\cmd\git.exe" clone --depth 1 https://github.com/<owner>/<repo>.git <dir>
& "C:\Program Files\Git\cmd\git.exe" -C <dir> log -1 --oneline
```

### PyInstaller 打包
```powershell
cd <项目目录>
& "C:\Program Files\Python313\python.exe" -m pip install pyinstaller
& "C:\Program Files\Python313\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name MyApp app.py
# 产物: dist\MyApp.exe；--windowed 用于 GUI，避免黑窗口
```

### C/C++（MSVC）
```powershell
# 方式A（推荐）：加载完整环境后编译
cmd /c "\"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat\" && cl /EHsc main.cpp"

# 方式B：直接用 cl.exe 完整路径（需自行设置 INCLUDE/LIB/PATH，不推荐手动做）
```

### Go / Rust / Java
```powershell
& "C:\Program Files\Go\bin\go.exe" build ./...
& "C:\Program Files\Go\bin\go.exe" run main.go
& "$env:USERPROFILE\.cargo\bin\cargo.exe" new hello
& "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release
& "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\javac.exe" Hello.java
& "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\java.exe" Hello
```

### VS Code
```powershell
& "$env:LOCALAPPDATA\Programs\Microsoft VS Code\Code.exe" <目录>
```

## 4. GitHub 代码分析工具（本机项目）

- 默认位置：`C:\Users\Administrator\Doubao\chats\<会话>\new-chat\GitHubCodeAnalyzer\`
- 结构：`app.py`（GUI 主程序）/ `analyzer.py`（静态分析引擎）/ `ai_analyzer.py`（AI 分析）/
  `reporter.py`（报告导出）/ `build.bat`（一键打包）/ `dist\GitHubCodeAnalyzer.exe`（成品）
- 程序化分析示例：

```python
import sys
sys.path.insert(0, r"C:\Users\Administrator\Doubao\chats\<会话>\new-chat\GitHubCodeAnalyzer")
import analyzer
r = analyzer.analyze_repo(r"<代码目录>")
print(r["total_files"], r["total_lines"], r["languages"][:5], r["entries"])
```

- 运行 GUI：双击 `dist\GitHubCodeAnalyzer.exe`，或 `python app.py`
- 重新打包：双击 `build.bat`

## 5. 环境变量

| 变量 | 值 |
| --- | --- |
| Path（系统） | 含 `C:\Program Files\Python313\`、`C:\Program Files\Git\cmd\`、`C:\Program Files\Go\bin\`、`...\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\` |
| Path（用户） | 含 `%USERPROFILE%\.cargo\bin` |
| JAVA_HOME | `C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot` |
