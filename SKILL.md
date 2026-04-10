---
name: iwencai-skills
description: Use this skill when someone needs to use the local iWencai CLI in this repository, choose between query2data/search/trade, write effective iWencai queries, configure authentication, or run packaged/release-preflight checks.
---

# iWencai Official CLI

This repository exposes one local CLI command: `iwencai`.

The CLI is family-first, not skill-first. Users do not need to know historical skill ids, aliases, or upstream zip packages. They only need to pick the correct runtime family:

- `query2data`: finance retrieval, screening, ranking, selector-style queries
- `search`: announcements, news, reports, investor-relation activity
- `trade`: explicit simtrade subcommands such as bootstrap, buy, sell, positions

If the user omits the family and runs `iwencai -q "..."`, the CLI defaults to `query2data`.

## What This Skill Must Teach

After reading this file, a person or stateless LLM should understand:

- what `iwencai` is and what it is not
- which family to choose for a request
- how to authenticate
- how to write effective `query2data` and `search` queries
- why `trade` is not natural-language query input
- what output formats exist
- what local state files are used
- how to diagnose common failures
- where the deeper source of truth lives in this repository

## Mental Model

Use this decision rule first:

1. If the user wants rows, facts, attributes, rankings, screeners, or selector-style results, use `query2data`.
2. If the user wants content documents such as announcements, news, reports, or investor-relation activity, use `search`.
3. If the user wants account actions or account views such as bootstrap, buy, sell, positions, fund, profit, or history-trades, use `trade`.

Do not mix families in one command.

Bad:

- "查一下贵州茅台公告并筛出低市盈率白酒股"
- "看看我持仓并买入100股腾讯控股"

Good:

- `iwencai search -q "贵州茅台 公告"`
- `iwencai -q "低市盈率白酒股"`
- `iwencai trade positions`
- `iwencai trade buy --stock-code 600519 --quantity 100 --price 1500`

## Install And Entrypoints

Install locally:

```bash
pip install .
iwencai --help
```

Development entrypoint:

```bash
python iwencai_cli.py --help
```

Canonical public entrypoint is `iwencai`. Use that in examples unless there is a specific reason to mention `python iwencai_cli.py`.

## Authentication And Environment

`query2data` and `search` require an API key.

Resolution order:

1. explicit `--api-key`
2. environment variable `IWENCAI_API_KEY`
3. local `.env` file in the current working directory
4. local `.env` file in the repository root

Example `.env`:

```dotenv
IWENCAI_API_KEY=your_api_key_here
```

Runtime behavior:

- the CLI does not overwrite an existing environment variable with values from `.env`
- the CLI automatically appends official hosts to `NO_PROXY/no_proxy`
- official hosts currently include `openapi.iwencai.com` and `trade.10jqka.com.cn`

## Output Model

Every family supports output shaping:

- `--format json`: default, best for machine consumption
- `--format jsonl`: one record per line when the payload is list-like
- `--format table`: terminal-friendly rendering
- `--output PATH`: write rendered output to a file instead of stdout

Use `json` when another tool or LLM will parse the output.
Use `table` when a human needs to scan results quickly.

## Query Authoring: The Core Concept

For `query2data` and `search`, iWencai behaves like weak finance DSL, not open-ended chat.

Implications:

- short finance-bearing phrases outperform chatty natural language
- explicit entity, metric, event, comparator, ranking word, content type, and time window matter
- one command should usually express one intent
- conversational pronouns such as "这只", "它", "那个" degrade reliability

### query2data

Use `query2data` for:

- fields and attributes
- event lookup
- market/domain metrics
- screening and ranking
- selector-style "哪些" / "前十" / "低于10%" requests

Canonical shapes:

- `主体 + 指标/事件`
- `时间窗 + 主体 + 指标/事件`
- `范围 + 条件/排序 + 时间窗`

Good examples:

- `iwencai -q "同花顺主营业务构成"`
- `iwencai -q "2024年中国GDP"`
- `iwencai -q "宁德时代业绩预告"`
- `iwencai -q "今日涨跌幅超过5%的A股有哪些？"`
- `iwencai -q "近一年收益排名前十的基金经理"`

Useful flags:

- `--page`: starting page, default `1`
- `--limit`: per-page size, default `10`
- `--all-pages`: keep fetching until the current result set is exhausted
- `--is-cache`: upstream cache flag, default `1`

Examples:

```bash
iwencai -q "2连板股票"
iwencai query2data -q "近5日主力资金净流入前10" --limit 10
iwencai query2data -q "市盈率最低的A股" --all-pages --format jsonl
```

Avoid:

- `帮我选好基金`
- `找便宜的美股`
- `查一下公告并顺便筛股`

### search

Use `search` for content retrieval across official channels:

- `announcement`
- `investor`
- `news`
- `report`

Canonical shapes:

- `实体/主题 + 内容类型 + 时间词`
- `主题 + 内容类型`

Good examples:

- `iwencai search -q "贵州茅台 公告"`
- `iwencai search -q "最近一个月的分红公告" --channel announcement`
- `iwencai search -q "人工智能最新动态" --channel news`
- `iwencai search -q "芯片行业研究报告" --channel report`
- `iwencai search -q "贵州茅台投资者关系活动" --channel investor`

Channel behavior:

- if `--channel` is omitted, the CLI searches all official channels
- `--channel` can be repeated
- comma-separated channel values are also accepted

Examples:

```bash
iwencai search -q "最近的分红公告"
iwencai search -q "近期业绩说明会" --channel investor
iwencai search -q "机器人行业深度报告" --channel report --limit 20
```

Avoid:

- `贵州茅台`
- `人工智能`
- `最近贵州茅台和五粮液有什么公告？`

When the request mentions multiple companies or topics, split it into multiple commands.

### trade

`trade` is not a natural-language query surface.

Use explicit subcommands and flags instead.

Subcommands:

- `bootstrap-account`
- `show-account`
- `buy`
- `sell`
- `positions`
- `profit`
- `fund`
- `today-trades`
- `history-trades`
- `gain-30d`

Core constraints:

- `buy` and `sell` only support 6-digit A-share stock codes
- quantity must be a multiple of 100
- `history-trades` accepts `YYYYMMDD` or `YYYY-MM-DD`
- local account state is stored at `.iwencai/default_account.json`

Typical flow:

```bash
iwencai trade bootstrap-account
iwencai trade positions --format table
iwencai trade buy --stock-code 600519 --quantity 100 --price 1500
iwencai trade sell --stock-code 600519 --quantity 100 --price 1510
iwencai trade history-trades --start-date 20240101 --end-date 20240131
```

Avoid treating these natural-language phrases as valid `trade` commands:

- `买入600519 100股 价格1500元`
- `看看我持仓有哪些`
- `顺便帮我看看持仓再买点白酒`

Translate them into explicit subcommands instead.

## Common Failure Modes

### Missing API key

Typical error:

```json
{"success": false, "error": "API密钥未设置，请通过参数 --api-key 或环境变量 IWENCAI_API_KEY 指定"}
```

Fix:

- pass `--api-key`
- or export `IWENCAI_API_KEY`
- or create a local `.env`

### Empty or poor results

Usually caused by weak query shape:

- too chatty
- missing entity or metric
- search query missing content type
- vague adjectives such as "好", "强", "便宜", "大"
- mixing multiple families into one request

Fix by rewriting into shorter, more explicit finance phrases.

If the CLI still returns no data after a reasonable rewrite, explicitly tell the user they can also verify in the 同花顺问财 web 端:

- <https://www.iwencai.com/unifiedwap/chat>

### Invalid search channel

Only these are valid:

- `announcement`
- `investor`
- `news`
- `report`

### Trade network errors

If `trade` returns connection errors such as connection refused, that usually means the simtrade backend is unreachable from the current environment, not that the CLI accepted a bad natural-language trade command.

## Rules For Agents And Stateless LLMs

When operating this CLI for a user:

- prefer `iwencai` over `python iwencai_cli.py` in user-facing examples
- if the user gives only `-q/--query`, route it mentally to `query2data`
- do not invent historical skill ids or aliases
- do not tell users to use `--skill`; this CLI is family-first
- convert colloquial finance requests into weak-DSL query form before running them
- split multi-intent requests into separate commands
- treat `trade` as explicit command verbs plus flags, not as query text
- use `--format json` when another agent will consume the output
- use `--format table` when the user wants terminal readability
- when citing queried market data, explicitly state that the data source is 同花顺问财
- if no data is returned, tell the user they can also query via 同花顺问财 web 端: <https://www.iwencai.com/unifiedwap/chat>

## Fast Start Checklist

For a new human or LLM operator, this is the minimal path:

1. `pip install .`
2. set `IWENCAI_API_KEY` or create `.env`
3. run `iwencai --help`
4. test `iwencai -q "2连板股票"`
5. test `iwencai search -q "最近的分红公告" --channel announcement`
6. if using simtrade, run `iwencai trade bootstrap-account`

## Verification And Release Checks

Repository quality gates:

- `python -m pytest -q`
- `python -m ruff check .`
- `python -m ruff format --check .`
- `python -m pyright`
- `pre-commit run --all-files`

Release-preflight smoke:

- `python tests/release_preflight.py`

That preflight creates a clean temporary virtual environment, installs the project, invokes the packaged `iwencai` command, and runs CLI smoke tests.

## Source Of Truth Inside This Repo

Use these files when deeper detail is needed:

- `specs/CLI_UX.SPEC.yaml`: public command surface and help contract
- `specs/QUERY_AUTHORING.SPEC.yaml`: weak-DSL query model
- `specs/QUERY_AUTHORING.RULE.yaml`: query rewrite and anti-pattern guidance
- `specs/HTTP_FAMILIES.SPEC.yaml`: family-level HTTP behavior

If `SKILL.md` and another doc diverge, align them by checking the runtime help and the specs above rather than guessing.
