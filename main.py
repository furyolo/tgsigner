import os
import sys
import logging
import asyncio
import click
import json
import random
from dotenv import load_dotenv
from python_socks import ProxyType
from telethon import TelegramClient
from logging.handlers import RotatingFileHandler
from telegram_log_handler import TelegramLogHandler
from telethon.events import NewMessage

# 加载.env
load_dotenv()

# {{CHENGQI:
# Action: [Added]
# Timestamp: 2025-06-02 16:09:23 +08:00 // Reason: [实现AccountFilter(logging.Filter)，自动注入account，日志内容带account，调用端无侵入]
# Principle_Applied: [KISS/DRY/SOLID - Filter单一职责，结构简单，日志内容自动注入account，便于维护与扩展]
# Optimization: [日志内容自动带account，Handler/Formatter配置解耦，便于后续多账户扩展]
# Architectural_Note (AR): [日志系统与主业务解耦，便于维护与扩展]
# Documentation_Note (DW): [AccountFilter实现与集成细节已同步至/project_document/，含时间戳与变更原因]
# }}
# {{START MODIFICATIONS}}
class AccountFilter(logging.Filter):
    def __init__(self, account):
        super().__init__()
        self.account = account
    def filter(self, record):
        record.account = self.account
        return True
# {{END MODIFICATIONS}}

# 账户配置加载
SUPPORTED_ACCOUNTS = [k.split('_')[0].lower() for k in os.environ.keys() if k.endswith('_API_ID')]

PROXY_TYPE_MAP = {
    'socks5': ProxyType.SOCKS5,
    'http': ProxyType.HTTP,
}

def get_account_config(account):
    account_upper = account.upper()
    api_id = os.getenv(f'{account_upper}_API_ID')
    api_hash = os.getenv(f'{account_upper}_API_HASH')
    if not api_id or not api_hash:
        raise click.ClickException(f"账户{account}的API_ID/API_HASH未配置或.env缺失")
    return int(api_id), api_hash

def get_session_path(account):
    return os.path.join('sessions', f'{account}.session')

def parse_proxy(proxy_str):
    if not proxy_str:
        return None
    # 支持socks5://host:port 或 http://host:port
    if '://' not in proxy_str:
        raise click.ClickException('代理格式应为socks5://host:port 或 http://host:port')
    scheme, addr = proxy_str.split('://', 1)
    if scheme not in PROXY_TYPE_MAP:
        raise click.ClickException('仅支持socks5/http代理')
    host, port = addr.split(':')
    return (PROXY_TYPE_MAP[scheme], host, int(port))

@click.group()
@click.option('-a', '--account', required=True, type=click.Choice(SUPPORTED_ACCOUNTS), help='账户名（如 anzo, fury）')
@click.option('-p', '--proxy', default=None, help='代理地址（如 socks5://localhost:3067）')
@click.pass_context
def cli(ctx, account, proxy):
    # 自动创建sessions目录
    sessions_dir = os.path.join(os.getcwd(), 'sessions')
    if not os.path.exists(sessions_dir):
        os.makedirs(sessions_dir)
    ctx.ensure_object(dict)
    ctx.obj['account'] = account
    ctx.obj['proxy'] = parse_proxy(proxy)
    ctx.obj['session'] = get_session_path(account)
    ctx.obj['api_id'], ctx.obj['api_hash'] = get_account_config(account)

    # {{CHENGQI:
    # Action: [Modified]
    # Timestamp: 2025-06-02 16:09:23 +08:00 // Reason: [日志Handler/Formatter/Filter按account动态配置，日志内容和文件均带account]
    # Principle_Applied: [KISS/DRY/SOLID - 动态配置，结构解耦，便于维护与扩展]
    # Optimization: [日志文件名logs/{account}.log，所有Handler均加AccountFilter，Formatter统一加%(account)s]
    # Architectural_Note (AR): [日志系统与主业务解耦，便于后续多账户扩展]
    # Documentation_Note (DW): [日志系统动态配置细节已同步至/project_document/，含时间戳与变更原因]
    # }}
    # {{START MODIFICATIONS}}
    global logger
    LOG_DIR = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    log_file = os.path.join(LOG_DIR, f'{account}.log')

    # 日志格式统一加account
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(account)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 文件Handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=7, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    file_handler.addFilter(AccountFilter(account))

    # 控制台Handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(AccountFilter(account))

    # Telegram Handler
    handlers = [file_handler, console_handler]
    try:
        telegram_handler = TelegramLogHandler()
        telegram_handler.setFormatter(formatter)
        telegram_handler.addFilter(AccountFilter(account))
        handlers.append(telegram_handler)
    except Exception as e:
        # 临时logger用于初始化异常
        tmp_logger = logging.getLogger(f'tgsigner.{account}.init')
        tmp_logger.warning(f"未启用Telegram日志推送Handler: {e}")

    # logger按account命名，防止多账户冲突
    logger = logging.getLogger(f'tgsigner.{account}')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    for h in handlers:
        logger.addHandler(h)
    # {{END MODIFICATIONS}}

@cli.command()
@click.argument('dialog_id', type=str)
@click.argument('message', type=str)
@click.option('--delete-after', type=int, default=None, help='N秒后自动删除消息')
@click.pass_context
def send_text(ctx, dialog_id, message, delete_after):
    """发送文本消息到指定dialog_id，可选N秒后自动删除。"""
    async def _send():
        client = TelegramClient(
            ctx.obj['session'],
            ctx.obj['api_id'],
            ctx.obj['api_hash'],
            proxy=ctx.obj['proxy']
        )
        async with client:
            logger.info(f'向{dialog_id}发送: {message}')
            try:
                response = await client.send_message(int(dialog_id), message)
                if response:
                    logger.info(f'消息发送成功！')
                    if delete_after:
                        await asyncio.sleep(delete_after)
                        await client.delete_messages(int(dialog_id), response.id)
                        logger.info('消息已删除')
            except Exception as e:
                logger.error(e)
    asyncio.run(_send())

@cli.command()
@click.pass_context
def login(ctx):
    """手动登录账户（首次/需验证码时用）。"""
    async def _login():
        client = TelegramClient(
            ctx.obj['session'],
            ctx.obj['api_id'],
            ctx.obj['api_hash'],
            proxy=ctx.obj['proxy']
        )
        async with client:
            logger.info('请根据提示完成登录...')
            await client.connect()
            if not await client.is_user_authorized():
                client.start()
            logger.info('登录完成')
    asyncio.run(_login())

@cli.command()
@click.pass_context
def logout(ctx):
    """登出账户。"""
    async def _logout():
        client = TelegramClient(
            ctx.obj['session'],
            ctx.obj['api_id'],
            ctx.obj['api_hash'],
            proxy=ctx.obj['proxy']
        )
        async with client:
            await client.log_out()
            logger.info('已登出')
    asyncio.run(_logout())

@cli.command()
@click.pass_context
def list_dialogs(ctx):
    """列出当前账户的所有对话（dialog），显示名称和ID。"""
    async def _list():
        client = TelegramClient(
            ctx.obj['session'],
            ctx.obj['api_id'],
            ctx.obj['api_hash'],
            proxy=ctx.obj['proxy']
        )
        async with client:
            logger.info('正在获取所有对话...')
            try:
                async for dialog in client.iter_dialogs():
                    print(f'{dialog.name} has ID {dialog.id}')
            except Exception as e:
                logger.error(e)
    asyncio.run(_list())

@cli.command()
@click.argument('dialog_id', type=str)
@click.argument('message', type=str)
@click.option('--timeout', type=int, default=30, help='等待回复的最大时长（秒），默认30秒')
@click.option('--max-messages', type=int, default=1, help='最多捕获多少条回复，默认1条')
@click.option('--delete-after', type=int, default=None, help='N秒后自动删除消息')
@click.pass_context
def send_and_log_reply(ctx, dialog_id, message, timeout, max_messages, delete_after):
    """发送消息到指定dialog_id，监听回复并写入日志。可选N秒后自动删除消息。"""
    async def _send_and_listen():
        client = TelegramClient(
            ctx.obj['session'],
            ctx.obj['api_id'],
            ctx.obj['api_hash'],
            proxy=ctx.obj['proxy']
        )
        received_msgs = []
        event = asyncio.Event()
        
        def is_target_reply(event_message):
            # 只监听目标对话的消息，且为新消息（不含自己发的）
            return (str(event_message.chat_id) == str(dialog_id)) and (not event_message.out)

        async def handler(event_message):
            if is_target_reply(event_message):
                logger.info(f'收到回复: {event_message.text}')
                received_msgs.append(event_message.text)
                if len(received_msgs) >= max_messages:
                    event.set()

        async def listen_replies():
            client.add_event_handler(handler, NewMessage(chats=int(dialog_id)))
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.info(f'监听超时（{timeout}秒），共收到{len(received_msgs)}条回复')
            finally:
                client.remove_event_handler(handler, NewMessage(chats=int(dialog_id)))

        async def del_after():
            try:
                await asyncio.sleep(delete_after)
                await client.delete_messages(int(dialog_id), response.id)
                logger.info('消息已删除')
            except Exception as e:
                logger.error(f'自动删除消息失败: {e}')

        async with client:
            logger.info(f'向{dialog_id}发送: {message}')
            try:
                response = await client.send_message(int(dialog_id), message)
                tasks = []
                if response and delete_after:
                    tasks.append(asyncio.create_task(del_after()))
                tasks.append(asyncio.create_task(listen_replies()))
                await asyncio.gather(*tasks)
            except Exception as e:
                logger.error(e)
    asyncio.run(_send_and_listen())

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
            # 只显示消息的前20个字符，避免日志过长
            message_preview = message[:20] + "..." if len(message) > 20 else message
            logger.info(f'向{dialog_id}发送Markdown消息: {message_preview}')
            
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

if __name__ == '__main__':
    cli(obj={})
