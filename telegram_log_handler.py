import logging
import os
import requests
from dotenv import load_dotenv

# 加载.env
load_dotenv()

class TelegramLogHandler(logging.Handler):
    """
    日志推送到Telegram bot的Handler。
    emit时同步POST到Bot API，支持等级过滤、内容分段、异常catch降级。
    配置项：LOG_BOT_TOKEN, LOG_BOT_CHAT_ID, LOG_BOT_LEVEL
    """
    def __init__(self, level=None):
        super().__init__()
        self.bot_token = os.getenv('LOG_BOT_TOKEN')
        self.chat_id = os.getenv('LOG_BOT_CHAT_ID')
        self.level_name = os.getenv('LOG_BOT_LEVEL', 'ERROR').upper()
        self.setLevel(level or getattr(logging, self.level_name, logging.ERROR))
        if not self.bot_token or not self.chat_id:
            raise ValueError('LOG_BOT_TOKEN或LOG_BOT_CHAT_ID未配置于.env')
        try:
            self.chat_id = int(self.chat_id)
        except Exception:
            raise ValueError('LOG_BOT_CHAT_ID必须为整数')
        self.api_url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'

    def emit(self, record):
        try:
            msg = self.format(record)
            # Telegram单条消息最大4096字符，需分段
            parts = [msg[i:i+4096] for i in range(0, len(msg), 4096)]
            for part in parts:
                payload = {
                    'chat_id': self.chat_id,
                    'text': part
                }
                resp = requests.post(self.api_url, data=payload, timeout=5)
                if not resp.ok:
                    # 失败时降级为本地日志
                    logging.getLogger(__name__).warning(f'Telegram日志推送失败: {resp.text}')
        except Exception as e:
            # 任何异常不影响主业务
            logging.getLogger(__name__).warning(f'TelegramLogHandler异常: {e}') 