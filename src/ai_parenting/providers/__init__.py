"""模型供应商适配层。"""

from ai_parenting.providers.base import ModelProvider
from ai_parenting.providers.mock_provider import MockProvider

__all__ = ["ModelProvider", "MockProvider"]

# 延迟导入 HunyuanProvider 以避免强制依赖 httpx
try:
    from ai_parenting.providers.hunyuan_provider import HunyuanProvider  # noqa: F401

    __all__.append("HunyuanProvider")
except ImportError:
    pass
