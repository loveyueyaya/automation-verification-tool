# -*- coding: utf-8 -*-
"""core/constants.py — 跨模块共享常量（单一来源）。

P2-3 单源化清单 #1：此前远控软件名单存在两份且互相缺失 ——
  - testbar.py:90  REMOTE_PROCS     = wujie/sunloginclient/todesk/anydesk/rper/uu/mstsc/qclient（8 项）
  - env_probe.py:23 REMOTE_SOFTWARE = wujie/sunloginclient/todesk/anydesk/teamviewer/向日葵/wujie2（7 项）
现合并为并集 11 项，两边统一引用本常量。
比对口径：进程名（去扩展名、转小写）相等即命中。
"""
REMOTE_SOFTWARE = (
    "wujie", "wujie2", "sunloginclient", "todesk", "anydesk",
    "teamviewer", "向日葵", "rper", "uu", "mstsc", "qclient",
)
