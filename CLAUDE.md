# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

知乎文章 (Zhihu Articles) — 基于 Agent Team 的 7x24 知乎科技前沿内容系统。4 个独立 agent 通过 SQLite 任务队列协作：采集 → 筛选 → 写作 → 发布。

## Quick Start

```bash
# 测试一轮（采集→筛选→写作→发布指令）
manage.bat once

# 7x24 后台运行
manage.bat start

# 查看状态
manage.bat status

# 注册每小时定时任务
manage.bat install

# 单次流程（不用 agent team）
.venv/Scripts/python main.py
```

## Agent Team 架构

```
                         ┌──────────────────┐
                         │   Orchestrator   │  7x24 循环调度
                         │  (orchestrator)  │  默认每1小时唤醒一轮
                         └────────┬─────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             ▼                    ▼                    ▼
     ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
     │ Collector    │    │  Screener    │    │   Writer     │
     │ Agent        │───▶│  Agent       │───▶│   Agent      │
     │ (RSS 采集)   │    │ (AI 筛选)    │    │ (AI 写作)    │
     └──────────────┘    └──────────────┘    └──────┬───────┘
                                                    │
                                             ┌──────▼───────┐
                                             │  Publisher   │
                                             │  Agent       │
                                             │ (Tabbit 指令) │
                                             └──────────────┘
```

每个 agent 独立运行，通过 SQLite 数据库传递任务状态：

| Agent | 任务 | 频率 | 输入 → 输出 |
|-------|------|------|------------|
| **Collector** | RSS 采集 | 每 6 小时 | 网络 → `article_sets` |
| **Screener** | AI 筛选+打分 | 每轮 | `articles` → `screening_results` |
| **Writer** | 生成文章 | 每轮 | 素材 → `output/*.md` |
| **Publisher** | 生成发布指令 | 每轮 | 文章 → `*_发布指令.md` |

## Project Structure

```
├── agent_team/                  # Agent Team 核心
│   ├── orchestrator.py          # 7x24 编排器（主循环）
│   ├── database.py              # SQLite 任务队列
│   ├── base_agent.py            # Agent 基类
│   ├── collector_agent.py       # 采集 Agent
│   ├── screener_agent.py        # 筛选 Agent
│   ├── writer_agent.py          # 写作 Agent
│   └── publisher_agent.py       # 发布 Agent
├── main.py                      # 单次流程（兼容旧用法）
├── collector/                   # RSS 采集模块
├── writer/                      # AI 写作模块
├── publisher/                   # 发布模块
├── output/                      # 文章输出
├── data/                        # SQLite 数据库
├── manage.bat                   # 一键管理脚本
├── .env.example
└── requirements.txt
```

## Content Rules

- 禁止搬运，必须是原创整理和分析
- 排除未经验证爆料、营销软文、二手转述
- 区分事实、推测和个人判断
- 图片用保守策略：优先官方图或 AI 生成图

## 管理命令

```bash
manage.bat start       # 后台 7x24 运行
manage.bat stop        # 停止
manage.bat status      # 查看运行状态和统计
manage.bat once        # 执行一轮（测试用）
manage.bat install     # 注册 Windows 定时任务（每小时）
manage.bat remove      # 移除定时任务
```
