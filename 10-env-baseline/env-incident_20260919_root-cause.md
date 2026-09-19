# 环境事故根因取证报告：site-packages 包文件批量丢失

- 取证时间：**2026-09-19 04:14 ~ 04:35 +0800**（系统时间实测）
- 取证原则：**一切结论以本机代码/日志的原始输出为准**（用户 2026-09-19 裁定的绝对规则）
- 关联 issue：`F:\自动化验证工具\09-feedback\issues\issue_002_site-packages-file-loss.md`
- 关联上一步：`env-verify_20260919.md`（环境验证报告，含覆盖法修复记录）

---

## 一、结论（一句话）

**根因链**：WorkBuddy 工具层把命令触发的删除操作**逐个文件转送回收站（`genie-trash`）** →
每次删除实测 **47~126 ms/文件**（对照组 `cmd /c del` 仅 **0.74 ms/文件**，慢 64~170 倍）→
`pip uninstall` / `pip install --force-reinstall` 这类万级文件操作**必然超过命令超时**（180~600 s）→
**进程被强杀（`killed=true`）**→ 卸载中断 → 包被"半删"（pip 已把 `pkg` 改名为 `~pkg` 并删掉一部分）→
`import` 失败、`dist-info` 残留（或反向缺失），表现为"文件凭空消失"。

**不是**：磁盘空间不足、杀毒软件隔离、UAC/权限、Git 操作。

---

## 二、取证步骤与原始证据

### 2.1 先排除：分辨率误报（用户说法已由代码证实）

| 检查 | 原始输出 |
|---|---|
| `GetSystemMetrics(0/1)`（主屏） | `2560 x 1440` |
| `GetSystemMetrics(78/79)`（虚拟屏） | `2560 x 1440` |
| `EnumDisplayMonitors` | 1 台，`(0,0) 2560x1440` |
| 项目截图引擎 `shot.py` | `{"engine":"dxcam","mode":"fullscreen","size":[2560,1440]}` |
| dxcam 原始帧 | `(1440, 2560, 3)` |

→ 与 09-18 基线（2560×1440）一致，**"3200×1440" 为切屏过程中的瞬时状态**，用户说法核实无误。

### 2.2 排除项（逐项实测，均不成立）

| 假设 | 实测结果 | 结论 |
|---|---|---|
| Windows Defender 隔离 | `Get-MpComputerStatus`/`Get-MpThreatDetection` 等 cmdlet **不存在**（Defender 未启用），`root\SecurityCenter2` 无注册杀软 | ✗ |
| 沙箱 GC 清理超量 | GC 日志：`retain_window=600s/1800s`，`maxSizeMb=3000`；全程只有 `sandbox-cli-gc: 无需删除`（172 次），**无任何一次真实删除记录** | ✗ |
| CLI 文件树清单回滚 | `file-tree-manifests`/`changes-index` 解析：仅覆盖工作区 `F:\wordbuddy\...`，`Python313`/`site-packages`/`paddle`/`cv2` **出现 0 次** | ✗ |
| 凭据检测规则 | `security\...\detect-rules.toml` = 密码/密钥检测（cipher），与文件删除无关 | ✗ |

### 2.3 抓到肇事者：系统审计（本次新建的取证手段）

**手段**：`auditpol` 开启「文件系统」审核（GUID `{0CCE921D-...}`，成功+失败）+ 对 `C:\Program Files\Python313` 设置可继承 SACL（`FileSystemRights=Delete,DeleteSubdirectoriesAndFiles`）。
**自证性测试**：创建 `site-packages\_wbaudit\probe.txt` 后删除 → 安全日志 4663 命中，原始输出：

```
09/19/2026 04:19:17 | 进程=C:\Program Files\WorkBuddy\resources\vendor\genie-trash\win32-x64.exe | PID=0x2e4c | 对象=C:\Program Files\Python313\Lib\site-packages\_wbaudit\probe.txt
09/19/2026 04:19:17 | 进程=C:\Program Files\WorkBuddy\resources\vendor\genie-trash\win32-x64.exe | PID=0x2e4c | 对象=C:\$RECYCLE.BIN\S-1-5-21-...\$RMZ6QIW.txt
```

→ **删除由 `genie-trash` 执行，且文件进入回收站**（同一份删除产生"原路径删除 + 回收站写入"两条事件）。
工具层还装了 `CODEBUDDY_SAFE_DELETE_PS_R*` 变量（沙箱日志里的 PowerShell profile 片段）作为安全删除挂钩。

**回滚信息**（本次审计改动可完整还原）：
- 原始 SACL（空）：`Sddl = O:SYG:SYD:AI(A;ID;FA;;;S-1-5-80-956008885-...)...`
- 现 SACL 追加：`S:AI(AU;OICISAFA;DTSD;;;WD)`
- 还原命令：`Set-Acl` 去掉该 AuditRule；`auditpol /set /subcategory:"{0CCE921D-69AE-11D9-BED3-505054503030}" /success:disable /failure:disable`

### 2.4 量化：删除到底有多慢（同环境对照实验）

各通道删除 100 个文件（文件内容 200 B）实测：

| 删除通道 | 用时 | 单文件成本 | 回收站条目变化 |
|---|---|---|---|
| Python `os.remove`（在受拦截进程内） | 12,586 ms | **125.86 ms/文件** | **+100** |
| Bash `rm`（工具层命令） | 4,924 ms | **49.2 ms/文件** | **+100** |
| 工作区内 `rm`（对照组） | 4,708 ms | **47.08 ms/文件** | **+100** |
| `cmd /c del /q`（不经拦截通道） | 74 ms | **0.74 ms/文件** | **+0** |

→ 结论：**同时满足**"全部进回收站"与"慢 64~170 倍"。按 47 ms/文件折算：`paddlepaddle` 3,500 文件 ≈ 165 s；numpy + 依赖 1,500 文件 ≈ 70 s；opencv 三包连卸 ≈ 更久 —— 与各档命令超时（180/300/420/600 s）处于同一量级。

### 2.5 抓到中断：进程被杀（`killed=true`）

沙箱日志统计：`killed=false` 1,611 次、**`killed=true` 28 次**。ProcessKill 时刻（原文）与删除潮结束时刻对照：

| 删除潮 | 删除时间跨度（回收站元数据实测） | ProcessKill 时刻 | 对应 |
|---|---|---|---|
| W1 | 00:05:09 ~ 00:19:46（2,252 个缺失文件） | **00:04:29**（pipe-41）、**00:18:40**（pipe-56） | ✓ 重合 |
| W2 | 01:49:01 ~ 01:55:53（1,822 个） | **01:55:53.581**（pipe-4） | ✓ **与最后一笔删除同一秒** |
| W3 | 03:32:56 ~ 03:40:31（821 个，paddle 813） | **03:37:46**（pipe-9）、**03:41:54**（pipe-11） | ✓ 重合 |

### 2.6 触发命令（沙箱日志 `displayCommand` 原文摘录）

| 时刻 | 命令 | 备注 |
|---|---|---|
| 00:06:26 | `python -m pip install --no-deps --no-cache-dir "numpy==2.3.5"` | 触发 numpy 卸载；回收站留下 `~umpy`（1108 文件）、numpy（787） |
| 00:07 / 00:12 | `python -m pip uninstall -y opencv-python opencv-contrib-python openc...` | `timeoutMs=180000`；开跑 ≤40 s 即触及删除成本上限 |
| 00:11:39 | `python -m pip install --no-deps --force-reinstall --no-cache-dir "op...` | **`--force-reinstall`**（项目后来明令禁用） |
| 03:32:35 / 03:32:46 / 03:38:06 | `python -m pip uninstall -y paddlepaddle`（**连做 3 次**） | 删掉与 `paddlepaddle-gpu` **共享**的 `paddle/` 树，813 个文件缺失 |

### 2.7 损坏面量化（回收站元数据 `$I` 全量解析）

- 回收站条目总数 35,495；site-packages 相关 **29,592**
- 其中 **24,405** 对应文件**当前存在** → 属于"覆盖式替换时旧版本进回收站"的良性回收
- **5,187 个文件当前缺失**；其中 **5,186 个仍带可恢复负载（`$R`），合计 132.1 MB**
- 缺失分布：`~umpy` 1108、paddle 875、numpy 787、openpyxl 365、baidubce 233、huggingface_hub 196、Cython 159、comtypes 157、future 146、cv2 140、modelscope_hub 69、chardet 48、cryptography 41、opt_einsum 40、packaging 38、dxcam 29、nvidia 26 …

> 注：本节"当前缺失"是**修复后**的残留统计（paddle/cv2/dxcam 等已由 `env-verify_20260919.md` 的覆盖法补回并可正常 import）。

---

## 三、可复现取证工具（本轮新建，可复用）

| 工具 | 路径 | 用途 |
|---|---|---|
| `recycle_forensics.py` | `F:\自动化验证工具\10-env-baseline\_tools\` | 解析回收站 `$I`，还原被删文件的原路径 + 精确删除时间（支持 `--since` 与关键字过滤） |
| `damage_check.py` | 同上 | 判定回收条目是否造成"当前缺失"，统计可恢复负载与包分布 |
| `analyze_waves.py` | 同上 | 按波次统计删除构成（顶层包 / 扩展名 / 样例） |
| `attribute_waves.py` | 同上 | 时间窗口 × 包名 × 缺失数，做操作归因 |
| `watch_files.py` | 同上 | 定时采样关键目录文件数（用于确认"是否仍在持续消失"） |
| `restore_from_wheels.py` | 同上 | 覆盖法修复（wheel → 逐文件覆盖写入，只补不删） |

---

## 四、结论与建议（按优先级）

1. **禁止**在大包上使用 `pip uninstall` / `--force-reinstall`（本环境特有风险）：卸载 `opencv-python` 连带删共享 `cv2/`；卸载 `paddlepaddle`(CPU) 直接删共享 `paddle/` 树 → 打死 `paddlepaddle-gpu`。
2. 修环境继续用**覆盖法**（下载 wheel → 只补缺失文件 → 覆盖写入），与项目既有硬规则一致；禁止 `pip --force-reinstall`。
3. 必须批量删除时：先把该条命令的**超时放大到 ≥1800 s**（并先建缓存快照），否则必然被中断；对纯残留目录可评估使用快速通道（`cmd /c rd /s /q`，0.74 ms/文件），代价是放弃"可撤销"。
4. 本次开启的**文件系统审计建议保留**（不改权限，只加审计规则）；再发生同类事件可直接拿到进程名与时间戳。若不需要，可用 2.3 节的命令还原。
5. 恢复策略：**按包判断**——整包缺失→从回收站恢复；部分缺失→wheel 覆盖法补齐。不得整体回灌旧版本（会与新版本混淆造成二次损坏）。
6. 用户裁定的规则入库：**遇到版本问题直接查官方手册与更新说明；若不涉及被调用的 API，则不做升级**（已写入 `SOUL.md` 与 `local-dev-environment\SKILL.md`）。
