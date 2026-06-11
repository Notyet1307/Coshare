## 1. 修正后的总体建议

你们的方向仍然成立，但我会把落地顺序改得更保守：

```text
阶段 1：milestone doc 为主任务源
        Codex Direct Mode + 少量 Subagent Mode
        DeepSeek V4 Pro 作为独立 reviewer / spec critic
        Bridge 只做 task contract、evidence gate、closeout

阶段 2：接 GitHub Issue/PR/CI
        GitHub issue 成为执行票据或部分任务源
        PR / CI / branch protection 成为代码事实源
        AI Reviewer / AI Verifier 接入 PR gate

阶段 3：接 Multica
        Multica 作为 agent 执行看板、运行时分配、阻塞状态汇报层
        不作为最终验收事实源

阶段 4：接内网 GitLab
        Bridge 通过 WorkItem adapter 抽象 GitHub Issue / GitLab Issue / Multica Issue
```

核心判断：

1. **当前不应急着把 Multica 做成主状态中心。**
   Multica 的价值是 agent 执行编排和可视化，不是最终工程验收。它的 server 存 workspace、issue、comment、task queue、agent definitions；实际 agent 在你们自己的机器上由 daemon 调用本地 Codex、Claude Code 等工具执行，server 不执行 agent task。([Multica][1])

2. **你们应该先把“任务契约”和“验收证据”标准化，而不是先做完整平台集成。**
   你们现在最大风险不是缺看板，而是：AI 说完成了、issue 说 done、PR/CI 说 failed、handoff 没更新。Bridge 的第一职责是防止这类状态冲突。

3. **初期主任务源建议继续用 milestone doc。**
   因为你们是通用 Codex 模板，不是单一 GitHub 项目。milestone doc 更适合做 backend-neutral contract。GitHub issue 可以晚一点成为任务源，但不应一开始就强绑定，否则未来接 GitLab 会增加迁移成本。

4. **AI Reviewer / AI Verifier 可以作为主要机制，但必须被 deterministic evidence 约束。**
   AI 的结论不能单独算证据。Verifier 的证据应该是命令、退出码、CI 状态、commit SHA、环境信息；Reviewer 的证据应该是 diff 范围、文件行号、风险等级、是否存在 unresolved P0/P1。

5. **Multica Cloud 可以用于低敏 POC，自建适合正式内网/公司项目。**
   Multica Cloud 不直接拿代码和本地 API keys，但 issue body、agent comment、task metadata 仍会出现在第三方服务。自建 Multica 主要保护这些“协作元数据”，不自动解决 Codex / DeepSeek 模型调用的数据边界。

---

## 2. 自建 Multica vs Cloud / 托管服务决策矩阵

### 结论先给

你们当前约束下，推荐：

```text
个人 / 非敏感 POC：Multica Cloud 可用
公司开发流程试点：优先自建
涉及内网 GitLab、VPN、内部 URL、客户信息、日志片段：必须自建或暂缓引入 Multica
```

Multica Cloud 的优势是启动快：官方 cloud quickstart 设计为注册、装 CLI、启动 daemon、创建 agent、分配任务的快速流程；daemon 会在本地检测 AI coding tools 并轮询任务。([Multica][2])
Self-host 的优势是 Multica server 层数据在你们控制下，包括 workspace、issues、comments、agent 配置；但 agent 执行仍然依赖本地 daemon 和本机 AI coding tools，self-host 替换的是 server 层，不是执行层。([Multica][3])

### 决策矩阵

| 场景                                   | Cloud 是否够用 | 自建必要性 | 判断                         |
| ------------------------------------ | ---------: | ----: | -------------------------- |
| 个人项目、开源项目、无敏感 issue/comment          |          高 |     低 | Cloud 足够做 POC              |
| 只想验证 Multica 是否能降低 agent 协调成本        |          高 |     低 | 先 Cloud，别先背运维              |
| issue body 可能包含内部系统名、内网 URL、客户名、错误日志 |          低 |     高 | 建议自建                       |
| agent 通过 VPN 访问公司内网                  |         中低 |     高 | 自建更稳，但还要做本机权限隔离            |
| 后期接内网 GitLab                         |          低 |     高 | 自建或等 GitLab adapter 成熟     |
| 公司要求任务、评论、agent 配置不能外发               |          低 |    必须 | 自建                         |
| 需要内部 SMTP、内部登录策略、注册白名单               |         中低 |     高 | 自建更合适                      |
| 团队没有人维护 PostgreSQL、备份、升级、TLS、监控      |          高 |     低 | Cloud 或暂缓引入 Multica        |
| 只使用 Codex + GitHub，任务量不大             |         中高 |     低 | GitHub Issues + Codex 可能够用 |
| 多 agent / 多模型 / 多工具池长期并行             |          中 |    中高 | Multica 价值上升               |

### 自建收益

自建 Multica 的安全收益主要是：

```text
Multica workspace / issue / comment / task queue / agent config 不出组织边界
可以接内部 SMTP / 内部反向代理 / 内部域名 / 内部访问控制
可以自行做 DB backup、审计、日志保留、网络隔离
```

但要注意边界：**自建 Multica 不等于“代码和 diff 不出组织”。** Codex、DeepSeek 或其他 coding tool 在执行时仍可能把上下文、diff、错误日志发给对应模型服务。Multica 文档只说明 server 不执行 agent task、代码目录和 API keys 保留在本机；并不代表底层模型供应商不接收 prompt/context。([Multica][1])

### 自建成本

POC 看起来很轻，官方文档说明 self-host 可以用 Docker 启动 backend、frontend、PostgreSQL；`make selfhost` 会生成 `.env`、拉镜像、启动 docker compose、等待 health endpoint。([Multica][3])

生产化成本不是 10 分钟，至少包括：

| 成本项           | 说明                                                                                                    |
| ------------- | ----------------------------------------------------------------------------------------------------- |
| PostgreSQL 运维 | 备份、恢复演练、升级、磁盘告警                                                                                       |
| TLS / 反向代理    | 官方 self-host 默认 loopback 绑定，跨机器访问要反向代理和 TLS；不能把 Postgres/secret 暴露公网。([Multica][3])                   |
| 环境变量治理        | 生产必须显式配置 `DATABASE_URL`、`JWT_SECRET`、`APP_ENV=production`、`FRONTEND_ORIGIN`，并保持开发验证码为空。([Multica][4]) |
| 登录和注册策略       | 需要配置邮箱验证码、Google OAuth 或内部 SMTP；self-host/on-prem 场景可用 SMTP relay，避免邮件流量出内网。([Multica][5])            |
| 注册白名单         | 要限制谁能注册，避免内部工具变成开放入口。([Multica][6])                                                                   |
| token 策略      | PAT 权限很宽，daemon 生产应使用 daemon token，避免给 daemon 全用户权限。([Multica][7])                                    |
| secret 管理     | Multica `custom_env` 的值存于 server DB plaintext；不能放生产 DB 密码、root token、高价值云 AK。([Multica][8])           |
| 版本升级          | 数据库迁移、镜像版本、回滚策略                                                                                       |
| 安全监控          | 登录异常、agent 异常任务、内网访问异常                                                                                |
| 数据生命周期        | issue/comment/task log 保留多久，谁能导出                                                                      |

### 推荐部署策略

```text
POC 1：
Cloud，非敏感 repo，验证流程价值。

POC 2：
本机或内网 VM self-host，验证运维和权限边界。

正式使用：
只要接入公司 repo、VPN、内网 GitLab、内部 URL 或客户日志，转 self-host。
```

---

## 3. VPN / 内网访问下的 agent 权限边界

你们给出的关键信息是：**agent 可以通过 VPN 访问公司内网。**
这意味着风险从“代码仓库权限”扩大到“内网横向访问权限”。

### 基本原则

```text
不要让 agent 继承人的全部本机权限。
不要让 prompt 充当安全边界。
不要让 Builder 拥有生产网络、生产凭据、main branch 写权限。
```

agent 在 VPN 环境下的实际权限通常等于：

```text
本机 shell 权限
+ 当前用户的 SSH/Git 凭据
+ VPN 后可达的内网网段
+ 环境变量里的 token
+ 浏览器/CLI/credential helper 中缓存的凭据
+ repo、测试配置、日志中暴露的 secret
```

### 推荐边界设计

#### A. 网络边界

| 控制     | 建议                                              |
| ------ | ----------------------------------------------- |
| VPN 账号 | 给 agent 单独的低权限 VPN 身份，不复用人工账号                   |
| 网络可达范围 | 只允许访问 Git、artifact registry、测试环境、必要依赖源          |
| 禁止访问   | 生产数据库、生产控制台、客户生产环境、堡垒机、内部管理后台                   |
| 出口代理   | agent 流量走可审计 proxy，记录目的域名/IP                    |
| DNS    | 不允许 agent 随意解析内部全部域名                            |
| 测试环境   | Functional Test 只能访问 staging / sandbox，不访问 prod |

#### B. 主机边界

| 控制                | 建议                                                    |
| ----------------- | ----------------------------------------------------- |
| 系统用户              | agent 使用独立 OS 用户                                      |
| HOME 目录           | 独立 HOME，不挂载个人 `~/.ssh`、`~/.aws`、`~/.kube`、浏览器 profile |
| 容器 / VM           | 高风险任务在 devcontainer、VM、sandbox 中跑                     |
| 文件挂载              | Builder 只挂载目标 repo；Verifier/Reviewer 用只读 checkout     |
| credential helper | 禁止继承个人 Git credential helper                          |
| SSH agent         | 默认不转发 SSH agent                                       |
| 临时目录              | 每个 task 独立 workspace，完成后清理                            |

#### C. Git 权限

你们公司已有 branch protection、required CI、CODEOWNERS，这很好。GitHub protected branch 可以要求 PR approval 和 status checks；required status checks 必须是 successful、skipped 或 neutral 后才能合并。([GitHub Docs][9]) CODEOWNERS 也可以配合 branch protection 要求特定路径的 owner review。([GitHub Docs][10])

对 agent 建议：

| 角色              | Git 权限                                        |
| --------------- | --------------------------------------------- |
| Builder         | 只能 push feature branch，不能 push main           |
| Test            | 可改 tests / fixtures，不能改核心逻辑，除非任务明确授权          |
| Verifier        | 无写权限；只读 checkout；运行命令                         |
| Reviewer        | 无写权限；只能评论 PR 或生成 report                       |
| Functional Test | 最好无 repo 访问；只访问 artifact / staging            |
| Docs            | 只能改 `docs/milestones/**`、必要时改 `docs/agent/**` |
| Integration     | 可跨范围整合，但必须走 PR + gate                         |

对后期 GitLab：GitLab protected branches 可控制谁能 push/merge、强制 code review / approval、管理 Code Owner approval；Code Owners 可与 protected branch 结合，要求特定路径 owner 审批。([GitLab Docs][11])

#### D. Secret 边界

最小规则：

```text
禁止 agent 读取或使用生产 secret。
禁止把高价值 secret 放 Multica custom_env。
禁止把公司长期 token 放 issue body / comment / prompt。
```

Multica `custom_env` 适合放低权限、短期、可轮换的 agent credential；不适合放生产 DB 密码、root token、高价值云 AK，因为值会以 plaintext 形式存在 server DB 中。([Multica][8])

#### E. Stop conditions

所有角色任务模板里都应强制写：

```md
Stop and report blocker if:
- task requires production credentials
- task requires accessing customer data
- task requires touching forbidden paths
- task requires modifying branch protection / CI policy
- task requires changing auth, billing, encryption, audit, or deployment controls without explicit acceptance criteria
- VPN-only resource is unavailable or unexpectedly broad
```

---

## 4. 只用 Codex + DeepSeek V4 Pro 的初期 worker / role 设计

你们初期主要用 Codex，DeepSeek V4 Pro 辅助。这个组合下，不建议一开始建很多 worker。先用 **4+1** 角色：

```text
1. Orchestrator / PM：Codex 主会话
2. Builder：Codex
3. Test Builder：Codex
4. Reviewer：DeepSeek V4 Pro + Codex PR review
5. Verifier：Codex 执行命令，但证据以命令/CI为准
可选：Functional Tester，按任务类型启用
```

Codex 当前支持 subagent workflow，可显式生成专门 agent 并等待其结果；subagent 也会继承当前 sandbox policy，所以安全边界仍要靠 sandbox/权限，而不是只靠角色说明。([OpenAI Developers][12]) Codex 的 GitHub code review 能按 `AGENTS.md` 中的 review guidelines 审查 PR diff，并重点报告严重问题。([OpenAI Developers][13]) DeepSeek V4 Pro 官方说明为 1.6T total / 49B active 参数、支持 1M context，并强调 coding / reasoning / agentic coding 能力；它也支持 OpenAI ChatCompletions 与 Anthropic APIs。([DeepSeek API Docs][14])

### 初期角色分配

| 角色                | 工具               | 职责                                | 禁止事项                              |
| ----------------- | ---------------- | --------------------------------- | --------------------------------- |
| Orchestrator      | Codex            | 拆任务、判断 Direct/Subagent、派发、汇总 gate | 不直接大范围改代码                         |
| Builder           | Codex            | 实现功能，小步提交                         | 不改 forbidden paths，不关闭自己的 blocker |
| Test Builder      | Codex            | 增补单测、集成测试、fixture                 | 不改业务逻辑，除非明确授权                     |
| Verifier          | Codex + shell/CI | 运行固定命令，收集 evidence                | 不改代码；若产生 diff，结果无效                |
| Reviewer-A        | Codex review     | PR diff 高信号审查                     | 不直接修复，除非另开 Builder task           |
| Reviewer-B        | DeepSeek V4 Pro  | 对抗性审查：scope、架构、安全、遗漏测试            | 不直接改代码                            |
| Functional Tester | Codex 或 DeepSeek | 黑盒/灰盒验收                           | 不读实现细节，不基于 builder summary 放行     |
| Docs / Closeout   | Codex            | 写 handoff / closeout              | 不篡改 evidence，不把 pending 写成 done   |

### 为什么 DeepSeek 不建议初期做 Builder 主力

不是因为能力不足，而是工程集成风险：

* Codex 对你们现有 Codex 模板、AGENTS.md、subagents、GitHub review 更自然；
* DeepSeek 更适合做长上下文、独立视角、对抗性 review；
* 若 DeepSeek 通过 API wrapper 接入，本地 tool execution、权限隔离、文件修改控制要额外验证；
* 初期最重要的是流程闭环，不是模型池最大化。

推荐组合：

```text
Builder：Codex
Test Builder：Codex
Verifier：Codex 触发 deterministic commands
Reviewer 1：Codex PR review
Reviewer 2：DeepSeek V4 Pro adversarial review
Functional Test：能黑盒时 Codex 或 DeepSeek 均可，优先不给源码
```

---

## 5. Functional Test 是否应该坚持黑盒

### 建议：坚持“黑盒优先”，但允许分级降级

Functional Test 的价值在于独立性。完全黑盒不是所有任务都可行，但应把它作为最高等级，而不是口号。

### Functional Test 分级模型

| 等级    | 名称     |                          源码可见性 | 适用场景                  |     可信度 |
| ----- | ------ | -----------------------------: | --------------------- | ------: |
| FT-L0 | 真黑盒    |   无源码、无 diff、无 builder summary | Web/API/CLI/SDK 有稳定入口 |       高 |
| FT-L1 | 接口黑盒   | 可看用户文档 / OpenAPI / README，不看实现 | API、CLI、SDK、前端流程      |      中高 |
| FT-L2 | 灰盒验收   |            可看测试入口和部署说明，不看 diff | 本地项目无法脱离 repo 运行      |       中 |
| FT-L3 | 独立场景复核 |  可看 milestone acceptance，不运行系统 | 纯重构、底层库、无可运行环境        |      中低 |
| FT-L4 | 不启用 FT |                              无 | 文档、构建脚本、小范围内部重构       | 无 FT 证据 |

### 应坚持黑盒的场景

| 场景                | 原因                                     |
| ----------------- | -------------------------------------- |
| 用户可见功能            | 最终行为比实现解释更重要                           |
| API 兼容性           | 可以用 HTTP request / OpenAPI scenario 验收 |
| CLI 工具            | 可以用命令行输入输出验收                           |
| SDK / library     | 可以用 public API 示例项目验收                  |
| 登录、权限、审计、计费等高风险路径 | Builder 自测不够                           |
| bugfix            | 黑盒复现用例最有价值                             |

### 不适合完全黑盒的场景

| 场景          | 替代                                                  |
| ----------- | --------------------------------------------------- |
| 纯内部重构       | Reviewer + Verifier + regression tests              |
| 性能优化        | benchmark evidence + Reviewer                       |
| 类型系统 / 架构调整 | static check + targeted tests + architecture review |
| CI/CD 配置变更  | pipeline dry-run + restricted environment           |
| 安全修复        | security reviewer + exploit/regression test，必要时灰盒   |
| 无稳定运行入口     | FT-L2 或 FT-L3                                       |

### 实现方式

#### Web / API

```text
输入：
- staging URL
- 测试账号
- 允许操作范围
- acceptance scenarios
- negative scenarios
- expected observable behavior

禁止：
- repo path
- PR diff
- Builder summary
- implementation notes
```

#### CLI

```text
CI build artifact → 临时目录安装 → 运行命令 → 比较 stdout/stderr/exit code/filesystem output
```

#### Library / SDK

```text
创建一个最小 example project
只通过 public API 调用
不 import internal modules
不读取源码实现
```

#### 本地服务

```text
Builder 产出启动命令和 seed data
Functional Tester 只拿启动入口和用户场景
无法脱离 repo 时，至少禁止读取 diff 和实现文件
```

### 降级但保持独立性的规则

当不能完全黑盒时，仍要保留三条：

```text
Functional Tester 不读 Builder 的“我做了什么”总结。
Functional Tester 不以单测通过为验收结论。
Functional Tester 的结论必须来自独立场景执行或独立规格检查。
```

---

## 6. AI Reviewer / AI Verifier 的可靠性边界与最小证据标准

### 基本判断

AI Reviewer 和 AI Verifier 可以成为你们主要机制，但不能成为唯一事实。合理表达是：

```text
AI Reviewer 给出审查判断。
AI Verifier 调度和解释验证命令。
真正的证据来自 diff、命令、退出码、CI、日志、artifact、commit SHA。
```

### AI Verifier 的边界

AI Verifier 不应“相信自己跑过测试”。必须输出结构化 evidence。

最小 evidence：

```yaml
verifier_evidence:
  task_id: M1-T03
  commit: <full_sha>
  branch: agent/M1-T03-...
  environment:
    os: ...
    runtime: ...
    package_manager: ...
    dependency_lock_hash: ...
  commands:
    - command: "npm test -- --runInBand"
      exit_code: 0
      started_at: ...
      duration_sec: ...
      stdout_excerpt: ...
      stderr_excerpt: ...
  ci:
    provider: github-actions | gitlab-ci | local
    run_url: ...
    status: passed | failed | skipped | unavailable
  pre_post_diff_check:
    before_tree_status: clean
    after_tree_status: clean
  conclusion: pass | fail | inconclusive
  blocker: null
```

硬规则：

```text
exit_code 非 0 → fail
命令没跑 → inconclusive，不是 pass
Verifier 产生代码 diff → evidence invalid
CI failed → fail
CI unavailable 且任务风险 medium/high → inconclusive
只写“测试通过”无命令 → invalid
```

### AI Reviewer 的边界

AI Reviewer 容易漏问题，尤其是：

* 复杂业务语义；
* 并发 / race condition；
* 权限绕过；
* 依赖版本和供应链风险；
* 测试假阳性；
* 大 diff 中的细节遗漏；
* prompt 中没强调的非功能需求。

最小 evidence：

```yaml
reviewer_evidence:
  task_id: M1-T03
  reviewer: codex-review | deepseek-v4-pro | other
  model_or_tool_version: ...
  base_sha: ...
  head_sha: ...
  diff_scope:
    files_changed:
      - path: ...
        status: modified
  checklist:
    scope_match: pass | fail | unknown
    forbidden_paths: pass | fail
    tests_added_or_updated: pass | fail | not_applicable
    security_risk: pass | fail | unknown
    error_handling: pass | fail | unknown
    backward_compatibility: pass | fail | unknown
    observability: pass | fail | not_applicable
  findings:
    - severity: P0 | P1 | P2 | P3
      file: ...
      line: ...
      issue: ...
      required_action: ...
  conclusion: pass | fail | pass_with_risk | inconclusive
```

硬规则：

```text
任何 unresolved P0/P1 → fail
Reviewer 无法定位到文件/行或具体风险 → 不算 blocking finding，但也不能算强 pass
Reviewer 没检查 forbidden paths → inconclusive
Reviewer 与 Builder 是同一模型同一上下文 → 不能作为唯一 review
Reviewer pass 但 Verifier fail → fail
Reviewer pass 但 Functional Test fail → fail
```

### 推荐双 reviewer 策略

```text
Reviewer-A：Codex PR review
- 看 diff
- 遵循 AGENTS.md review guidelines
- 重点找严重问题

Reviewer-B：DeepSeek V4 Pro adversarial review
- 看 task contract + diff + acceptance
- 重点找 scope drift、遗漏测试、安全边界、兼容性问题
```

Codex GitHub code review 能读取 PR diff、遵循仓库指导，并发布标准 GitHub review。([OpenAI Developers][13]) DeepSeek V4 Pro 的 1M context 和 coding/reasoning 能力适合做第二视角长上下文审查，但它的结论仍必须落到具体 finding 和 evidence。([DeepSeek API Docs][14])

---

## 7. milestone doc 主任务源 vs GitHub issue 主任务源 vs 双轨过渡

这是你们当前最重要的架构选择。

### 方案 A：milestone doc 作为主任务源

```text
docs/milestones/M1.md 是 canonical task spec
GitHub issue / Multica issue 是执行镜像
```

#### 优点

| 优点              | 说明                                   |
| --------------- | ------------------------------------ |
| backend-neutral | 后续接 GitHub、GitLab、Multica 都不改任务模型    |
| 适合模板            | 通用 Codex 模板不依赖某个平台                   |
| 支持本地 repo       | 无远程 issue 系统也能跑                      |
| 容易 code review  | 任务变更本身通过 git diff 审查                 |
| handoff 稳定      | 跨 session 可读，不依赖聊天和平台状态              |
| 适合长期复杂项目        | scope、risk、acceptance 放 repo 更贴近代码演进 |

#### 缺点

| 缺点      | 说明                             |
| ------- | ------------------------------ |
| 运行态差    | 讨论、阻塞、执行进度不如 issue 系统          |
| 并发编辑弱   | 多 agent 同时改 milestone doc 容易冲突 |
| UI 弱    | 看板、assignee、label、状态筛选都弱       |
| 自动化成本高  | 需要 Bridge 解析 Markdown          |
| 容易过度文档化 | 小任务也可能被写成重流程                   |

#### 适用

你们当前阶段非常适合：

```text
本地 repo / GitHub 混用
后期可能 GitLab
通用模板优先
Direct Mode 占多数
复杂项目才启用 Subagent
```

### 方案 B：GitHub issue 作为主任务源

```text
GitHub issue 是 canonical task spec
milestone doc 只做索引 / 汇总 / handoff
```

GitHub Issues 原生用于计划、讨论和跟踪工作，支持 sub-issues、issue dependencies、labels、milestones，并能和 PR 通过引用和关键词关联。([GitHub Docs][15])

#### 优点

| 优点      | 说明                                               |
| ------- | ------------------------------------------------ |
| 执行协作强   | comment、assignee、label、milestone、dependency 原生支持 |
| PR 集成好  | issue ↔ PR ↔ CI ↔ review 关联清晰                    |
| 自动化成熟   | webhook、REST/GraphQL、GitHub CLI 都可用              |
| 团队可见性好  | 看板、通知、项目视图、筛选好                                   |
| 适合后期团队化 | 多人/多 agent 共同维护更自然                               |

#### 缺点

| 缺点               | 说明                                        |
| ---------------- | ----------------------------------------- |
| 平台锁定             | 后期接 GitLab 要做迁移或 adapter                  |
| 本地 repo 不友好      | 离线/本地项目没有 issue 系统                        |
| 结构化约束弱           | issue body 是 Markdown，自由编辑导致 schema drift |
| 容易和 repo docs 漂移 | issue 改了 scope，milestone doc 未同步          |
| 模板复杂化            | 通用模板需要内置 GitHub 假设                        |

#### 适用

适合你们后期：

```text
正式团队协作
GitHub branch protection / CI / CODEOWNERS 完整启用
PR 是主要交付入口
每个 task 都需要讨论、阻塞、状态跟踪
```

### 方案 C：双轨过渡

这是我推荐的路径，但必须强调：**双轨不是双主。**

```text
每个 task 有且只有一个 canonical owner。
另一个系统只保存 mirror / execution reference。
```

#### 推荐状态

阶段 1：

```text
canonical task spec：milestone doc
execution ticket：GitHub issue 或 Multica issue
code result：PR / CI
final handoff：repo docs
```

阶段 2：

```text
canonical task spec：GitHub issue
milestone doc：milestone index + acceptance summary + closeout
Multica issue：agent execution ticket
```

阶段 3：

```text
canonical task spec：WorkItem adapter
backend：GitHub issue / GitLab issue
repo docs：stable governance + milestone closeout
```

### 如何避免迁移成本和事实源混乱

#### 1. 从第一天引入稳定 `task_id`

不要用 GitHub issue number、Multica issue key 做主 ID。

```yaml
task_id: M1-T03
canonical: repo-doc
revision: 4
backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
```

#### 2. 每个 task 明确 canonical owner

```yaml
canonical_owner: repo-doc | github-issue | gitlab-issue
```

规则：

```text
canonical_owner = repo-doc：
  scope / acceptance / allowed_paths 只能改 milestone doc。
  GitHub issue body / Multica issue body 是生成镜像。
  issue comment 里的 scope change 只能变成 proposed_change，不自动生效。

canonical_owner = github-issue：
  scope / acceptance 只能改 GitHub issue body。
  milestone doc 只保留摘要和链接。
```

#### 3. Bridge 必须检测漂移

```text
repo doc revision = 4
GitHub issue embedded revision = 3
→ stale mirror，Bridge 提示 update issue body

GitHub issue body 被手工改了 acceptance
canonical_owner = repo-doc
→ conflict，不自动回写 doc
```

#### 4. 迁移时冻结旧任务体

从 milestone doc 迁到 GitHub issue 时，不要删除原 task。改成：

```md
### M1-T03: Auth timeout handling

Canonical source: GitHub Issue #123
Migrated at: 2026-06-11
Previous revision: 5
Current status: tracked externally
```

#### 5. 不做双向实时同步

建议只做：

```text
repo-doc → issue body：允许 upsert
issue comments → blocker / evidence：允许 pull
issue body → repo-doc：禁止自动写回，除非人工确认迁移
```

### 我的推荐路径

```text
现在：
milestone doc 主任务源。

1–2 个月后：
GitHub issue 作为执行票据，不是主任务源。

团队规模和 PR 流程稳定后：
GitHub issue 可成为 task-level canonical source。
milestone doc 降级为 milestone index / closeout / handoff。

接 GitLab 前：
保持 task_id 和 WorkItem adapter，避免 GitHub issue number 渗透进任务模型。
```

---

## 8. 更贴近你们情况的 1–2 周 POC 计划

### POC 总目标

验证四件事：

```text
1. milestone doc 主任务源是否可行
2. Codex + DeepSeek 双 reviewer 是否能提升质量
3. AI Verifier / Reviewer gate 是否能拦住失败状态
4. Multica 是否值得引入，cloud 与 self-host 成本差异如何
```

### POC 范围选择

选一个低敏 repo，最好具备：

```text
- 一个小功能
- 一个 bugfix
- 一个测试补充
- 一个文档 closeout
- 一条 GitHub Actions 或本地 test command
```

主动植入失败场景：

```text
- CI fail
- forbidden path 被修改
- Reviewer 发现 P1
- Functional Test 失败
- Multica issue done 但 PR 未通过
```

### 第 1–2 天：模板最小改造

交付：

```text
docs/agent/task-contract.md
docs/agent/evidence-and-gates.md
docs/agent/execution-backends.md
docs/agent/security-boundaries.md
docs/milestones/M1.md
```

验收：

```text
每个 task 有 task_id、canonical_owner、allowed_paths、forbidden_paths、acceptance、required_evidence。
Direct/Subagent 判断规则能落到每个 task。
```

### 第 3–4 天：Bridge local baseline

Bridge 只做本地，不接 Multica。

命令建议：

```bash
agent-bridge validate docs/milestones/M1.md
agent-bridge export --backend github --dry-run
agent-bridge gate --task M1-T03
agent-bridge closeout --milestone M1
```

验收：

```text
重复运行不产生重复任务。
能发现 schema 缺失。
能根据 git diff 检查 forbidden paths。
能生成 gate report。
```

### 第 5–6 天：Codex + DeepSeek 角色闭环

执行 2–3 个 task：

```text
Builder：Codex
Test Builder：Codex
Reviewer-A：Codex review
Reviewer-B：DeepSeek V4 Pro
Verifier：Codex 运行固定命令
```

验收：

```text
Builder 输出 PR 或 patch。
Verifier 输出结构化 command evidence。
DeepSeek reviewer 输出具体 finding，而不是泛泛建议。
Codex reviewer 与 DeepSeek reviewer 的结论可合并成 gate。
```

### 第 7 天：Functional Test 分级验证

选一个可黑盒任务，做 FT-L0 或 FT-L1。再选一个无法黑盒任务，验证 FT-L2 / FT-L3 降级。

验收：

```text
黑盒任务不提供源码和 diff 仍能验收。
无法黑盒任务能被明确标记为 graybox 或 not_applicable。
Functional Test 失败时 gate 不放行。
```

### 第 8–10 天：Multica Cloud POC

用同一批 task 导出 Multica issue，不接敏感数据。

验证：

```text
milestone doc → Multica issue upsert
task_id 反向引用
agent comment/blocker 回收
Multica done 与 Bridge accepted 分离
```

验收：

```text
Multica done 但 CI failed → Bridge 判 not_accepted。
Multica blocker comment → Bridge unresolved issue gate。
重复导出 → 不重复创建 issue。
```

### 第 11–12 天：Multica self-host 小试

只验证部署和安全边界，不必生产化。

检查：

```text
Docker/selfhost 启动
生产环境变量 checklist
注册白名单
SMTP 或临时邮箱策略
daemon token 而非 PAT
custom_env 不放高价值 secret
```

验收：

```text
能在本机或内网 VM 跑起来。
能连接 daemon。
能创建一个 agent 并执行无敏任务。
能说明 production gap 清单。
```

### 第 13–14 天：决策报告

输出一份 POC report：

```md
# Agent Workflow POC Closeout

## What worked
## What failed
## Evidence summary
## Gate results
## Multica Cloud vs Self-host assessment
## GitHub issue vs milestone doc assessment
## Recommended next phase
## Unresolved risks
```

最终验收标准：

```text
1. 新 session 只看 repo docs + GitHub/Multica refs 能恢复状态。
2. 至少 4 种失败场景被 gate 拦住。
3. AI Reviewer 结论都能落到文件/行/风险等级。
4. Verifier evidence 包含 commit SHA、命令、退出码、环境。
5. Multica issue 状态不再被误认为最终验收状态。
6. Bridge dry-run / rerun 幂等。
7. 明确 cloud 是否可用于公司项目，或必须 self-host。
```

---

## 9. 现在马上改模板的最小内容

不要大改。只加四类最小文件和少量字段。

### A. 根 `AGENTS.md` 只加索引

保持短：

```md
## Execution governance

For execution modes, task contracts, evidence gates, backend ownership, and handoff rules, see:

- docs/agent/task-contract.md
- docs/agent/evidence-and-gates.md
- docs/agent/execution-backends.md
- docs/agent/security-boundaries.md
```

### B. 新增 `docs/agent/task-contract.md`

定义 task 最小 schema：

```yaml
task_id: M1-T03
title: ...
canonical_owner: repo-doc
revision: 1
mode: direct | subagent | borderline
risk: low | medium | high
roles:
  builder: required
  test_builder: optional
  verifier: required
  reviewer: required
  functional_test: conditional
allowed_paths:
  - src/...
forbidden_paths:
  - infra/prod/**
acceptance:
  - ...
required_context:
  - AGENTS.md
  - docs/agent/evidence-and-gates.md
backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
stop_conditions:
  - requires production credentials
  - requires forbidden path changes
  - acceptance unclear
```

### C. 新增 `docs/agent/evidence-and-gates.md`

写死 gate：

```text
accepted requires:
- task_id present
- PR or patch linked
- forbidden path check passed
- verifier evidence passed
- reviewer conclusion passed
- functional test passed or explicitly not_applicable
- unresolved blockers = 0
- closeout/handoff updated
```

最小 evidence 格式：

```yaml
verifier:
  commit:
  commands:
    - command:
      exit_code:
      stdout_excerpt:
      stderr_excerpt:
  conclusion: pass | fail | inconclusive

reviewer:
  base_sha:
  head_sha:
  findings:
    - severity:
      file:
      line:
      issue:
  conclusion: pass | fail | pass_with_risk | inconclusive

functional_test:
  level: FT-L0 | FT-L1 | FT-L2 | FT-L3 | FT-L4
  scenario:
  result:
  conclusion:
```

### D. 新增 `docs/agent/execution-backends.md`

只定义状态归属，不写长篇 Multica 教程：

```md
# Execution backends

## Canonical ownership

- Task spec: repo doc initially.
- Execution state: selected backend.
- Code result: PR / commit / CI.
- Final handoff: repo docs.

## Supported backend profiles

### codex-local
Use for Direct Mode and small Subagent Mode.

### github-issues
Use GitHub issue as execution ticket.
Do not make GitHub issue canonical unless `canonical_owner: github-issue`.

### multica
Use Multica issue/task as agent execution state.
Do not treat Multica Done as acceptance.
Bridge gate remains authoritative for acceptance.
```

### E. 新增 `docs/agent/security-boundaries.md`

包含 VPN 和 secret 最小规则：

```md
# Security boundaries for agents

- Agents must not use production credentials.
- Agents must not access production systems.
- Agents must not inherit personal SSH/cloud/kube credentials.
- Reviewer and Verifier should run read-only where possible.
- Functional Test should use staging/sandbox.
- High-value secrets must not be placed in Multica custom_env.
- VPN access must be scoped to development/test resources.
```

### F. 修改 `docs/milestones/_template.md`

加入：

```md
## Task list

### M1-T01: ...

~~~yaml
task_id: M1-T01
canonical_owner: repo-doc
revision: 1
mode: direct
risk: low
allowed_paths: []
forbidden_paths: []
acceptance: []
required_evidence:
  verifier: true
  reviewer: true
  functional_test: false
backend_refs:
  github_issue:
  multica_issue:
  pr:
~~~
```

### G. 不要现在就加的内容

现在不要加：

```text
new-milestone-with-multica 模式
worker registry
worker metrics 自动路由
tasks.jsonl 作为必须维护的主状态
issues.jsonl 作为全局状态数据库
自动双向同步
自动 merge
自动 loop until done
完整 Cockpit
````

---

## 10. 最后建议的落地决策

你们现在最稳的路线是：

```text
模板：
采用方案 B：new-milestone + 可选 execution-backends.md。
不新增 new-milestone-with-multica 作为正式模式。

任务源：
短期 milestone doc canonical。
中期 GitHub issue 作为 execution ticket。
后期 GitHub/GitLab issue 可按 task 迁移为 canonical，但每个 task 只能有一个 canonical owner。

Multica：
先 Cloud POC，非敏感。
公司项目和 VPN/内网场景转 self-host。
Multica 只做 execution backend，不做 acceptance source of truth。

AI 角色：
Codex Builder/Test/Verifier。
Codex review + DeepSeek V4 Pro adversarial review。
Functional Test 黑盒优先，不能黑盒则按 FT-L1~FT-L4 降级。

Bridge：
现在只做 validate / export / gate / closeout。
不要做平台化调度。
```

最关键的一条规则：

```text
“Done” 不是验收状态。
只有 Bridge gate 基于 PR/CI/evidence/review/functional test/closeout 计算出来的 accepted，才是验收状态。
```

[1]: https://www.multica.ai/docs/how-multica-works "How Multica works | Multica Docs"
[2]: https://www.multica.ai/docs/cloud-quickstart "Cloud quickstart | Multica Docs"
[3]: https://www.multica.ai/docs/self-host-quickstart "Self-host quickstart | Multica Docs"
[4]: https://multica.ai/docs/environment-variables "Environment variables | Multica Docs"
[5]: https://www.multica.ai/docs/auth-setup "Sign-in and signup configuration | Multica Docs"
[6]: https://multica.ai/docs/zh/environment-variables?utm_source=chatgpt.com "环境变量| Multica Docs"
[7]: https://www.multica.ai/docs/auth-tokens "Authentication and tokens | Multica Docs"
[8]: https://www.multica.ai/docs/agents-create "Create and configure an agent | Multica Docs"
[9]: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches "About protected branches - GitHub Docs"
[10]: https://docs.github.com/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners "About code owners - GitHub Docs"
[11]: https://docs.gitlab.com/user/project/repository/branches/protected/ "Protected branches | GitLab Docs"
[12]: https://developers.openai.com/codex/subagents "Subagents – Codex | OpenAI Developers"
[13]: https://developers.openai.com/codex/integrations/github "Code review in GitHub – Codex | OpenAI Developers"
[14]: https://api-docs.deepseek.com/news/news260424 "DeepSeek V4 Preview Release | DeepSeek API Docs"
[15]: https://docs.github.com/articles/about-issues "About issues - GitHub Docs"

## Reference Implementations To Study Later

### spellbook / skills / threads

Reference:
- https://github.com/majiayu000/spellbook/tree/main/skills/threads

Use later for:
- Codex-native parallel thread workflow design
- lane map format
- worktree/file ownership model
- planner / worker / reviewer / merge reviewer / closure auditor role split
- independent review gate
- remote truth vs local state reporting
- failure rules for vague worker output, unassigned file touches, repeated failed attempts

Do not copy blindly.
Adapt into our governance contract and Bridge gate model.

### mattpocock / skills

Reference:
- https://github.com/mattpocock/skills

Use later for:
- small composable skill design
- setup skill pattern
- issue tracker abstraction: GitHub / Linear / local files
- shared language / CONTEXT.md pattern
- ADR integration
- TDD / diagnose / triage / handoff workflow ideas
- skill quality structure: hard rules, examples, verification checklists

Do not copy blindly.
Adopt patterns only after license and architecture review.
