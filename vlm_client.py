from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .config import (
    JSON_PRESENCE_PENALTY,
    JSON_REPETITION_PENALTY,
    JSON_TEMPERATURE,
    OCR_PRESENCE_PENALTY,
    OCR_REPETITION_PENALTY,
    OCR_TEMPERATURE,
    VLM_API_KEY,
    VLM_API_URL,
    VLM_MODEL_NAME,
)
from .markdown_postproc import fix_ocr_markdown, remove_parentheses_around_numbers
from .prompts import FRAGMENT_PROMPT, SYSTEM_PROMPT_JSON, SYSTEM_PROMPT_MD
from .schemas import parser


def invoke_vlm_ocr(b64_images: List[str]) -> str:
    llm = ChatOpenAI(
        base_url=VLM_API_URL,
        api_key=VLM_API_KEY,
        model=VLM_MODEL_NAME,
        temperature=OCR_TEMPERATURE,
        presence_penalty=OCR_PRESENCE_PENALTY,
        extra_body={"repetition_penalty": OCR_REPETITION_PENALTY},
    )

    all_md = []
    for b64 in b64_images:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT_MD),
            HumanMessage(
                content=[
                    {"type": "text", "text": FRAGMENT_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ]
            ),
        ]
        resp = llm.invoke(messages)
        cleaned = fix_ocr_markdown(resp.content.strip())
        all_md.append(cleaned)

    return "\n\n".join(md for md in all_md if md)


def invoke_vlm_json(markdown_text: str) -> dict:
    llm = ChatOpenAI(
        base_url=VLM_API_URL,
        api_key=VLM_API_KEY,
        model=VLM_MODEL_NAME,
        temperature=JSON_TEMPERATURE,
        presence_penalty=JSON_PRESENCE_PENALTY,
        extra_body={"repetition_penalty": JSON_REPETITION_PENALTY},
    )

    cleaned_md = remove_parentheses_around_numbers(markdown_text)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT_JSON),
        HumanMessage(content=[{"type": "text", "text": cleaned_md}]),
    ]

    response = llm.invoke(messages)
    parsed = parser.parse(response.content)
    result = parsed.model_dump(by_alias=True, exclude_none=False)

    required_keys = [
        "balance_head_table",
        "balance_dates_table",
        "balance_main_table_dates",
        "balance_main_table",
        "report_main_table",
    ]
    tables_data = result.get("tables_data", {})
    message = {key: "OK" if key in tables_data else "Missing" for key in required_keys}
    enriched = {"message": message, "xlsx": None, **result}
    return enriched
