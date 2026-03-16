"""腾讯混元大模型供应商。

通过 OpenAI 兼容接口调用腾讯混元大模型，支持 hunyuan-lite 等模型。
API 文档: https://cloud.tencent.com/document/product/1729/111007
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ai_parenting.providers.base import ModelProvider

logger = logging.getLogger(__name__)


class HunyuanProvider(ModelProvider):
    """腾讯混元大模型供应商实现。

    使用 OpenAI 兼容的 /chat/completions 接口。

    Args:
        api_key: 混元 API 密钥。
        base_url: 混元 API 基础 URL。
        model: 模型名称，默认 hunyuan-lite。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.hunyuan.cloud.tencent.com/v1",
        model: str = "hunyuan-lite",
    ) -> None:
        if not api_key:
            raise ValueError("Hunyuan API key must not be empty")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def provider_name(self) -> str:
        return "hunyuan"

    @property
    def model_version(self) -> str:
        return self._model

    async def generate(self, prompt: str, timeout_seconds: float) -> str:
        """调用混元大模型生成响应。

        Args:
            prompt: 完整的 Prompt 文本。
            timeout_seconds: 超时时间（秒）。

        Returns:
            模型返回的文本内容（预期为 JSON 格式字符串）。

        Raises:
            asyncio.TimeoutError: 请求超时。
            httpx.HTTPStatusError: HTTP 错误响应。
            Exception: 其他调用异常。
        """
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一位专业的儿童发展与家庭教育专家。"
                        "你的输出必须是纯 JSON 格式，不要包含任何 markdown 标记或额外文字说明。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "top_p": 0.9,
        }

        logger.info(
            "Calling Hunyuan API: model=%s, prompt_length=%d, timeout=%.1fs",
            self._model,
            len(prompt),
            timeout_seconds,
        )

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            # 从 OpenAI 兼容格式中提取内容
            content = data["choices"][0]["message"]["content"]

            # 清理可能的 markdown 代码块包裹
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            logger.info(
                "Hunyuan API response received: content_length=%d, "
                "usage=%s",
                len(content),
                data.get("usage", {}),
            )
            return content

        except httpx.TimeoutException as exc:
            logger.error("Hunyuan API timeout after %.1fs", timeout_seconds)
            raise asyncio.TimeoutError(
                f"Hunyuan API timeout after {timeout_seconds}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Hunyuan API HTTP error: status=%d, body=%s",
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise
        except KeyError as exc:
            logger.error(
                "Hunyuan API unexpected response format: %s", exc
            )
            raise ValueError(
                f"Unexpected Hunyuan API response format: missing {exc}"
            ) from exc
