# 日志策略与变更记录

- 文档创建时间：2025-06-02 10:54:01 +08:00
- 责任人：DW（文档负责人）
- 适用项目：tgsigner-20250601-2206

---
## 1. 日志本地持久化与多账户隔离方案（2025-06-02 16:22:08 +08:00更新）
- 日志采用Python logging模块，主Handler为RotatingFileHandler，支持多Handler（控制台、文件、Telegram等）。
- 日志文件路径：logs/{account}.log（每个account独立日志文件，自动创建logs目录）。
- 日志内容每条均自动带account字段（通过AccountFilter(logging.Filter)自动注入，调用端无侵入）。
- 单文件最大10MB，最多保留7个历史文件，超出自动轮转。
- 日志级别：INFO及以上。
- 控制台、文件、Telegram等多Handler并存，日志格式统一，便于开发、生产与远程监控。
- 日志内容不含API_ID、API_HASH等敏感信息。

## 2. 配置说明
- 日志目录与文件自动创建，无需手动干预。
- Handler/Formatter/Filter均在cli入口按account动态配置，日志内容和文件均带account。
- 轮转策略可通过修改main.py中RotatingFileHandler参数调整。
- 后续可扩展多Handler、灵活配置日志级别、远程同步、自动化分析等。

## 3. 安全注意事项
- 严禁将敏感信息（如API_ID、API_HASH、session路径等）写入日志。
- logs/目录建议设置合理权限，防止未授权访问。
- 日志推送到Telegram时，内容同样自动带account，便于溯源。

## 4. 变更历史（Newest First）
---
### [2025-06-03 13:19:28 +08:00] 文档同步：README.md 本地日志持久化部分修订
- 按最新日志系统实现，README.md 本地日志持久化部分已修订为 logs/{account}.log，每个账户独立日志文件，结构化分条说明，FAQ补充文件名示例。
- 变更原因：日志系统升级为多账户隔离，文档需与实际实现同步，提升可读性与可用性。
- 责任人：DW
---
### [2025-06-02 16:22:08 +08:00] 日志系统升级：多账户隔离与account自动注入
- 日志文件按account区分，路径为logs/{account}.log。
- 日志内容每条均自动带account字段，AccountFilter(logging.Filter)自动注入，调用端无侵入。
- Handler/Formatter/Filter动态配置，兼容RotatingFileHandler、StreamHandler、TelegramLogHandler等多Handler。
- 结构KISS/DRY/SOLID，便于维护与扩展。
- 变更原因：满足多账户日志隔离、内容可溯源、结构可维护性与扩展性需求。
- 责任人：AR、LD、DW
---
### [2025-06-02 10:54:01 +08:00] 日志本地持久化功能上线
- 方案采用RotatingFileHandler，日志文件logs/main.log，单文件最大10MB，最多7个历史文件。
- 自动创建logs目录，控制台与文件双输出。
- 变更原因：提升可维护性与问题追踪能力，防止日志丢失或单文件过大。
- 责任人：LD、DW
--- 