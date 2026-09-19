# -*- coding: utf-8 -*-
"""core 包 — P2 七层架构中的公共层（P2-3 建立）。

当前内容：
  - `core.constants`：跨模块共享常量（单源，避免多处各维护一份名单）
  - `core.utils`：公共工具函数（JSON / 键码 / 进程 / GPU / 配置读写）

供 contracts、env_adapter、P1-toolbox-legacy/scripts、testbar-console 共同引用，
取代此前"同一能力多处各自实现"的状态（详见 P2-3 单源化清单）。
"""
