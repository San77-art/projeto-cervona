"""
Claude-based XML data extractor
"""

import re

from anthropic import AsyncAnthropic
from src.config.settings import settings
from src.agent.prompts import SYSTEM_PROMPT, get_extraction_prompt
import logging
import json

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_LARGE_XML_WARN_CHARS = 500_000  # well beyond any real NFe/NFCe; flag anomalies instead of silently truncating

class XMLExtractor:
    """Extrai dados de XMLs usando Claude"""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL

    async def extract(self, xml_content: str) -> dict:
        """
        Extract data from XML using Claude
        """
        try:
            logger.info(f"Extracting from XML ({len(xml_content)} chars)")
            if len(xml_content) > _LARGE_XML_WARN_CHARS:
                logger.warning(
                    f"XML content is unusually large ({len(xml_content)} chars) — "
                    "verify this is a genuine NFe/NFCe and not malformed input"
                )

            # Build message
            user_prompt = get_extraction_prompt(xml_content)

            # Call Claude
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=settings.CLAUDE_MAX_TOKENS,
                temperature=settings.CLAUDE_TEMPERATURE,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Parse response (strip markdown code fences if the model wrapped the JSON)
            response_text = _JSON_FENCE_RE.sub("", response.content[0].text.strip())
            result = json.loads(response_text)
            
            logger.info(f"Extraction successful: {len(result.get('items', []))} items")
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Claude: {e}")
            return {"error": "Invalid response format", "items": []}
        
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {"error": str(e), "items": []}

# Singleton
extractor = XMLExtractor()
