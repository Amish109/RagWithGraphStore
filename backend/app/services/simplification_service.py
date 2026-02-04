"""Text simplification service with reading level control.

Provides simplified explanations of complex document content.
Implements QRY-07: User can request simplified explanations.

Simplification Levels:
- eli5: Explain like I'm 5 years old (elementary reading level)
- general: General audience explanation (8th grade reading level)
- professional: Professional but accessible (college reading level)

Uses two-stage prompting:
1. Generate initial simplified explanation
2. Verify and adjust to target reading level
"""

import logging
from typing import Dict, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


# Simplification levels with configuration
SIMPLIFICATION_LEVELS: Dict[str, Dict[str, str]] = {
    "eli5": {
        "description": "Explain like I'm 5 years old",
        "prompt": "Explain this in very simple terms that a child could understand. Use everyday analogies and avoid technical words.",
        "reading_level": "elementary"
    },
    "general": {
        "description": "General audience explanation",
        "prompt": "Explain this for someone with no background in this field. Use simple language and define any technical terms.",
        "reading_level": "8th grade"
    },
    "professional": {
        "description": "Professional but accessible",
        "prompt": "Explain this for a professional in a different field. Be clear but don't oversimplify technical concepts.",
        "reading_level": "college"
    }
}


async def simplify_text(
    text: str,
    level: str = "general",
    context: Optional[str] = None
) -> dict:
    """Simplify complex text to specified reading level.

    Uses two-stage prompting for consistent reading levels:
    1. Generate initial simplified explanation using level-specific prompt
    2. Verify and adjust to target reading level

    Args:
        text: The complex text to simplify.
        level: Simplification level (eli5, general, professional).
        context: Optional surrounding context to improve accuracy.

    Returns:
        Dict with original_text (truncated), simplified_text, level, level_description.
    """
    level_config = SIMPLIFICATION_LEVELS.get(level, SIMPLIFICATION_LEVELS["general"])

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.4,  # Slight creativity for explanations
        openai_api_key=settings.OPENAI_API_KEY,
    )

    # Stage 1: Initial simplification
    if context:
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an expert at explaining complex topics simply.
Target audience: {level_config['description']}.
Reading level: {level_config['reading_level']}.

{level_config['prompt']}"""),
            ("user", """Context from the document:
{context}

Complex text to simplify:
{text}

Simplified explanation:""")
        ])
        messages = prompt.format_messages(context=context, text=text)
    else:
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an expert at explaining complex topics simply.
Target audience: {level_config['description']}.
Reading level: {level_config['reading_level']}.

{level_config['prompt']}"""),
            ("user", """Complex text to simplify:
{text}

Simplified explanation:""")
        ])
        messages = prompt.format_messages(text=text)

    response = await llm.ainvoke(messages)
    simplified = response.content

    # Stage 2: Verify and adjust reading level
    verify_prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a reading level expert. Review this explanation and ensure it matches the target reading level: {level_config['reading_level']}.

If it's too complex, simplify further. If it's good, return it unchanged.
Only output the final explanation, no commentary."""),
        ("user", "{explanation}")
    ])

    messages = verify_prompt.format_messages(explanation=simplified)
    response = await llm.ainvoke(messages)

    logger.info(f"Simplified text at level '{level}': {len(text)} chars -> {len(response.content)} chars")

    return {
        "original_text": text[:500] + "..." if len(text) > 500 else text,
        "simplified_text": response.content,
        "level": level,
        "level_description": level_config["description"]
    }


async def simplify_document_section(
    document_id: str,
    user_id: str,
    section_text: str,
    level: str = "general"
) -> dict:
    """Simplify a specific section of a document with surrounding context.

    Retrieves nearby chunks for context to improve simplification accuracy.

    Args:
        document_id: ID of the source document (for context retrieval).
        user_id: ID of the user (for access control).
        section_text: The text section to simplify.
        level: Simplification level (eli5, general, professional).

    Returns:
        Dict with original_text, simplified_text, level, level_description.
    """
    from app.services.retrieval_service import retrieve_relevant_context

    context = None
    # Get context from document if document_id provided
    if document_id:
        try:
            context_result = await retrieve_relevant_context(
                query=section_text[:500],  # Use first 500 chars as query
                user_id=user_id,
                max_results=2
            )

            if context_result.get("chunks"):
                context = "\n".join([
                    chunk["text"] for chunk in context_result["chunks"]
                ])
                logger.info(f"Retrieved {len(context_result['chunks'])} context chunks for simplification")
        except Exception as e:
            logger.warning(f"Context retrieval failed, simplifying without context: {e}")

    return await simplify_text(
        text=section_text,
        level=level,
        context=context
    )
