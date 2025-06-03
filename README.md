# Telegram 多账户命令行自动化与日志推送工具

> 支持批量运维、集中 session 管理、日志推送到 Telegram bot 与本地持久化
> 更新时间：2025-06-03 14:24:06 +08:00

## 项目简介
本项目基于 Telethon，支持多账户、集中 session 管理、命令行灵活操作（消息发送、登录、登出、延迟删除、代理、对话查询等），适用于 Telegram 群组/频道自动化、批量运维等场景。

## 核心特性
- 多账户支持，账户配置集中于 .env，字段如 ANZO_API_ID/ANZO_API_HASH。
- 所有 session 文件集中于 `sessions/` 目录，命名为 `{account}.session`。
- 命令行接口基于 click，支持账户切换、代理、消息发送与删除、登录登出、对话查询等。
- 日志安全、参数校验、异常处理完善。
- 日志可自动推送到 Telegram bot，支持本地持久化、分段、等级过滤、异常降级。
- 结构清晰，便于扩展批量/文件发送等功能。

## 快速开始
1. **安装依赖**
   ```bash
   uv sync --default-index https://pypi.tuna.tsinghua.edu.cn/simple
   ```
2. **配置 .env**（参考 .env.example）
   ```env
   # anzo 账户
   ANZO_API_ID=123456
   ANZO_API_HASH=abcdef1234567890abcdef1234567890
   # fury 账户
   FURY_API_ID=654321
   FURY_API_HASH=098765fedcba098765fedcba098765fe
   # Telegram 日志推送配置
   LOG_BOT_TOKEN=your_bot_token_here
   LOG_BOT_CHAT_ID=123456789
   LOG_BOT_LEVEL=ERROR
   ```
3. **确保 `sessions/` 和 `logs/` 目录存在**，首次运行会自动创建，无需手动操作。

## 命令行用法
以 uv 为例：

- **发送消息并 10 秒后删除**
  ```bash
  uv run main.py -a fury send-text --delete-after 10 77893 hello
  ```
- **使用代理**
  ```bash
  uv run main.py -a anzo -p socks5://localhost:3067 send-text --delete-after 5 77893 签到
  ```
- **登录账户（首次/需验证码时）**
  ```bash
  uv run main.py -a anzo login
  ```
- **登出账户**
  ```bash
  uv run main.py -a fury logout
  ```
- **查询所有对话（dialog）ID与名称**
  ```bash
  uv run main.py -a anzo list-dialogs
  ```
- **dialog_id 为负数时的用法**
  > **注意：** 如果 dialog_id 为负数，需在参数前加 `--`，如：
  ```bash
  uv run main.py -a fury send-text --delete-after 10 -- -105275 hello
  ```
  `--` 告诉命令行解析器，后面的内容全部作为"位置参数"处理，不再解析为选项。
- **发送消息并监听回复写入日志**
  ```bash
  uv run main.py -a fury send-and-log-reply 77893 "你好，机器人" --timeout 30 --max-messages 1 --delete-after 5
  ```
  > 发送后自动监听目标对话的回复（默认首条，支持--timeout、--max-messages、--delete-after），收到内容自动写入日志。
  >
  > **说明：**
  > - `--delete-after` 倒计时从消息发送后立即开始，监听回复与消息删除互不阻塞。
  > - 若消息发送失败，不会启动监听/删除，日志有详细错误提示。

## 参数说明
- `-a/--account`：账户名（如 anzo, fury），必填。
- `-p/--proxy`：代理地址（如 socks5://localhost:3067），可选。
- `send-text`：发送消息命令，需指定 dialog_id 和消息内容。
- `--delete-after`：N 秒后自动删除消息，可选。
- `login`/`logout`：登录/登出账户。
- `list-dialogs`：查询所有对话ID与名称。
- `send-and-log-reply`：发送消息并监听目标对话回复，收到内容写入日志。参数：dialog_id, message, --timeout, --max-messages, --delete-after。监听与删除并发，delete-after倒计时从消息发送后立即开始。

## 日志推送与本地持久化
- **日志推送到Telegram bot**：
  - 需在.env中配置：
    - `LOG_BOT_TOKEN`：用于推送日志的bot token
    - `LOG_BOT_CHAT_ID`：日志推送目标chat_id（个人或群组）
    - `LOG_BOT_LEVEL`：推送日志的最低等级（如ERROR/CRITICAL/INFO）
  - 日志推送支持：
    - 日志等级过滤（仅推送高于设定等级的日志）
    - 内容分段（单条消息最大4096字符，自动分段推送）
    - 异常catch降级（推送失败自动降级为本地持久化，不影响主业务）
    - 敏感信息保护（日志不含API密钥等敏感信息）
  - 配置缺失或错误时，日志推送自动降级为本地持久化。
- **本地日志持久化**：
  - 日志文件存放于 `logs/{account}.log`，每个账户独立日志文件，统一存放于 logs/ 目录。
  - 日志文件自动轮转：单文件最大10MB，最多7个历史文件，超出自动轮转。
  - 控制台与文件双输出，便于开发与生产调试。
  - logs/目录首次运行自动创建。
  - 日志内容不含API_ID、API_HASH等敏感信息。
  - 建议设置logs/目录合理权限，防止未授权访问。
- **详细日志策略与安全说明**见 `/project_document/logging_policy.md`。

## 常见问题 FAQ
- **如何扩展新账户？**
  在 .env 中新增 `NEWACCOUNT_API_ID` 和 `NEWACCOUNT_API_HASH`，并在命令行用 `-a newaccount` 指定。
- **session 文件如何管理？**
  所有 session 文件自动存放于 `sessions/` 目录，命名为 `{account}.session`。
- **代理支持哪些格式？**
  支持 socks5/http，格式如 `socks5://host:port`。
- **dialog_id 为负数如何输入？**
  在命令行参数前加 `--`，如：
  ```bash
  uv run main.py -a fury send-text --delete-after 10 -- -105275 hello
  ```
- **如何查询所有对话ID与名称？**
  使用 `list-dialogs` 命令：
  ```bash
  uv run main.py -a anzo list-dialogs
  ```
- **日志推送到Telegram bot如何配置？推送失败会怎样？**
  需在.env配置LOG_BOT_TOKEN、LOG_BOT_CHAT_ID、LOG_BOT_LEVEL，推送失败自动降级为本地日志，不影响主业务。
- **日志本地持久化如何轮转？**
  日志文件最大10MB，最多7个历史文件，超出自动轮转。
- **本地日志文件示例？**
  日志文件按账户区分，示例：
  ```
  logs/anzo.log
  logs/fury.log
  ```
- **日志是否包含敏感信息？**
  日志不记录API密钥等敏感信息。
- **如何发送消息并监听回复写入日志？**
  使用 send-and-log-reply 命令：
  ```bash
  uv run main.py -a fury send-and-log-reply 77893 "你好，机器人" --timeout 30 --max-messages 1 --delete-after 5
  ```
  > 发送后自动监听目标对话的回复（默认首条，支持--timeout、--max-messages、--delete-after），收到内容自动写入日志。
  >
  > **说明：**
  > - `--delete-after` 倒计时从消息发送后立即开始，监听回复与消息删除互不阻塞。
  > - 若消息发送失败，不会启动监听/删除，日志有详细错误提示。
- **send-and-log-reply 异常场景说明**
  - 若消息发送失败（如网络异常、权限不足等），不会启动监听/删除，日志会详细记录错误。
  - 监听期间如遇超时、无回复、或删除失败，均有详细日志提示，便于排查。

## 文档与归档说明
- 所有设计、决策、会议纪要、实现细节、日志策略均归档于 `/project_document/` 目录，详见 `tgsigner_task.md`、`logging_policy.md`