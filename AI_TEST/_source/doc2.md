# 项目核心 Skills 介绍
本项目实现 **需求文档 → 测试用例 → 基于用例探索实际系统 → 固化自动化脚本 → 独立回放** 的闭环流水线。  
流水线由一组相互衔接的 skill 驱动，模型逐条完成理解、设计、评审与探索，脚本负责格式转换、准入检查与执行结果记录。

整个流程分为七段，三个核心 skill 承担主链路，若干辅助 skill 提供文档解析、浏览器操作、表格渲染等能力支撑。

## 一、Skill 总览
| 类别 | Skill | 作用阶段 | 一句话职责 |
| --- | --- | --- | --- |
| 核心 | [req-processor](../.agents/skills/req-processor/SKILL.md) | ①解析 ②拆分 ③理解 | 原始文档 → 结构化需求规范 + REQ 清单 |
| 核心 | [testcase-builder](../.agents/skills/testcase-builder/SKILL.md) | ④设计 ⑤评审 | 需求规范 → 逐条用例 + 评审凭据 |
| 核心 | [web-automation](../.agents/skills/web-automation/SKILL.md) | ⑥读取 ⑦探索与固化 | 已评审用例 → 真实探索 → pytest 脚本 → 独立回放 |
| 辅助 | [mineru](../.agents/skills/mineru/SKILL.md) | ①解析支撑 | PDF / Word / 图片 / Excel → Markdown |
| 辅助 | [playwright-cli](../.agents/skills/playwright-cli/SKILL.md) | ⑦探索支撑 | 命令式浏览器自动化（open / click / fill / snapshot） |
| 辅助 | [xlsx](../.agents/skills/xlsx/SKILL.md) | ④⑤渲染支撑 | Excel 读写与格式规范 |
| 共享 | [shared](../.agents/skills/shared/) | 全流程 | 编号规则、格式契约、环境门禁、脚本门禁 |


> Skills 维护源为 `.agents/skills/`；`.claude/skills/` 为兼容镜像，修改后用 `shared/scripts/sync_skills.py` 同步。
>
> ## Skill 之间的衔接关系
> ![](https://cdn.nlark.com/yuque/0/2026/png/32819200/1790128912169-86058832-595b-49b7-8355-2d1be8ed316e.png)
>



## 二、核心 Skills 详解
### 1. req-processor — 需求处理（解析 + 拆分 + 理解）
**定位**：流水线第一段。把原始需求文档（Word/PDF/图片/Excel）转为结构化、带 REQ 编号的需求规范，供下游设计用例。

**内部三阶段，必须按序执行**：

```plain
原始文档(input/)
   ① 解析   -> output/_来源/{文档版本}/解析.md + images/（完整稿，不覆盖）
   ② 拆分   -> output/{模块}/解析.md + output/_公共/拆分报告.md
   ③ 理解   -> output/{模块}/需求规范.md + REQ清单.json
```

| 阶段 | 触发语 | 产物 | 强制门禁脚本 |
| --- | --- | --- | --- |
| ① 解析 | "解析需求文档""导入需求" | `output/_来源/{文档版本}/解析.md` + `images/` | `check_parse.py` |
| ② 拆分 | "拆分需求""按功能拆分" | `output/{模块}/解析.md` + `output/_公共/拆分报告.md` | `check_split.py` |
| ③ 理解 | "理解需求""需求分析" | `output/{模块}/需求规范.md` + `REQ清单.json` | `validate_spec.py` |


**核心铁律**：

+ 解析是**转录不是理解**——禁止增删改写任何需求内容；错别字、可疑表述原样保留。
+ 拆分必须先做 5 维度需求理解，**禁止机械按章节拆分**。
+ 理解阶段只基于文件，**禁止猜测填补未明确内容**；附图逐张理解，禁止跳图（脚本会对账）。
+ **P0 疑问未确认不得进入用例设计**（阻塞下游）；P1/P2 记录后继续。
+ REQ 编号 `REQ_{功能缩写}_{三位序号}`，只增不改不复用。

**关键契约**：[parse-rules.md](../.agents/skills/req-processor/references/parse-rules.md)、[split-rules.md](../.agents/skills/req-processor/references/split-rules.md)、[spec-template.md](../.agents/skills/req-processor/references/spec-template.md)。

### 2. testcase-builder — 用例设计与逐条评审
**定位**：流水线第二段。基于需求规范逐条设计测试用例并逐条评审，输出 11 列 Excel 与结构化评审凭据，供 AI 探索实际系统。

**前置**：`output/{模块}/需求规范.md`、`REQ清单.json`、`output/_公共/拆分报告.md`。第 8 节 P0 未确认时不得设计。

**④ 设计**：

+ 逐条设计业务目标、前置条件、业务动作、数据、预期、关联 REQ、可自动化初判。
+ **locator、页面路径、具体控件在下游探索确定，不能提前猜测。**
+ 覆盖基本流 / 备选流 / 异常流；不适用的流程明确说明，不为凑比例编造规则。
+ 写 `用例数据.json`（测试数据为 JSON 对象；步骤和预期为字符串数组）。
+ 门禁：`render_xlsx.py`（渲染 + 校验 P0/数据）+ `check_coverage.py`（拒绝未关联 / 未知 REQ / 重复编号）。
+ **REQ 关联 100% 不等于预期已充分覆盖。**

**⑤ 评审**：

+ 按评审规则**逐条**核对预期来源、步骤可执行性、数据与前置条件、关联 REQ、场景覆盖。
+ 写 `评审数据.json`：每条结论、原因、建议、可自动化判定、执行方式，及三流 / 方法论评分依据。
+ **未知 locator 不是业务用例不通过的理由。**
+ 业务正文不在评审脚本中修改；发现问题回到设计 JSON 修订、重渲染后重新评审。
+ 门禁：`update_review.py` 检查逐条完整性、JSON/Excel 正文一致、需求关联；计算评分并生成 `.review.json` 指纹凭据。
+ **评分 ≥ 75 只是模块准入**；具体条目仍需通过且可自动化=是、执行方式=UI；需确认 / 不合理不能被平均分抵消。

**关键契约**：[design-rules.md](../.agents/skills/testcase-builder/references/design-rules.md)、[case-template.md](../.agents/skills/testcase-builder/references/case-template.md)、[review-rules.md](../.agents/skills/testcase-builder/references/review-rules.md)、[case-format-contract.md](../.agents/skills/shared/references/case-format-contract.md)。

### 3. web-automation — 用例驱动的探索执行与自动化固化
**定位**：流水线第三段。基于已评审测试用例探索真实 Web 系统，执行并记录证据，将实际操作固化为 pytest + playwright 脚本，再独立回放。

**核心理念**：需求确定测试目标和预期；AI 在真实系统中发现实现目标的操作路径。用例中的业务动作可拆成多个 UI 操作，但不能改变业务含义、输入约束或断言预期。

**测试环境门禁（执行前必须满足）**：

+ 用户必须明确提供测试 URL，或明确指定本次使用的配置文件。
+ 旧文件存在、原始需求附带链接、默认地址、以前运行过**均不能代替用户指定**。
+ 没有明确环境时，向用户索取并等待；等待期间可处理文档、用例、评审和离线校验，禁止打开测试站点、发业务请求或执行业务 pytest。
+ 收到环境后配置 `tests/.env` 与 `tests/environment.json`（来源只记录用户消息 / 指定文件说明，不含凭据）。
+ 网页探索、切换环境和每次独立执行前运行 `environment_gate.py`，非零退出立即阻止。

**⑥ 读取（准入）**：

+ `read_cases.py --for-exploration` 检查评审凭据、需求 / 用例版本、P0 阻塞、评分 ≥ 75。
+ 只输出逐条通过、可自动化=是、执行方式=UI 的用例；其他用例附跳过原因。
+ **缺少评审时返回 testcase-builder 完成评审；不凭文件名判断已评审。**

**⑦ 逐条探索**：

1. 理解目标：读 REQ、前置条件、全部步骤和预期，确定观察点。入口 / locator 未知由探索解决，不当作需求疑问。
2. 准备环境和数据：建立登录 / 角色 / 业务状态，记录数据准备和清理；使用测试数据，避免依赖其他用例执行顺序。
3. 探索实际页面：snapshot 寻找入口和控件，逐步执行；收集每次真实 `Ran Playwright code:`、关键快照 / 截图。
4. 逐项判断：预期来自需求和已评审用例，实际来自页面 / 必要的网络响应证据。**不能把观察到的错误表现写成新的正确预期。**
5. 分类结果：`passed` / `product_bug` / `blocked` / `needs_clarification` / `unsupported`。
6. 保存证据：逐条写 `output/{模块}/探索/{TC编号}/记录.json`，保留输入指纹、步骤映射、预期 / 实际、证据路径、前置准备和清理说明。

**固化与独立回放**：

+ 只有实际探索完成且步骤 / 预期有证据的 `passed` 或 `product_bug` 条目才能固化；阻塞条目保留原因，草稿放模块的 `待固化/`，不进入 `tests/`。
+ 逐条写 `tests/test_*.py` + `tests/data/*.yaml`；locator 来自真实证据，前置条件实现为操作 / fixture。
+ **禁止只写注释、TODO、pass 或固定成功断言。**
+ `finalize_exploration.py --run` 记录真实退出码、JUnit 和指纹；正常通过标 `verified`，产品缺陷复现标 `defect_reproduced`（仍返回非零）。
+ 成功回放或缺陷复现后由脚本回填已评审 Excel 的脚本 / 实际结果列，并更新工作簿指纹。**不要临时手写 Excel 回填代码。**

**自愈约束**：自愈只修定位、等待和执行方式，不删步骤 / 断言，不改预期、编号、函数名或文件名；先分类根因，不能将产品缺陷改绿。

**关键契约**：[exploration-contract.md](../.agents/skills/web-automation/references/exploration-contract.md)、[generate-rules.md](../.agents/skills/web-automation/references/generate-rules.md)、[asserts.md](../.agents/skills/web-automation/references/asserts.md)、[pytest-conventions.md](../.agents/skills/web-automation/references/pytest-conventions.md)、[heal-rules.md](../.agents/skills/web-automation/references/heal-rules.md)、[env-config.md](../.agents/skills/web-automation/references/env-config.md)。

## 三、辅助 Skills
### mineru — 文档提取
为阶段①解析提供文档转 Markdown 能力。支持 PDF、Word、PPT、Excel、图片、网页等 80+ 语言。  
两种模式：`flash-extract`（免配置、≤20 页 / ≤10MB，首选）与 `extract`（需 token，VLM 布局分析，高精度）。  
解决扫描件 OCR、表格识别、公式识别、批量处理等场景。

### playwright-cli — 命令式浏览器自动化
为阶段⑦探索提供浏览器操作能力。命令式 API：`open / goto / click / fill / type / press / snapshot / screenshot / close`。  
通过 snapshot 返回的 ref 与页面交互，收集 `Ran Playwright code:` 作为探索证据。

### xlsx — Excel 读写与格式规范
为阶段④⑤的 Excel 渲染与回填提供格式规范。要求专业字体、零公式错误、保留既有模板约定。  
项目实际渲染走 `testcase-builder/scripts/render_xlsx.py` 与 `update_review.py`，禁止临时手写 openpyxl。

### shared — 跨 skill 共享契约与脚本
+ [references/numbering-rules.md](../.agents/skills/shared/references/numbering-rules.md)：编号体系（REQ / TC 只增不改不复用）。
+ [references/case-format-contract.md](../.agents/skills/shared/references/case-format-contract.md)：用例格式契约。
+ [scripts/environment_gate.py](../.agents/skills/shared/scripts/environment_gate.py)：环境门禁。
+ [scripts/script_guard.py](../.agents/skills/shared/scripts/script_guard.py)：脚本静态门禁。
+ [scripts/sync_skills.py](../.agents/skills/shared/scripts/sync_skills.py)：`.agents/skills/` → `.claude/skills/` 同步。
+ `tests/`：框架回归测试（`uv run pytest .agents/skills/shared/tests -q`）。

## 
