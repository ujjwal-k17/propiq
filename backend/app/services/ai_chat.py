"""
AI Chat Service
===============
Provides context-aware Q&A on a real estate project using Claude / GPT-4.
Streams responses as server-sent events.

Context injected into the system prompt:
  - Project metadata (name, city, RERA, status, prices)
  - Latest risk score and red flags
  - Complaint summary
  - Developer track record
"""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from app.config import settings
from app.models.project import Project

SYSTEM_PROMPT_TEMPLATE = """You are PropIQ, an expert AI assistant specialising in Indian real estate due diligence.
You help home buyers and investors analyse residential and commercial projects with clarity and honesty.

## Project Context
Name: {name}
Developer: {developer}
City: {city} | Locality: {locality}
RERA ID: {rera_id}
Status: {status}
Possession Date: {possession_date}
Price Range: ₹{price_min}–₹{price_max} per sqft
Total Complaints: {complaints}

## Risk Assessment
Overall Score: {risk_score}/100 | Band: {risk_band}
Red Flags: {red_flags}

## Instructions
- Answer questions strictly based on the project context above and your knowledge of Indian real estate.
- If you don't have specific data, say so clearly — do not fabricate facts.
- Always recommend professional legal and financial advice for major decisions.
- Be concise but thorough. Use bullet points for lists.
- Flag any serious risk issues prominently.
"""


def _build_system_prompt(project: Project) -> str:
    latest_score = (
        project.risk_scores[-1] if project.risk_scores else None
    )
    developer_name = project.developer.name if project.developer else "Unknown"

    return SYSTEM_PROMPT_TEMPLATE.format(
        name=project.name,
        developer=developer_name,
        city=project.city,
        locality=project.locality or "N/A",
        rera_id=project.rera_id or "Not registered",
        status=project.status,
        possession_date=project.rera_possession_date or "Not specified",
        price_min=project.price_per_sqft_min or "N/A",
        price_max=project.price_per_sqft_max or "N/A",
        complaints=project.total_complaints,
        risk_score=latest_score.overall_score if latest_score else "Not computed",
        risk_band=latest_score.risk_band if latest_score else "Unknown",
        red_flags=json.dumps(latest_score.red_flags) if latest_score and latest_score.red_flags else "[]",
    )


async def stream_chat_response(
    project: Project,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Yield streamed text chunks from the AI model.
    Falls back gracefully if no API key is configured.
    """
    if settings.ANTHROPIC_API_KEY:
        async for chunk in _stream_anthropic(project, messages):
            yield chunk
    elif settings.OPENAI_API_KEY:
        async for chunk in _stream_openai(project, messages):
            yield chunk
    else:
        yield "AI chat is not configured. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY."


async def _stream_anthropic(project: Project, messages: list[dict]) -> AsyncGenerator[str, None]:
    import anthropic  # pip install anthropic

    system_prompt = _build_system_prompt(project)
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async with client.messages.stream(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def _stream_openai(project: Project, messages: list[dict]) -> AsyncGenerator[str, None]:
    from openai import AsyncOpenAI  # pip install openai

    system_prompt = _build_system_prompt(project)
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    all_messages = [{"role": "system", "content": system_prompt}] + messages

    async with await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=all_messages,
        stream=True,
    ) as stream:
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
