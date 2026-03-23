from langchain_core.language_models import BaseChatModel

from app.core.config import settings


# Defined this layer to use my current OPEN AI setup, but to have AWS Bedrock Compatibility to ensure privacy of data
def get_llm() -> BaseChatModel:
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )
    if settings.llm_provider == "bedrock":
        from langchain_aws import ChatBedrock

        return ChatBedrock(
            model_id=settings.bedrock_model_id,
            region_name=settings.bedrock_region,
        )
    raise ValueError(f"Unknown LLM provider: '{settings.llm_provider}'. Must be 'openai' or 'bedrock'.")
