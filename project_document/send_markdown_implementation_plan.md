# Telegram多账户工具发送Markdown消息功能实现方案

## 需求分析

为Telegram多账户工具添加发送Markdown消息功能，具体要求：
1. 创建`messages.json`文件存储可手动编辑的Markdown消息模板（已存在）
2. 在`main.py`中新增`send-markdown`命令，该命令读取并随机选择一条消息
3. 调用Telethon的`send_message`方法，并设置`parse_mode='md'`来发送消息

## 实现方案

### 1. 功能设计

在`main.py`中添加新的命令行命令`send-markdown`，该命令应该：
- 接受`dialog_id`参数（必需）
- 接受`--delete-after`选项（可选，N秒后自动删除消息）
- 读取`messages.json`文件
- 随机选择一条消息
- 使用`parse_mode='md'`参数发送消息
- 处理消息删除逻辑（如果指定了--delete-after）

### 2. 代码实现

在`main.py`中添加以下函数：

```python
@cli.command()
@click.argument('dialog_id', type=str)
@click.option('--delete-after', type=int, default=None, help='N秒后自动删除消息')
@click.pass_context
def send_markdown(ctx, dialog_id, delete_after):
    """从messages.json中随机选择一条Markdown消息发送到指定dialog_id，可选N秒后自动删除。"""
    async def _send():
        client = TelegramClient(
            ctx.obj['session'],
            ctx.obj['api_id'],
            ctx.obj['api_hash'],
            proxy=ctx.obj['proxy']
        )
        async with client:
            # 读取messages.json文件
            try:
                with open('messages.json', 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                if not messages:
                    logger.error('messages.json文件为空')
                    return
            except FileNotFoundError:
                logger.error('未找到messages.json文件')
                return
            except json.JSONDecodeError as e:
                logger.error(f'messages.json文件格式错误: {e}')
                return
            
            # 随机选择一条消息
            message = random.choice(messages)
            logger.info(f'向{dialog_id}发送Markdown消息: {message}')
            
            try:
                response = await client.send_message(int(dialog_id), message, parse_mode='md')
                if response:
                    logger.info(f'Markdown消息发送成功！')
                    if delete_after:
                        await asyncio.sleep(delete_after)
                        await client.delete_messages(int(dialog_id), response.id)
                        logger.info('消息已删除')
            except Exception as e:
                logger.error(e)
    asyncio.run(_send())
```

### 3. 错误处理

需要处理以下异常情况：
- `messages.json`文件不存在
- `messages.json`文件格式错误
- `messages.json`文件为空数组
- 网络异常或Telegram API错误
- 消息发送失败

### 4. 使用示例

```bash
# 发送Markdown消息
uv run main.py -a fury send-markdown 77893

# 发送Markdown消息并在10秒后删除
uv run main.py -a fury send-markdown --delete-after 10 77893
```

## 测试计划

1. 验证命令是否正确添加到CLI
2. 测试正常发送Markdown消息功能
3. 测试消息删除功能
4. 测试错误处理机制
5. 验证日志记录是否正确

## 文档更新

需要更新`README.md`文件，添加新命令的使用说明：
- 命令语法
- 参数说明
- 使用示例
- 注意事项