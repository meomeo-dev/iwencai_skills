# iWencai Official CLI

单文件、family-first 的同花顺问财 CLI。

本项目基于 <https://www.iwencai.com/skillhub> 的官方技能整合而成，收敛为一个统一的 CLI 工具。
`IWENCAI_API_KEY` 可在登录后从对应技能页面复制获得。
原始 skill 为 MIT License，本项目继承并延续 MIT License。

## 安装

```bash
pip install .
iwencai --help
```

安装后会生成 `iwencai` 命令。

开发态仍可直接运行：

```bash
python iwencai_cli.py --help
```

## 配置 API Key

`query2data` 和 `search` 需要 `IWENCAI_API_KEY`。可以直接传 `--api-key`，也可以用 `.env`。
如果两者都没配好，在交互式终端里首次发起 `query2data/search` 时，CLI 会自动拉起一个本地 HTML 配置页，方便直接粘贴密钥，并可勾选保存到当前目录 `.env`。

推荐做法：

```bash
cp .env.example .env
```

然后把 `.env` 里的占位值替换成你的真实 key：

```dotenv
IWENCAI_API_KEY=your_api_key_here
```

也可以临时用环境变量：

```bash
export IWENCAI_API_KEY=your_api_key_here
```

或者单次调用显式传入：

```bash
iwencai -q "2连板股票" --api-key your_api_key_here
```

自动配置页流程：

1. 直接运行任一需要密钥的 `query2data/search` 命令。
2. CLI 会自动打开本地网页。
3. 粘贴密钥，可选择是否持久化到当前目录 `.env`。
4. 提交后，当前命令会继续执行。

`trade` 子命令不依赖 `IWENCAI_API_KEY`，但依赖本地模拟账户状态和上游交易服务可达。

## 快速开始

```bash
iwencai -q "2连板股票"
iwencai search -q "最近的分红公告" --channel announcement
iwencai trade positions --format table
```

## Query 写法

`iwencai` 的 query 不是严格自由自然语言，更像带金融词法和弱约束的弱 DSL。

核心原则：

- 一条 query 只做一件事，尽量只对应一个 family 和一个主意图。
- 少写聊天铺垫，多写金融实体、指标、事件、时间窗、排序词、比较词。
- 口语要改成标准金融说法。
- 多主体、多维度问题要拆成多条 query。
- 单次 CLI 调用不要依赖“这只”“它”“那个”这类上下文代词。

## query2data 写法

更适合“查字段/查事件/做筛选/做排行”。

推荐结构：

- 主体 + 指标/事件
- 范围 + 条件/排序 + 时间窗

好的例子：

- `同花顺主营业务构成`
- `2024年中国GDP`
- `宁德时代业绩预告`
- `今日涨跌幅超过5%的A股有哪些？`
- `转股溢价率低于10%的可转债有哪些？`
- `近一年收益排名前十的基金经理`

不好的例子：

- `帮我选好基金`
- `找便宜的美股`
- `查一下公告并顺便筛股`

改写思路：

- `帮我选好基金` -> `股票型基金有哪些？` 或 `近一年收益排名前十的基金`
- `帮我选涨得好的美股` -> `涨幅前五的美股`
- `帮我选规模大的` -> `管理规模排名前十的基金公司`

## search 写法

更适合“搜公告/新闻/研究报告/投资者关系活动”。

推荐结构：

- 实体/主题 + 内容类型 + 时间词
- 不要只写公司名或主题名

好的例子：

- `贵州茅台 公告`
- `最近一个月的分红公告`
- `人工智能最新动态`
- `芯片行业研究报告`
- `贵州茅台投资者关系活动`

不好的例子：

- `贵州茅台`
- `人工智能`
- `最近贵州茅台和五粮液有什么公告？`

改写思路：

- `贵州茅台` -> `贵州茅台 公告` 或 `贵州茅台 最新动态`
- `人工智能` -> `人工智能最新动态` 或 `人工智能行业研究报告`
- `最近贵州茅台和五粮液有什么公告？` -> `贵州茅台 公告` + `五粮液 公告`

## trade 命令写法

trade 不是自然语言 query 入口，而是显式子命令。

更适合“开户、下单、查持仓、查资金、查历史成交”。

推荐结构：

- `trade bootstrap-account`
- `trade buy|sell --stock-code <6位代码> --quantity <100股整数倍> --price <价格>`
- `trade positions|profit|fund|today-trades|gain-30d`
- `trade history-trades --start-date <YYYYMMDD> --end-date <YYYYMMDD>`

好的例子：

- `iwencai trade bootstrap-account`
- `iwencai trade buy --stock-code 600519 --quantity 100 --price 1500`
- `iwencai trade positions --format table`
- `iwencai trade history-trades --start-date 20240101 --end-date 20240131`

不好的例子：

- `买入600519 100股 价格1500元`
- `看看我持仓有哪些`
- `顺便帮我看看持仓再买点白酒`

## 为什么总查不出结果

常见原因：

- query 太像聊天，没有核心金融词。
- 只写“好/强/便宜/大”，没写指标、阈值或排序。
- search 没写内容类型，只写了公司名或主题。
- 把搜索、筛选、交易混进同一条 query。
- 一个 query 里塞了多个公司、多个维度，但没有拆分。
- 用“这只基金”“那个股票”这类依赖上下文的说法。

遇到空结果时，优先这样改：

1. 去掉铺垫，只保留金融关键词。
2. 补齐实体、内容类型、指标、比较词、时间词。
3. 把口语改成标准金融术语。
4. 把复合问题拆成多条 query。

## 帮助文档

```bash
iwencai --help
iwencai query2data --help
iwencai search --help
iwencai trade --help
```

更底层的 query 规则固化在：

- `specs/QUERY_AUTHORING.SPEC.yaml`
- `specs/QUERY_AUTHORING.RULE.yaml`
