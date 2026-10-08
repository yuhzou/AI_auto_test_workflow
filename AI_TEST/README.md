# auto_test — 需求到独立回放的 Web 自动化测试流水线（Skills 实现）

本目录依据三篇语雀在线文档设计：

| 文档 | 归档 |
| --- | --- |
| 1、基于 codex 从需求文档到独立回放的 web 自动测试 | [docs/01-流程总览.md](docs/01-流程总览.md) |
| 2、核心的 skills | [docs/02-核心Skills.md](docs/02-核心Skills.md) |
| 3、AGENTS.md | [docs/03-AGENTS原始稿.md](docs/03-AGENTS原始稿.md) |

抓取与解析过程记录见 [docs/99-来源与解析记录.md](docs/99-来源与解析记录.md)。

## 设计出的 Skills

核心 skill（按文档实现，位于 `.agents/skills/`）：

| Skill | 作用阶段 | 一句话职责 | 入口 |
| --- | --- | --- | --- |
| `req-processor` | ①解析 ②拆分 ③理解 | 原始文档 → 结构化需求规范 + REQ 清单 | [SKILL.md](.agents/skills/req-processor/SKILL.md) |
| `testcase-builder` | ④设计 ⑤评审 | 需求规范 → 逐条用例 + 评审凭据 | [SKILL.md](.agents/skills/testcase-builder/SKILL.md) |
| `web-automation` | ⑥读取 ⑦探索与固化 | 已评审用例 → 真实探索 → pytest 脚本 → 独立回放 | [SKILL.md](.agents/skills/web-automation/SKILL.md) |
| `shared` | 全流程 | 编号规则、格式契约、环境门禁、脚本门禁、镜像同步 | [SKILL.md](.agents/skills/shared/SKILL.md) |

辅助 skill（`mineru` / `playwright-cli` / `xlsx`）文档中提及但已由用户自行安装，
本项目不重复设计；核心 skill 的 SKILL.md 中按名称引用。

## 结构

```plain
auto_test/
  AGENTS.md                  # 项目级指令（依据文档 3 设计）
  pyproject.toml             # Python 依赖（pytest / playwright / pyyaml / openpyxl）
  docs/                      # 三篇文档原文归档 + 抓取记录
  input/                     # 原始需求文档（只读）
  output/                    # 各阶段产物（按模块组织）
  tests/                     # 正式 pytest 脚本与业务数据
  _source/                   # 语雀抓取原始文件（HTML / API JSON / Markdown）
  .agents/skills/
    req-processor/           # SKILL.md + references + scripts
    testcase-builder/        # SKILL.md + references + scripts
    web-automation/          # SKILL.md + references + examples + scripts
    shared/                  # SKILL.md + references + scripts + tests
```

## 快速开始

```bash
uv sync
uv run playwright install chromium

# 1. 需求：解析 → 拆分 → 理解
uv run python .agents/skills/req-processor/scripts/check_parse.py --md "output/_来源/v1/解析.md"
uv run python .agents/skills/req-processor/scripts/check_split.py --source "output/_来源/v1/解析.md" --input-dir output
uv run python .agents/skills/req-processor/scripts/validate_spec.py --module "示例模块"

# 2. 用例：设计 → 渲染 → 覆盖率 → 评审
uv run python .agents/skills/testcase-builder/scripts/render_xlsx.py --module "示例模块" --json "output/示例模块/用例数据.json"
uv run python .agents/skills/testcase-builder/scripts/check_coverage.py --module "示例模块"
uv run python .agents/skills/testcase-builder/scripts/update_review.py "output/示例模块/详细用例.xlsx" "output/示例模块/详细用例_已评审.xlsx" "output/示例模块/评审数据.json"

# 3. 探索与回放（需要用户先提供测试环境）
uv run python .agents/skills/shared/scripts/environment_gate.py
uv run python .agents/skills/web-automation/examples/read_cases.py "output/示例模块/详细用例_已评审.xlsx" --for-exploration
uv run python .agents/skills/web-automation/scripts/finalize_exploration.py "output/示例模块/探索/TC_XXX_001/记录.json" --run
```

同步镜像与框架回归：

```bash
uv run python .agents/skills/shared/scripts/sync_skills.py          # .agents/skills -> .claude/skills
uv run pytest .agents/skills/shared/tests -q                        # 门禁脚本回归测试
```

## 核心原则（来自文档）

- 每一个箭头都有**强制门禁**，每一个产物都有**唯一事实源**；
- 人不写定位器、不抄页面、不靠口述结论——定位器来自真实系统探索证据；
- 用例逐条评审、逐条评分；评分 ≥ 75 只是模块准入，单条“需确认 / 不合理”不能被平均分抵消；
- 独立回放记录真实退出码、JUnit 与指纹；产品缺陷复现就是缺陷复现（不用 xfail/skip 掩盖）；
- 没有用户明确提供的测试地址，**不打开测试站点、不发业务请求**。
