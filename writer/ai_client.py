"""AI API 客户端。兼容 DeepSeek / OpenAI / 通义千问 等兼容接口。"""

from openai import OpenAI

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def get_client() -> OpenAI:
    """获取 AI 客户端实例。"""
    if not settings.ai_api_key:
        raise ValueError(
            "未配置 AI_API_KEY。\n"
            "1. 复制 .env.example 为 .env\n"
            "2. 填入你的 API Key\n"
            f"   DeepSeek: https://platform.deepseek.com  (推荐)\n"
            f"   通义千问: https://dashscope.aliyun.com\n"
        )
    return OpenAI(api_key=settings.ai_api_key, base_url=settings.ai_base_url)


def chat(messages: list[dict], **kwargs) -> str:
    """调用 AI 模型进行对话。"""
    client = get_client()
    model = kwargs.pop("model", settings.ai_model)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=kwargs.pop("temperature", 0.7),
        max_tokens=kwargs.pop("max_tokens", 4096),
        **kwargs,
    )
    content = resp.choices[0].message.content.strip()
    # 统计 token 用量
    if resp.usage:
        logger.info(
            f"AI 调用完成 | 模型={model} "
            f"| 输入={resp.usage.prompt_tokens} tokens "
            f"| 输出={resp.usage.completion_tokens} tokens"
        )
    return content
