import os
import sys
import logging
import asyncio
import click
from dotenv import load_dotenv
from python_socks import ProxyType
from telethon import TelegramClient

# 加载.env
load_dotenv()

logging.basicConfig(
    format = "%(asctime)s %(levelname)s:%(name)s: %(message)s",
    level = logging.INFO,
    datefmt = "%H:%M:%S",
    stream = sys.stderr
)
logger = logging.getLogger(__name__)

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
                    logger.info(f'消息发送成功: {response.text}')
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

if __name__ == '__main__':
    cli(obj={})
