# Translation logic
import asyncio

# replace later with real translation model / API



import os
from langchain.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


openai_api_key = os.getenv("OPENAI_API_KEY")
translation_model = os.getenv("TRANSLATION_MODEL")
USE_OPENAI = bool(openai_api_key)
model =translation_model
base_url = os.getenv("BASE_URL")


# Create a single LLM instance at module level to avoid connection churn
if USE_OPENAI:
    _llm = ChatOpenAI(
        model=model,
        openai_api_key=openai_api_key,
        temperature=0,
        max_tokens=2000
    )
else:
    _llm = ChatOpenAI(
        model=model,
        openai_api_key="ollama",
        openai_api_base=base_url,
        temperature=0,
        max_tokens=2000
    )

def get_translation(prompt: str) -> str:
    # Create messages
    messages = [
        SystemMessage(content=f"Translate the following text into english : {prompt}. "
                              "Your response should only contain the translated text without any additional commentary. Only translate keeping the same meaning."),
        HumanMessage(content=f"Translate the following sentence into english : {prompt}.")
    ]

    # Get translation
    return _llm.invoke(messages).content



async def translate(text: str, source_lang: str) -> str:
    await asyncio.sleep(1)

    result= get_translation(text)

    return f"[Translated from {source_lang}] {result}"