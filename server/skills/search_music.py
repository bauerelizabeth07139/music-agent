"""Web Music Search Skill - searches for music references online.

This skill helps the AI find music references, chord progressions,
and style examples by searching the web.
"""

import httpx
import json
import re
from typing import Optional


async def search_music_info(query: str) -> dict:
    """Search for music information online.

    Uses DuckDuckGo instant answers API (no API key needed).
    Returns relevant music info like chord progressions, style references, etc.
    """
    results = []

    # Search DuckDuckGo for music info
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            if resp.status_code == 200:
                data = resp.json()

                # Abstract (main answer)
                if data.get("Abstract"):
                    results.append({
                        "type": "info",
                        "source": data.get("AbstractSource", ""),
                        "text": data["Abstract"],
                    })

                # Related topics
                for topic in data.get("RelatedTopics", [])[:5]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "type": "related",
                            "text": topic["Text"][:200],
                        })
    except Exception as e:
        results.append({"type": "error", "text": f"Search failed: {str(e)}"})

    return {
        "query": query,
        "results": results,
        "count": len(results),
    }


async def search_chord_progression(genre: str, key: str = "C") -> dict:
    """Search for common chord progressions for a genre."""
    query = f"{genre} music common chord progression in {key} major"
    return await search_music_info(query)


async def search_song_reference(description: str) -> dict:
    """Search for song references matching a description."""
    query = f"songs similar to {description} music style"
    return await search_music_info(query)