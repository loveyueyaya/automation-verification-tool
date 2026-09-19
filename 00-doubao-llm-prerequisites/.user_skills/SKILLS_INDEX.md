# 技能索引（.user_skills）

权威源：`F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\`
加载目录：`C:\Users\Administrator\.workbuddy\skills\`（在下一轮对话自动注入技能列表）

**加载机制实测（2026-09-19 复验）**：两处**均为实体目录**（`GetFileAttributesW` 无 `FILE_ATTRIBUTE_REPARSE_POINT`，`os.path.islink`=False —— 不是 junction、不是符号链接）。
→ **改权威源后必须同步复制到 AppData 才在下一轮生效**；同步后必须用 SHA256 逐文件校验一致（方法见文末）。

## 绝对规则（用户 2026-09-19 裁定，最高优先级）

1. **一切判断必须建立在本地代码的真实执行结果上** —— 不许猜测，每一步先跑代码验证。
2. **文件/包/接口是否存在只用执行验证**（`os.path.exists` / `importlib.util.find_spec` / 实跑）；不得用 RECORD、README、索引描述替代实测。
3. **先取证再动手**，结论附命令与原始输出；跑不了的标注"未验证"。
4. **破坏性操作必须可回滚**：先建缓存快照；修环境用「覆盖法」（只补不删）；禁用 `pip --force-reinstall`。
5. **用户的话同样是待验证输入**：先跑代码复验再采信，不通过就如实给实测数据。
6. **版本问题查官方手册与更新说明**；不涉及本项目实际调用的 API 则不做升级。

## 高危操作禁令（2026-09-19 根因取证结论）

本环境下**命令触发的删除逐个进回收站**（`genie-trash` 执行，实测 47~126 ms/文件 vs `cmd del` 0.74 ms/文件，慢 64~170 倍）→ 大包 `pip uninstall` / `--force-reinstall` 会超时被强杀 → 包半删（`~pkg` 残留）。
- **禁止**对大包执行 `pip uninstall` / `pip install --force-reinstall`；卸载 `opencv-python` 连带删共享 `cv2/`，卸载 `paddlepaddle`(CPU) 删共享 `paddle/` 树打死 `paddlepaddle-gpu`。
- 必须批量删除时先放大超时到 ≥1800 s 并建缓存；纯残留目录可走 `cmd /c rd /s /q` 快速通道。
- 取证工具：`F:\自动化验证工具\10-env-baseline\_tools\recycle_forensics.py` / `damage_check.py` / `analyze_waves.py` / `attribute_waves.py` / `watch_files.py` / `restore_from_wheels.py`。

## 缓存根（唯一）

`F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\cache-manager\temp-cache\`
（硬编码于 `cache-manager/scripts/make_cache.py` 的 `CACHE_ROOT`；AppData 侧不再作为缓存根，历史副本已合并回权威源）

## 五技能职责矩阵（默认启动技能）

| 技能名 | 用途 | 职责边界 | 依赖 | 加载方式 |
|---|---|---|---|---|
| local-dev-environment | 本机工具链 + 封板流程 + 绝对规则 | 只提供环境信息和标准命令 | 无 | AppData skills 目录 |
| parallel-serial-decider | 并行/串行判定 | 只判定和写日志，不做缓存 | → cache-manager | AppData skills 目录 |
| cache-manager | 缓存/回滚 | 只做快照和恢复 | 无（被调用） | AppData skills 目录 |
| feedback-logger | 事件流记录 | 只记录，不判定 | 无 | AppData skills 目录 |
| computer-use-automation | 本机 GUI / 桌面应用操作 | 只做界面操作与截图验证，不改项目代码 | → local-dev-environment | AppData skills 目录 |

## 调用链

```
判定（parallel-serial-decider）→ 建缓存/回滚（cache-manager）→ 写日志（parallel-serial-decider 决策日志 + feedback-logger 事件流）
                              ↘ 需要操作本机 GUI 时 → computer-use-automation
                              ↘ 需要工具链路径/打包时 → local-dev-environment
```

## 同步校验方法（每次改权威源后必须执行）

```bash
python -c "import os,hashlib; \
SRC=r'F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills'; \
APP=r'C:\Users\Administrator\.workbuddy\skills'; \
[print(n, hashlib.sha256(open(os.path.join(SRC,n,'SKILL.md'),'rb').read()).hexdigest()[:16], \
       hashlib.sha256(open(os.path.join(APP,n,'SKILL.md'),'rb').read()).hexdigest()[:16]) \
 for n in ['cache-manager','computer-use-automation','feedback-logger','local-dev-environment','parallel-serial-decider']]"
```

两边 SHA256 前 16 位一致即为同步成功；任一行不一致 = 该技能未同步。

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-19 | 复验加载机制为"实体目录副本"（更正原 junction 描述，两个 SKILL.md 同步更正）；缓存根归并为唯一路径；新增用户裁定的绝对规则 4 条 |
