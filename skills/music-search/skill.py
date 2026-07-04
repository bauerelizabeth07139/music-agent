"""Music reference search skill. Only searches for specific/unknown items."""

from __future__ import annotations
import html, re
from typing import List
import httpx

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

STYLE_TIPS = {
    "pop": ["常用和弦 C-G-Am-F，副歌张力上行", "BPM 96-120，中速律动"],
    "rock": ["强力和弦 A-D-E，八分驱动", "BPM 110-140"],
    "jazz": ["ii-V-I (Dm7-G7-Cmaj7)，延伸音", "swing 或 bossa 律动"],
    "folk": ["木吉他分解和弦 I-V-vi-IV", "BPM 88-112 叙事风格"],
    "electronic": ["合成器主导 Am-F-C-G", "build-up/drop 结构"],
    "hiphop": ["鼓组律动优先于和弦", "808低音+采样"],
    "rnb": ["色彩和弦+切分律动", "Cmaj7-Dm7-Em7-Fmaj7"],
    "cinematic": ["弦乐渐进推进", "持续音底色+张力和弦"],
}

def _offline(prompt: str, style: str = "") -> List[dict]:
    results = []
    tips = STYLE_TIPS.get((style or "").lower(), [])
    if tips:
        results.append({"type": "local", "text": f"风格建议（{style}）：" + "；".join(tips)})
    if prompt:
        results.append({"type": "local", "text": f"结构建议：围绕“{prompt[:60]}”构建主歌-副歌对比，避免重复旋律轮廓。"})
    return results

def _clean(v: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(v or ""))).strip()

def _extract(raw: str, limit: int = 5) -> List[dict]:
    results = []
    for block in re.findall(r'<li class="b_algo">(.*?)</li>', raw, re.S | re.I):
        title = _clean(re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S | re.I).group(1)) if re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S | re.I) else ""
        text = _clean(re.search(r"<p[^>]*>(.*?)</p>", block, re.S | re.I).group(1)) if re.search(r"<p[^>]*>(.*?)</p>", block, re.S | re.I) else ""
        text = text or title
        if text and len(text) > 4:
            results.append({"type": "related", "source": "bing", "title": title[:80], "text": text[:200]})
        if len(results) >= limit: break
    if not results:
        for m in re.finditer(r'<div class="b_caption"[^>]*>(.*?)</div>', raw, re.S | re.I):
            title = _clean(re.search(r"<h2[^>]*>(.*?)</h2>", m.group(1), re.S | re.I).group(1)) if re.search(r"<h2[^>]*>(.*?)</h2>", m.group(1), re.S | re.I) else ""
            text = _clean(re.search(r"<p[^>]*>(.*?)</p>", m.group(1), re.S | re.I).group(1)) if re.search(r"<p[^>]*>(.*?)</p>", m.group(1), re.S | re.I) else ""
            text = text or title
            if text and len(text) > 4:
                results.append({"type": "related", "source": "bing", "title": title[:80], "text": text[:200]})
            if len(results) >= limit: break
    return results

async def search_music_info(query: str) -> dict:
    results, source = [], "offline"
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=_HEADERS) as c:
            r = await c.get("https://www.bing.com/search", params={"q": query})
            if r.status_code == 200 and len(r.text) > 1000:
                results = _extract(r.text)
                source = "bing" if results else "bing-empty"
    except Exception: source = "offline"
    if not results: results = _offline(query); source = "offline"
    return {"query": query, "results": results, "count": len(results), "source": source}

async def gather_references_for_prompt(prompt: str, style: str = "", key: str = "C") -> dict:
    # Don't search for style—use local knowledge. Only search for specific unknowns.
    results = _offline(prompt, style)
    source = "offline"

    # Only search if prompt contains specific unknown references (e.g. a song name, artist)
    # Extract keywords: look for quoted text or proper nouns
    keywords = re.findall(r"[""「]([^""」]+)[""」]", prompt)
    if not keywords:
        # Check for specific song/artist patterns
        keywords = re.findall(r"(?:像|类似|参考|模仿)\s*(\S+)", prompt)

    if keywords:
        query = " ".join(keywords[:3]) + " 音乐风格"
        try:
            web = await search_music_info(query)
            if web.get("results"):
                source = web.get("source", "mixed")
                results.extend(web["results"][:3])
        except Exception:
            pass

    seen = set()
    unique = []
    for r in results:
        t = r.get("text", "")
        if t and t not in seen:
            seen.add(t)
            unique.append(r)

    return {"prompt": prompt, "style": style, "results": unique[:8], "count": len(unique[:8]), "source": source}