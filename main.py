import os
import sys
import logging
import asyncio
import click
from dotenv import load_dotenv
from python_socks import ProxyType
from telethon import TelegramClient
from logging.handlers import RotatingFileHandler
from telegram_log_handler import TelegramLogHandler

# 加载.env
load_dotenv()

# {{CHENGQI:
# Action: [Added/Modified]
# Timestamp: 2025-06-02 10:53:33 +08:00 // Reason: [实现本地日志持久化，按方案B，RotatingFileHandler，满足可维护性与追溯需求]
# Principle_Applied: [KISS/DRY/SOLID - 结构简单，日志轮转防止单文件过大，便于维护，控制台与文件双输出，日志目录自动创建]
# Optimization: [自动创建logs目录，日志文件轮转，便于后续扩展多Handler或灵活配置]
# Architectural_Note (AR): [日志与主业务解耦，便于后续扩展和维护]
# Documentation_Note (DW): [日志策略与实现细节已同步至/project_document/，含时间戳与变更原因]
# }}
# {{START MODIFICATIONS}}
LOG_DIR = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
log_file = os.path.join(LOG_DIR, 'main.log')

# 设置RotatingFileHandler
file_handler = RotatingFileHandler(
    log_file, maxBytes=10*1024*1024, backupCount=7, encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
))
file_handler.setLevel(logging.INFO)

# 控制台Handler
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s:%(name)s: %(message)s", datefmt="%H:%M:%S"
))
console_handler.setLevel(logging.INFO)

# 主logger配置
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# 移除默认Handler，防止重复输出
logger.handlers = []
logger.addHandler(file_handler)
logger.addHandler(console_handler)
try:
    telegram_handler = TelegramLogHandler()
    telegram_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(telegram_handler)
except Exception as e:
    logger.warning(f"未启用Telegram日志推送Handler: {e}")
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
            await client.start()
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

if __name__ == '__main__':
    cli(obj={})
