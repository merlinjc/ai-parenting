"""模型供应商测试。

覆盖：
- MockProvider 基本功能
- 超时模拟
- 非法 JSON 模拟
- 多次调用不同响应
"""

import asyncio

import pytest

from ai_parenting.providers.base import ModelProvider
from ai_parenting.providers.mock_provider import MockProvider


# ---------------------------------------------------------------------------
# ModelProvider Interface Tests
# ---------------------------------------------------------------------------


class TestModelProviderInterface:
    def test_mock_provider_is_model_provider(self):
        provider = MockProvider()
        assert isinstance(provider, ModelProvider)

    def test_provider_name(self):
        provider = MockProvider()
        assert provider.provider_name == "mock"

    def test_model_version(self):
        provider = MockProvider()
        assert provider.model_version == "mock-v1"


# ---------------------------------------------------------------------------
# MockProvider Tests
# ---------------------------------------------------------------------------


class TestMockProvider:
    @pytest.mark.asyncio
    async def test_basic_response(self):
        provider = MockProvider(response_json='{"result": "ok"}')
        response = await provider.generate("test prompt", timeout_seconds=5.0)
        assert response == '{"result": "ok"}'
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_simulate_timeout(self):
        provider = MockProvider(simulate_timeout=True)
        with pytest.raises(asyncio.TimeoutError):
            await provider.generate("test", timeout_seconds=0.1)

    @pytest.mark.asyncio
    async def test_simulate_invalid_json(self):
        provider = MockProvider(simulate_invalid_json=True)
        response = await provider.generate("test", timeout_seconds=5.0)
        assert "not valid json" in response

    @pytest.mark.asyncio
    async def test_multiple_responses(self):
        provider = MockProvider()
        provider.set_responses(["first", "second", "third"])
        r1 = await provider.generate("test", timeout_seconds=5.0)
        r2 = await provider.generate("test", timeout_seconds=5.0)
        r3 = await provider.generate("test", timeout_seconds=5.0)
        assert r1 == "first"
        assert r2 == "second"
        assert r3 == "third"
        assert provider.call_count == 3

    @pytest.mark.asyncio
    async def test_call_count_increments(self):
        provider = MockProvider(response_json='{}')
        assert provider.call_count == 0
        await provider.generate("test", timeout_seconds=5.0)
        assert provider.call_count == 1
        await provider.generate("test", timeout_seconds=5.0)
        assert provider.call_count == 2
