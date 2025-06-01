# Telegram 多账户命令行机器人

> 更新时间：2025-06-01 23:06:45 +08:00

## 项目简介
本项目基于 Telethon，支持多账户、集中 session 管理、命令行灵活操作（消息发送、登录、登出、延迟删除、代理等），适用于 Telegram 群组/频道自动化、批量运维等场景。

## 核心特性
- 多账户支持，账户配置集中于 .env，字段如 ANZO_API_ID/ANZO_API_HASH。
- 所有 session 文件集中于 `sessions/` 目录，命名为 `{account}.session`。
- 命令行接口基于 click，支持账户切换、代理、消息发送与删除、登录登出等。
- 日志安全、参数校验、异常处理完善。
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
   ```
3. **确保 `sessions/` 目录存在**，所有 session 文件将自动存放于此。

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
- **dialog_id 为负数时的用法**
  > **注意：** 如果 dialog_id 为负数，需在参数前加 `--`，如：
  ```bash
  uv run main.py -a fury send-text --delete-after 10 -- -105275 hello
  ```
  `--` 告诉命令行解析器，后面的内容全部作为"位置参数"处理，不再解析为选项。

## 参数说明
- `-a/--account`：账户名（如 anzo, fury），必填。
- `-p/--proxy`：代理地址（如 socks5://localhost:3067），可选。
- `send-text`：发送消息命令，需指定 dialog_id 和消息内容。
- `--delete-after`：N 秒后自动删除消息，可选。
- `login`/`logout`：登录/登出账户。

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
- **日志是否包含敏感信息？**
  日志不记录 API 密钥等敏感信息。

## 文档与归档说明
- 所有设计、决策、会议纪要、实现细节均归档于 `/project_document/` 目录，详见 `tgsigner_task.md`。
- 会议纪要、Checklist、进度与回顾等均严格遵循 RIPER-5 文档管理标准。

---
如需更多帮助或扩展功能，请查阅 `/project_document/` 或联系维护者。
