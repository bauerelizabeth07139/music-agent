"""Unified LLM client for MiMo models.

Voice system (official MiMo TTS voices):
  mimo_default  - 默认
  冰糖          - 女声甜
  茉莉          - 女声柔
  苏打          - 女声清
  白桦          - 男声低
  Mia           - 英文女
  Chloe         - 英文女2
  Milo          - 英文男
  Dean          - 英文男2
"""

from __future__ import annotations
import traceback
import logging

logger = logging.getLogger(__name__)
import httpx, json, base64, re, asyncio
from typing import Any, Dict, List, Optional
from config import get_config

TTS_MAX_CHARS = 900  # TTS text limit per request (chars, not tokens)

# ---------- Official MiMo TTS Voices ----------
VOICE_CATALOG = {
    "mimo_default": ("默认", "清晰自然的默认声音"),
    "冰糖":         ("冰糖", "甜美温柔的中文女声"),
    "茉莉":         ("茉莉", "柔和细腻的中文女声"),
    "苏打":         ("苏打", "清脆明亮的中文女声"),
    "白桦":         ("白桦", "低沉磁性的中文男声"),
    "Mia":          ("Mia", "英文女声"),
    "Chloe":        ("Chloe", "英文女声2"),
    "Milo":         ("Milo", "英文男声"),
    "Dean":         ("Dean", "英文男2"),
}

DEFAULT_SINGING_VOICE = "冰糖"
DEFAULT_SINGING_VOICE_MALE = "白桦"

TTS_STYLE_PROMPTS = {
    "播音":     "清晰自然的播报风格，语速适中，吐字清晰。",
    "甜美":     "温柔甜美的声音，语速适中。",
    "沉稳":     "沉稳有力的声音，语速适中。",
    "活力":     "年轻活力的声音，语速偏快。",
    "旁白":     "深沉浑厚的旁白叙述声音，语速稍慢，富有磁性。",
    "讲故事":   "生动有趣的讲故事声音，语速适中，表情丰富。",
    "唱歌_女":  "用甜美动人的女歌手方式演唱",
    "唱歌_男":  "用深情款款的男歌手方式演唱",
}

LEGACY_VOICE_MAP = {
    "mimo_default":   ("mimo_default", "播音"),
    "default_zh":     ("冰糖", "甜美"),
    "default_en":     ("Mia", "播音"),
    "zh_male_1":      ("白桦", "沉稳"),
    "zh_male_2":      ("白桦", "活力"),
    "zh_female_1":    ("茉莉", "甜美"),
    "zh_female_2":    ("苏打", "甜美"),
    "zh_child":       ("苏打", "活力"),
    "en_male_1":      ("Milo", "播音"),
    "en_female_1":    ("Mia", "播音"),
    "narrator":       ("白桦", "旁白"),
    "storyteller":    ("冰糖", "讲故事"),
    "singing_male":   ("白桦", "唱歌_男"),
    "singing_female": ("冰糖", "唱歌_女"),
}

REASONING_MODELS = {"mimo-v2.5-pro", "mimo-v2.5-pro-ultraspeed"}

STYLE_KNOWLEDGE = {
    "pop":        {"bpm": "96-120", "key": "C/G 大调", "chords": "I-V-vi-IV", "inst": "钢琴/吉他/鼓/贝斯", "tips": "副歌张力上行"},
    "rock":       {"bpm": "110-140", "key": "A/E 小调", "chords": "I-IV-V", "inst": "电吉他/贝斯/鼓", "tips": "强力和弦驱动"},
    "jazz":       {"bpm": "80-130", "key": "Bb/Eb", "chords": "ii-V-I", "inst": "钢琴/贝斯/萨克斯", "tips": "swing律动"},
    "electronic": {"bpm": "120-150", "key": "Am", "chords": "i-III-VII-VI", "inst": "合成器/鼓机", "tips": "build-up/drop"},
    "hiphop":     {"bpm": "80-100", "key": "小调", "chords": "i-VI-III-VII", "inst": "808鼓/采样", "tips": "鼓组律动"},
    "rnb":        {"bpm": "75-100", "key": "C/F", "chords": "Cmaj7-Dm7-Em7", "inst": "键盘/贝斯/鼓", "tips": "色彩和弦"},
    "folk":       {"bpm": "88-112", "key": "G/D", "chords": "I-V-vi-IV", "inst": "木吉他/口琴", "tips": "叙事风格"},
    "cinematic":  {"bpm": "60-100", "key": "Dm/Am", "chords": "i-VI-III-VII", "inst": "弦乐/铜管/打击", "tips": "张力推进"},
    "classical":  {"bpm": "60-140", "key": "多调", "chords": "I-IV-V-I", "inst": "弦乐/木管/钢琴", "tips": "主题发展"},
    "country":    {"bpm": "100-130", "key": "G/A", "chords": "I-IV-V", "inst": "班卓/木吉他/小提琴", "tips": "乡村叙事"},
    "blues":      {"bpm": "70-120", "key": "E/A", "chords": "I-IV-V 12小节", "inst": "吉他/口琴/钢琴", "tips": "蓝调音阶"},
}

AVAILABLE_INSTRUMENTS = [
    "piano", "guitar", "bass", "drums", "violin", "cello",
    "flute", "trumpet", "synth_pad", "synth_lead", "hulusi"
]


def _resolve_voice(voice_id: str):
    """Resolve a voice ID to (actual_voice_name, style_prompt)."""
    if voice_id in LEGACY_VOICE_MAP:
        return LEGACY_VOICE_MAP[voice_id]
    if voice_id in VOICE_CATALOG:
        return (voice_id, TTS_STYLE_PROMPTS.get("甜美", ""))
    return (DEFAULT_SINGING_VOICE, TTS_STYLE_PROMPTS.get("甜美", ""))


def _normalize_track_metadata(track: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure track has required fields."""
    if "id" not in track:
        track["id"] = f"track_{hash(str(track)) % 10000}"
    if "name" not in track:
        track["name"] = track["id"]
    if "role" not in track:
        track["role"] = "instrument"
    if "instrument" not in track:
        track["instrument"] = "piano"
    if "voice" not in track:
        track["voice"] = "" if track["role"] == "instrument" else DEFAULT_SINGING_VOICE
    if "channel" not in track:
        track["channel"] = 0
    if "part" not in track:
        track["part"] = "melody" if track["role"] == "vocal" else "accompaniment"
    if "volume" not in track:
        track["volume"] = 0.8
    return track


# ---------- JSON Extraction ----------
def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response with robust fallback strategies.
    
    Key insight: LLM often returns truncated JSON for large note arrays.
    We try truncation repair FIRST for large responses.
    """
    if not text or not text.strip():
        raise ValueError("Empty response")

    # Remove reasoning text before JSON
    first_brace = text.find('{')
    if first_brace < 0:
        raise ValueError(f"No JSON object found in response ({len(text)} chars)")
    
    if first_brace > 0:
        prefix = text[:first_brace].strip()
        if prefix and len(prefix) > 10:
            logger.info(f"[Extract] Removing {len(prefix)} chars of reasoning text")
    text = text[first_brace:].strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Balanced braces (handles non-truncated JSON)
    depth = 0
    end_pos = -1
    for j in range(len(text)):
        if text[j] == '{':
            depth += 1
        elif text[j] == '}':
            depth -= 1
            if depth == 0:
                end_pos = j
                break
    if end_pos > 0:
        candidate = text[:end_pos + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            cleaned = re.sub(r',\s*([\]}])', r'\1', candidate)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    # Strategy 3: Truncation repair (for large truncated responses)
    # This is critical for note generation where arrays get cut off
    candidate = text.rstrip()
    # Remove trailing incomplete field/object
    candidate = re.sub(r',\s*"[^"]*$', '', candidate)
    candidate = re.sub(r',\s*\{[^}]*$', '', candidate)
    candidate = re.sub(r',\s*$', '', candidate)
    
    # Balance brackets
    stack = []
    for ch in candidate:
        if ch in "{[":
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()
    while stack:
        candidate += ']' if stack.pop() == '[' else '}'
    
    try:
        result = json.loads(candidate)
        if isinstance(result, dict) and "notes" in result:
            logger.info(f"[Extract] Truncation repair: {len(result.get('notes', []))} notes")
        return result
    except json.JSONDecodeError:
        pass

    # Strategy 4: Markdown code blocks
    for m in re.finditer(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL):
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            continue

    # Strategy 5: Forward scan for valid JSON objects
    candidates = []
    i = 0
    while i < len(text):
        if text[i] == '{':
            depth = 0
            end = -1
            for j in range(i, len(text)):
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                    if depth == 0:
                        end = j
                        break
            if end > i:
                snippet = text[i:end + 1]
                try:
                    obj = json.loads(snippet)
                    if isinstance(obj, dict):
                        candidates.append((obj, len(snippet)))
                except json.JSONDecodeError:
                    cleaned = re.sub(r',\s*([\]}])', r'\1', snippet)
                    try:
                        obj = json.loads(cleaned)
                        if isinstance(obj, dict):
                            candidates.append((obj, len(snippet)))
                    except json.JSONDecodeError:
                        pass
                i = end + 1
                continue
        i += 1

    if candidates:
        # Prefer objects with 'notes' array
        with_notes = [c for c in candidates if 'notes' in c[0] and isinstance(c[0]['notes'], list)]
        if with_notes:
            result = max(with_notes, key=lambda x: len(x[0].get('notes', [])))[0]
            logger.info(f"[Extract] Found notes: {len(result.get('notes', []))}")
            return result

        # Check nested structures
        for obj, size in candidates:
            for key, val in obj.items():
                if isinstance(val, dict) and 'notes' in val:
                    val.setdefault('id', key)
                    return val

        # Prefer titled objects
        titled = [c for c in candidates if 'title' in c[0]]
        if titled:
            return max(titled, key=lambda x: x[1])[0]

        # Pick largest
        return max(candidates, key=lambda x: x[1])[0]

    # Strategy 6: Extract notes array directly
    notes_match = re.search(r'"notes"\s*:\s*\[', text)
    if notes_match:
        arr_start = notes_match.end() - 1
        notes_text = text[arr_start:]
        notes_text = re.sub(r',\s*\{[^}]*$', '', notes_text)
        notes_text = re.sub(r',\s*$', '', notes_text)
        # Balance
        stack = []
        for ch in notes_text:
            if ch == '[': stack.append(ch)
            elif ch == ']':
                if stack: stack.pop()
        while stack:
            notes_text += ']'
            stack.pop()
        try:
            notes = json.loads(notes_text)
            id_m = re.search(r'"id"\s*:\s*"([^"]*)"', text[:arr_start])
            name_m = re.search(r'"name"\s*:\s*"([^"]*)"', text[:arr_start])
            role_m = re.search(r'"role"\s*:\s*"([^"]*)"', text[:arr_start])
            inst_m = re.search(r'"instrument"\s*:\s*"([^"]*)"', text[:arr_start])
            return {
                "id": id_m.group(1) if id_m else "unknown",
                "name": name_m.group(1) if name_m else "unknown",
                "role": role_m.group(1) if role_m else "instrument",
                "instrument": inst_m.group(1) if inst_m else "piano",
                "notes": notes
            }
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON in response ({len(text)} chars)")


# ---------- LLM Client ----------
def _extract_content(data: dict, provider: str) -> str:
    if provider == "openai":
        choices = data.get("choices", [])
        if not choices:
            raise ValueError(f"No choices. Keys: {list(data.keys())}")
        msg = choices[0].get("message", {})
        c = msg.get("content")
        r = msg.get("reasoning_content")
        parts = []
        if c and str(c).strip():
            parts.append(str(c))
        if r and str(r).strip():
            parts.append(str(r))
        if parts:
            return "\n".join(parts)
        raise ValueError(f"Empty response. message keys: {list(msg.keys())}")
    else:
        for b in data.get("content", [{}]):
            if b.get("type") == "text" and b.get("text", "").strip():
                return b["text"]
        raise ValueError("No text in Anthropic response")


async def _call_llm(system_prompt: str, user_prompt: str, use_fast_model: bool = False) -> str:
    cfg = get_config()
    if not cfg.api_key:
        raise ValueError("API Key 未配置，请在左侧设置面板填入 API Key")

    model = cfg.model
    if use_fast_model and cfg.model in REASONING_MODELS:
        model = "mimo-v2.5"
        print(f"[LLM] Using fast model: {model}")

    is_reasoning = model in REASONING_MODELS
    if cfg.provider_format == "openai":
        url = f"{cfg.base_url.rstrip('/')}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json; charset=utf-8"}
        body = {
            "model": model, "max_tokens": 8192, "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        if not is_reasoning:
            body["response_format"] = {"type": "json_object"}
    else:
        url = f"{cfg.base_url.rstrip('/')}/v1/messages"
        headers = {"x-api-key": cfg.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json; charset=utf-8"}
        body = {"model": model, "max_tokens": 8192, "temperature": 0.3, "system": system_prompt, "messages": [{"role": "user", "content": user_prompt}]}

    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(url, headers=headers, content=payload)
        resp.raise_for_status()
        return _extract_content(resp.json(), cfg.provider_format)


# ---------- Prompts ----------
LYRICS_SYSTEM = """你是专业华语作词人。根据用户的创意描述，原创一首完整的华语歌词。

只输出JSON对象，不要输出任何其他文字。JSON字段：
- title: 歌曲标题（自己起名）
- full_lyrics: 完整歌词文本，用\n换行，包含主歌副歌所有段落
- sections: 数组，每项包含type(verse/chorus/bridge)、label(段落名)、lyrics(该段歌词)

要求：原创歌词，有情感，朗朗上口，至少2段主歌和1段副歌，中文为主。full_lyrics必须是实际创作的歌词，不能是占位符。"""

PLAN_SYSTEM = """你是专业编曲师。根据歌词和风格设计编曲方案。BPM、拍号、调性全部由你决定。只输出JSON对象，不要其他文字。
可用乐器：""" + ", ".join(AVAILABLE_INSTRUMENTS) + """
音色选择（voice字段）：""" + ", ".join(VOICE_CATALOG.keys()) + """
{"title":"标题","bpm":100,"time_signature":"4/4","key":"C major","total_beats":240,"tracks":[{"id":"vocal_1","name":"主唱","role":"vocal","instrument":"piano","voice":"冰糖","channel":0,"part":"melody","volume":0.9},{"id":"inst_1","name":"吉他","role":"instrument","instrument":"guitar","voice":"","channel":1,"part":"accompaniment","volume":0.7},{"id":"inst_2","name":"鼓组","role":"instrument","instrument":"drums","voice":"","channel":2,"part":"rhythm","volume":0.6}]}

规则：
- total_beats是歌曲总拍数，所有音轨的乐器部分必须覆盖这个长度（允许中间留白）。
- 歌曲时长不低于120秒（2分钟）。计算公式：total_beats = BPM × 120 / 60 = BPM × 2。例如BPM=100则total_beats至少200，BPM=120则至少240。
- 如果有人声轨道，歌词只占歌曲的一部分（约40%-70%），其余时间由intro、间奏、outro的纯伴奏填充。不要因为歌词短就缩短歌曲。
- 如果是纯器乐，歌曲至少120秒。
- vocal的voice必须是上面音色之一。instrument的voice=""。
- 可以不包含人声轨道。"""


SINGLE_TRACK_NOTES_SYSTEM = """你是MIDI编曲师。只输出JSON，不要其他文字。

输出格式：
{"id":"xxx","name":"xxx","role":"xxx","instrument":"xxx","notes":[{"pitch":"C4","start":0.0,"duration":1.0,"velocity":80}],"note_count":N}

规则：
1. 音高：C4,D#4,A3等。start/duration单位是拍数(float)。velocity 1-127
2. 你将收到一个total_beats参数，这是歌曲总拍数。所有音符的最后一个start+duration必须接近total_beats，不得短于total_beats*0.85。中间可以有留白（静音段）
3. 至少30个音符
4. 鼓：C2=底鼓 D2=军鼓 F#2=踩镲 A#2=镲片 C#2=拍手
5. 人声：每个note加lyrics字段（一个字），track级lyrics=完整歌词
6. 乐器：要有音乐性变化，不同段落不同pattern，verse轻柔、chorus丰富、bridge变化
7. 人声轨道：歌词不要从第0拍开始，前面留8-16拍的intro纯伴奏；最后留4-8拍的outro纯伴奏。人声=歌词段，intro/outro=无人声
7. 用长音符填满留白段落（如pad音色的whole note），确保时间线覆盖完整

只输出JSON对象，以{开头以}结尾。"""


async def generate_lyrics(prompt: str) -> dict:
    text = await _call_llm(LYRICS_SYSTEM, f"请为以下创意创作歌词：\n{prompt}")
    return _extract_json(text)


async def generate_track_plan(lyrics, user_tracks, style="", references=None, bpm=None, time_signature=None, key=None, vocal_duration=None):
    style_info = ""
    if style and style.lower() in STYLE_KNOWLEDGE:
        sk = STYLE_KNOWLEDGE[style.lower()]
        style_info = f"\n风格({style})：BPM {sk['bpm']}，{sk['key']}，{sk['chords']}，{sk['inst']}"
    td = ""
    if user_tracks:
        td = "\n用户音轨（可增删）：\n"
        for t in user_tracks:
            r = t.get("role", "instrument")
            td += f"- {t.get('name','?')}: role={r}"
            td += f", voice={t.get('voice','冰糖')}" if r == "vocal" else f", instrument={t.get('instrument','piano')}"
            td += f", part={t.get('part','melody')}\n"
    vocal_info = ""
    if vocal_duration:
        vocal_info = f"\n人声轨道已生成，时长{vocal_duration:.1f}秒。total_beats必须精确匹配人声时长，计算公式：total_beats = round(BPM * {vocal_duration:.1f} / 60)。所有乐器轨道必须覆盖到这个total_beats，人声之外的时间由intro/间奏/outro的纯伴奏填充。"
    
    text = await _call_llm(PLAN_SYSTEM, f"歌词：\n{lyrics}\n{style_info}{td}{vocal_info}\n输出编曲JSON。")
    result = _extract_json(text)
    if "tracks" in result:
        result["tracks"] = [_normalize_track_metadata(t) for t in result["tracks"]]
    # Ensure total_beats exists — compute from BPM if LLM omitted it
    if "total_beats" not in result:
        bpm = result.get("bpm", 120)
        if vocal_duration:
            result["total_beats"] = max(int(bpm * vocal_duration / 60), result.get("total_beats", int(bpm * vocal_duration / 60)))
        else:
            result["total_beats"] = max(int(bpm * 2), result.get("total_beats", int(bpm * 2)))  # 2 min floor
    return result


async def _generate_single_track_notes(lyrics, track_info, style, bpm, time_signature, key, total_beats=None):
    """Generate notes for a single track using dedicated LLM call."""
    track_id = track_info.get("id", "unknown")
    track_name = track_info.get("name", track_id)
    role = track_info.get("role", "instrument")
    instrument = track_info.get("instrument", "piano")

    # total_beats comes from plan via parameter; floor = 2 minutes
    if total_beats is None:
        total_beats = int(bpm * 2)
    total_beats = max(int(bpm * 2), total_beats)
    min_notes = max(30, total_beats // 6)

    # For vocal tracks, pass full lyrics
    lyrics_section = ""
    if role == "vocal":
        lyrics_section = f"\n完整歌词（必须逐字分配到每个音符的lyrics字段）：\n{lyrics}"

    # Compute intro/outro for vocal tracks
    if role == "vocal":
        intro_beats = max(8, int(total_beats * 0.08))   # ~8% of song or 8 beats min
        outro_beats = max(4, int(total_beats * 0.05))   # ~5% of song or 4 beats min
        vocal_req = f"""为歌词的每个字生成一个音符：
- 人声从第{intro_beats}拍开始（前{intro_beats}拍是纯伴奏intro）
- 最后歌词音符不超过total_beats-{outro_beats}拍（后{outro_beats}拍是纯伴奏outro）
- 最后音符的start+duration即为歌曲实际长度，乐器轨道会参考这个长度"""
    else:
        vocal_req = "所有音符必须覆盖到total_beats附近，最后一个音符的start+duration >= total_beats*0.85。中间可以有留白（静音段），留白段落可以用长音符填充（如whole note的pad）。"

    prompt = f"""为以下音轨生成MIDI音符：

音轨ID: {track_id}
名称: {track_name}
角色: {role}
乐器: {instrument}
BPM: {bpm}
拍号: {time_signature}
调性: {key}
total_beats: {total_beats}（歌曲总拍数，约{total_beats * 60 / bpm:.0f}秒）
{lyrics_section}

要求：{vocal_req}
- 音符数量：至少{min_notes}个
- {'每个音符必须有lyrics字段，包含对应歌词的一个字或词' if role == 'vocal' else '音符要有音乐性变化：intro轻柔、verse稳定、chorus丰富、bridge变化、outro渐弱'}
- 鼓轨道：C2=底鼓, D2=军鼓, F#2=踩镲, A#2=镲片

直接输出JSON，以{{开头。"""

    try:
        logger.info(f"[Notes] Generating track {track_id} ({track_name}, {role})")
        text = await _call_llm(SINGLE_TRACK_NOTES_SYSTEM, prompt, use_fast_model=True)
        logger.info(f"[Notes] Track {track_id} response: {len(text)} chars")

        result = _extract_json(text)

        # Handle single note object
        if "pitch" in result and "start" in result:
            result = {"id": track_id, "name": track_name, "role": role, "instrument": instrument, "notes": [result]}

        # Handle notes as dict instead of list
        if "notes" in result and isinstance(result["notes"], dict):
            result["notes"] = [result["notes"]]

        if "notes" not in result:
            result["notes"] = []

        # Ensure correct metadata
        result.setdefault("id", track_id)
        result.setdefault("name", track_name)
        result.setdefault("role", role)
        result.setdefault("instrument", instrument)

        # Fix drum notes missing pitch
        if instrument == "drums" or "drum" in track_name.lower():
            for note in result["notes"]:
                if "pitch" not in note:
                    vel = note.get("velocity", 80)
                    if vel > 90:
                        note["pitch"] = "C2"
                    elif vel > 70:
                        note["pitch"] = "D2"
                    else:
                        note["pitch"] = "F#2"

        note_count = len(result["notes"])
        result["note_count"] = note_count

        # For vocal tracks, ensure lyrics field
        if role == "vocal":
            if not result.get("lyrics"):
                result["lyrics"] = "".join(n.get("lyrics", "") for n in result["notes"]) or lyrics

        # ── Post-process: ensure track covers total_beats ──
        notes = result.get("notes", [])
        if notes:
            max_time = max(n.get("start", 0) + n.get("duration", 0) for n in notes)
            min_coverage = total_beats * 0.85
            if max_time < min_coverage and role != "vocal":
                # Pad with sustained notes to fill the gap
                logger.info(f"[Notes] Track {track_id}: coverage {max_time:.0f}/{total_beats:.0f} beats, padding...")
                # Use a repeating pattern from existing notes
                if len(notes) >= 4:
                    pattern = notes[-min(8, len(notes)):]
                    pat_max = max(n.get("start", 0) + n.get("duration", 0) for n in pattern)
                    if pat_max > 0:
                        cursor = max_time
                        while cursor < total_beats:
                            for n in pattern:
                                new_note = dict(n)
                                new_note["start"] = cursor + (n.get("start", 0) % pat_max)
                                if new_note["start"] + new_note.get("duration", 1) > total_beats:
                                    break
                                notes.append(new_note)
                            cursor += pat_max
                            if cursor >= total_beats:
                                break
                elif instrument in ("synth_pad", "bass"):
                    # For pad/bass, add long sustained notes
                    scale = ["C3", "E3", "G3", "A3"] if instrument == "synth_pad" else ["C2", "G2", "A2", "F2"]
                    cursor = max_time
                    idx = 0
                    while cursor < total_beats:
                        dur = min(8.0, total_beats - cursor)
                        notes.append({"pitch": scale[idx % len(scale)], "start": cursor, "duration": dur, "velocity": 60})
                        cursor += dur
                        idx += 1
                result["notes"] = notes
                result["note_count"] = len(notes)
                logger.info(f"[Notes] Track {track_id} after padding: {len(notes)} notes")

            # Vocal tracks: no padding needed — TTS determines actual audio length

        logger.info(f"[Notes] Track {track_id} final: {result.get('note_count', 0)} notes")
        return track_id, result

    except Exception as e:
        logger.error(f"[Notes] Track {track_id} failed: {e}")
        logger.error(traceback.format_exc())
        return track_id, {"id": track_id, "name": track_name, "role": role, "instrument": instrument, "notes": [], "note_count": 0}


async def generate_track_notes(lyrics, plan, style=""):
    """Generate notes for all tracks in parallel (max 4 concurrent)."""
    plan_tracks = plan.get("tracks", [])
    bpm = plan.get("bpm", 120)
    time_signature = plan.get("time_signature", "4/4")
    key = plan.get("key", "C major")

    print(f"[Notes] Generating notes for {len(plan_tracks)} tracks (parallel, max 4)")

    # Rate limit: mimo-v2.5-tts has 100 RPM, we use mimo-v2.5 for notes so similar limits
    semaphore = asyncio.Semaphore(4)

    async def generate_with_limit(track_info):
        async with semaphore:
            return await _generate_single_track_notes(lyrics, track_info, style, bpm, time_signature, key, total_beats)

    total_beats = plan.get("total_beats", int(bpm * 2))  # use plan value directly
    tasks = [generate_with_limit(t) for t in plan_tracks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Build arrangement
    arrangement = {
        "title": plan.get("title", ""),
        "bpm": bpm,
        "time_signature": time_signature,
        "key": key,
        "total_beats": total_beats,
        "tracks": []
    }

    for result in results:
        if isinstance(result, Exception):
            print(f"[Notes] Track generation failed: {result}")
            continue
        track_id, track_data = result

        # Map metadata from plan
        for plan_track in plan_tracks:
            if plan_track.get('id') == track_id:
                if not track_data.get('name') or track_data.get('name') == track_id:
                    track_data['name'] = plan_track.get('name', track_id)
                if not track_data.get('role') or track_data.get('role') == 'instrument':
                    track_data['role'] = plan_track.get('role', 'instrument')
                if plan_track.get('instrument'):
                    track_data['instrument'] = plan_track['instrument']
                if plan_track.get('voice'):
                    track_data['voice'] = plan_track['voice']
                break

        track_data = _normalize_track_metadata(track_data)
        if "notes" not in track_data:
            track_data["notes"] = []
        track_data["note_count"] = len(track_data["notes"])
        if track_data.get("role") == "vocal" and not track_data.get("lyrics"):
            track_data["lyrics"] = "".join(n.get("lyrics", "") for n in track_data["notes"]) or lyrics
        arrangement["tracks"].append(track_data)

    print(f"[Notes] Generated {len(arrangement['tracks'])} tracks total")
    for t in arrangement['tracks']:
        print(f"  - {t.get('id')}: {t.get('name')} ({t.get('role')}) notes={t.get('note_count')}")

    return arrangement


# ---------- TTS ----------
async def synthesize_voice(text: str, voice: str = "mimo_default", style: str = "") -> bytes:
    """Synthesize speech or singing via MiMo TTS.

    For singing mode: uses (唱歌) tag per MiMo documentation.
    Text limit: 1024 chars per request.
    """
    cfg = get_config()
    if not cfg.api_key:
        raise ValueError("API Key 未配置")

    actual_voice, default_style = _resolve_voice(voice)
    tts_style = style if style else default_style

    speak_text = text.strip()[:1024]
    if not speak_text:
        speak_text = "啦啦啦"

    # Determine if singing mode
    is_singing = any(kw in tts_style for kw in ["唱歌", "唱", "sing", "演唱"])

    if is_singing:
        assistant_content = f"(唱歌){speak_text}"
        user_content = tts_style
    else:
        assistant_content = speak_text
        user_content = tts_style

    body = {
        "model": cfg.tts_model,
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ],
        "audio": {"format": "wav", "voice": actual_voice}
    }

    url = f"{cfg.base_url.rstrip('/')}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json; charset=utf-8"}
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, content=payload)
        resp.raise_for_status()
        return _extract_audio(resp.json())


async def synthesize_voice_segments(lyrics: str, voice: str = "mimo_default", style: str = "") -> List[bytes]:
    """Split long lyrics into segments and synthesize each one."""
    if not lyrics.strip():
        return []

    segments = []
    text = lyrics.strip()
    while text:
        if len(text) <= TTS_MAX_CHARS:
            segments.append(text)
            break
        best = TTS_MAX_CHARS
        for sep in ["。", "！", "？", "；", "\n", "，", ".", "!", "?", "、"]:
            p = text.rfind(sep, 0, TTS_MAX_CHARS)
            if p > TTS_MAX_CHARS // 4:
                best = p + 1
                break
        segments.append(text[:best])
        text = text[best:].lstrip()

    results = []
    for seg in segments:
        if not seg.strip():
            continue
        try:
            audio = await synthesize_voice(seg, voice, style)
            results.append(audio)
            logger.info(f"[TTS] Segment ok: {len(seg)} chars -> {len(audio)} bytes")
        except Exception as e:
            logger.error(f"[TTS] Segment failed: {e}")
    return results


async def clone_voice(audio_bytes: bytes, text: str, filename: str = "sample.wav") -> bytes:
    """Voice cloning from uploaded audio reference."""
    cfg = get_config()
    if not cfg.api_key:
        raise ValueError("API Key 未配置")
    ref_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    speak_text = text.strip()[:1024] or "啦啦啦"

    body = {
        "model": cfg.tts_model,
        "messages": [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": speak_text}
        ],
        "audio": {"format": "wav", "voice": f"data:audio/mpeg;base64,{ref_b64}"}
    }
    url = f"{cfg.base_url.rstrip('/')}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json; charset=utf-8"}
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(url, headers=headers, content=payload)
        resp.raise_for_status()
        return _extract_audio(resp.json())


def _extract_audio(data: dict) -> bytes:
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    ad = message.get("audio", {})
    if ad and "data" in ad:
        return base64.b64decode(ad["data"])
    content = message.get("content")
    if content:
        try:
            return base64.b64decode(content)
        except Exception:
            pass
    raise ValueError(f"No audio in response. Keys: {list(message.keys())}")


