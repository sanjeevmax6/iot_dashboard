import pytest
from unittest.mock import MagicMock, patch

from agent.llm_rerouter import get_llm


def test_get_llm_openai_returns_chat_model():
    with patch("agent.llm_rerouter.settings") as mock_settings:
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.openai_api_key = "sk-dummy"

        mock_instance = MagicMock()
        with patch("langchain_openai.ChatOpenAI", return_value=mock_instance) as MockCls:
            result = get_llm()

        MockCls.assert_called_once_with(
            model="gpt-4o-mini", temperature=0, api_key="sk-dummy"
        )
        assert result is mock_instance


def test_get_llm_bedrock_returns_chat_model():
    with patch("agent.llm_rerouter.settings") as mock_settings:
        mock_settings.llm_provider = "bedrock"
        mock_settings.bedrock_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        mock_settings.bedrock_region = "us-east-1"

        mock_instance = MagicMock()
        with patch("langchain_aws.ChatBedrock", return_value=mock_instance) as MockCls:
            result = get_llm()

        MockCls.assert_called_once_with(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name="us-east-1",
        )
        assert result is mock_instance


def test_get_llm_unknown_provider_raises():
    with patch("agent.llm_rerouter.settings") as mock_settings:
        mock_settings.llm_provider = "unknown_provider"
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm()
