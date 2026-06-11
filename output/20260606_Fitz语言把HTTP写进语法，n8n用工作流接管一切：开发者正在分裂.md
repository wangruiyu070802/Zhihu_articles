---
title: "Fitz语言把HTTP写进语法，n8n用工作流接管一切：开发者正在分裂"
summary: "1. 编程语言在“内化”一切，AI工具在“外化”一切——谁走对了？"
topics:
  - 人工智能
  - 科技前沿
cover: "https://raw.githubusercontent.com/wangruiyu070802/Zhihu_articles/main/output/images/cover_20260606_01.jpeg"
ai_generated: true
allow_gifts: false
content_source: "科技媒体综合整理"
publish_mode: draft
---

## 一、两个几乎同时发生的“奇怪”项目

6月初的Dev.to上，两个项目几乎同时登上了开发者讨论的热区。

第一个叫Fitz。一个用Rust写的新编程语言，它的核心卖点非常激进：HTTP路由、OpenAPI生成、JWT认证、密码哈希、Postgres ORM、WebSocket、定时任务……这些东西不再是需要import的库，而是**语言的语法本身**。

![文章配图](https://raw.githubusercontent.com/wangruiyu070802/Zhihu_articles/main/output/images/ill_20260606_1_01.jpeg)




你不需要搭FastAPI + SQLAlchemy + python-jose + Celery + Pydantic + alembic那一整套栈。Fitz的创造者Martin Palopoli说得很直白：这些东西应该活在语言内部（"live inside the language"）。

![文章配图](https://raw.githubusercontent.com/wangruiyu070802/Zhihu_articles/main/output/images/ill_20260606_2_01.jpeg)



第二个项目看起来完全相反。一个叫n8n的开源自动化工具，配上Google的Gemini模型，用来搭一个**自托管的新闻通讯系统**。用户不需要写代码，通过Webhook、拖拽节点、AI辅助就能完成从表单收集、邮件发送到订阅管理的全流程。

两个项目，一个在把功能往语言里塞，一个在把功能从代码中剥离。

这不是巧合。这是2026年开发者工具生态中正在发生的深层分裂。

## 二、“内化派”的逻辑：Fitz为什么选择这条路

先认真看看Fitz的野心。

Fitz是一个**渐进类型**的编译型语言，运行在Rust之上。它的核心假设是：现代后端开发的大部分工作，是反复组合固定的几个模式——路由、认证、数据库操作、消息队列、定时任务。这些模式被不同的库解决，但库与库之间的衔接、版本兼容、配置散落，恰恰是开发者效率的最大杀手。

**事实：** Fitz把以下功能做成了语言原语：
- HTTP路由（带路径参数、方法匹配）
- OpenAPI/AsyncAPI自动生成
- JWT签发与验证
- 密码哈希
- 一个纯Rust写的Postgres驱动ORM
- 数据库Schema迁移
- WebSocket
- Cron定时任务
- 后台任务
- CLI生成器
- 健康检查端点

这不是在造一个“更好的Python”或“更快的Go”。这是在造一种**面向特定问题域的专用语言**——后端服务的构建语言。

**我的判断：** Fitz代表了一股被低估的趋势——当通用语言的抽象能力到达极限，一部分开发者会选择“向下沉”，用更底层的语言能力来解决组合复杂度问题。Rust生态中Zig、Mojo等语言的崛起也是这一逻辑的延伸。

但Fitz目前还只是一个早期项目。它的成功取决于：编译器质量、生态建设、以及开发者是否愿意为一套新语法放弃已有的库生态。

## 三、“外化派”的逻辑：为什么n8n代表另一种答案

再看n8n那条线。

素材[1]详细描述了如何用n8n + Gemini搭建一个自托管的新闻通讯系统。关键点不是技术细节，而是**设计哲学**：

- **Webhook代替API调用**：前端表单直接提交到n8n的Webhook，不需要写后端路由
- **AI辅助代替手写逻辑**：Gemini负责内容生成、分类、摘要
- **数据库操作封装在节点里**：upsert、订阅管理、去重，全部可视化配置
- **零平台锁定**：自托管，数据所有权100%归用户

这不是“低代码”的旧故事。这是**AI时代的工作流抽象**——把开发者的工作拆解成“触发-处理-存储”的原子单元，每个单元由AI或预制节点完成。

**事实：** 素材[3]中的Feather Engine走得更远——一个基于Three.js的开源游戏引擎，让开发者通过**AI提示**来控制游戏系统，而不是手动编写所有逻辑。Feather Engine的创始人Mario J.说得更直接：“目标是让开发者通过AI提示控制游戏系统，而不是手动连接一切。”

**我的判断：** “外化派”不是在消灭代码，而是在重新定义“谁在写代码”。当AI能够完成CRUD、邮件发送、数据库操作这些标准化工作时，开发者从“写代码的人”变成“定义流程的人”。这个转变对生产力提升是真实的，但它也带来了新的问题——素材[162]明确指出：当团队中的一个人纠正了AI Agent，这个改进不会自动传递给团队其他成员。每个成员都在训练“同一个”Agent的不同版本。

## 四、统一逻辑：都在回答同一个问题

表面上看，Fitz和n8n走的是相反的路。一个把所有东西塞进编译器，一个把所有东西拖出编辑器。

但它们的底层动机完全相同：**降低后端开发中的组合复杂度**。

传统后端开发的痛点不是“写不出某个功能”，而是“把这些功能拼在一起太累”。你要处理库版本冲突、中间件顺序、认证与路由的耦合、数据库连接池的生命周期、异步任务的错误处理……这些不是业务逻辑，是**系统粘合逻辑**。

Fitz的解法：把粘合逻辑变成语言特性，编译器替你管理。
n8n的解法：把粘合逻辑变成可视化工作流，运行时替你管理。

**殊途同归。** 两者的目标都是让开发者（或更广泛意义上的“系统构建者”）把注意力从“怎么把这些东西接起来”转移到“这些东西应该做什么”。

这不仅仅是技术路线选择，它反映了更深层的产业变化：**后端开发的瓶颈，已经从“性能”转向了“组合”**。

## 五、这不是二选一，这是分工重组

很多人会问：Fitz和n8n，哪个代表了未来？

**我的判断是：这个问题问错了。**

真正正在发生的是开发者的**分工重组**：

- **系统程序员**继续向底层走，用Fitz、Zig、Rust构建基础设施级别的抽象，把路由、认证、数据库操作“内化”到语言层面。他们关心的是性能、安全、可审计性。

- **应用构建者**向高层走，用n8n、Feather Engine、AI Agent构建业务流程，把技术实现“外化”为工作流。他们关心的是速度、迭代、业务适配。

这两类人需要不同的工具，而工具生态正在响应这种分化。

如果你去看素材[5]中Trae（字节跳动的AI IDE）的表现——“用中文描述功能，得到完整CRUD模块”——你会发现它本质上是一个“外化派”工具，但它服务的是“内化派”的受众：会写代码的人，只是不想写重复代码。

**事实：** 素材[174]中Supabase在8个月内估值翻倍到100亿美元，创始人明确表示“很大程度上受益于Claude、Codex等AI工具的助力”。Supabase本身是一个“外化”数据库服务，但它的用户是“内化”的开发者。

## 六、收束：2026年的开发者，需要学会“跨层思考”

回到文章开头那两篇Dev.to文章。Fitz的作者在介绍语言时写了一段话：“与其在Python上堆FastAPI + SQLAlchemy + python-jose + Celery + Pydantic + uvicorn + Alembic + typer，不如让这些问题活在语言内部。”

n8n的作者写的是：“自定义工作流打败平台锁定，给你100%的数据所有权、自定义样式控制和零平台费用。”

两句话，同一个敌人：**不必要的复杂性**。

只是一个人选择在编译器中消灭它，另一个人选择在工作流中消灭它。

对于2026年的开发者，最有价值的不是站队，而是理解这两种思路各自的适用范围：

- 如果你在构建一个需要长期维护、高安全要求、团队规模大的系统，**内化派**的思路（语言级抽象、强类型、编译时检查）是更可靠的选择。

- 如果你在快速验证想法、搭建MVP、或处理多变的业务流程，**外化派**的思路（工作流自动化、AI辅助、可视化编排）是更高效的选择。

**最后一句个人判断：** 真正聪明的团队，不会只选一条路。他们会把核心系统用“内化”的方式做深，把外围流程用“外化”的方式做快。2026年开发者工具的真正进化，不是某个工具的胜利，而是**跨层思考能力的普及**。

### 参考来源
- [1] Building a Self-Hosted Newsletter Setup with n8n & Gemini, Dev.to
- [2] Presentando Fitz: un lenguaje donde HTTP, Postgres, JWT y WebSockets son parte de la sintaxis, Dev.to
- [3] Building an AI game engine with Three.js, Dev.to
- [4] Introducing Fitz: a language where HTTP, Postgres, JWT, and WebSockets are part of the syntax, Dev.to
- [5] Why Trae Keeps Topping the Juejin AI Coding Tools List, Dev.to
- [162] AI agents are learning on the job — just not for your whole team, VentureBeat
- [174] Supabase doubles valuation to $10B in 8 months, TechCrunch