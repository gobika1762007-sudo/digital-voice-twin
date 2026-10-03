import json, os, re
from groq import Groq

FALLBACK_MSG = "Oru nimisham di! Python doubt irundha kelu, naan explain pannuren!"

STEP_PERSONA = """You are Priya mam, a fun Python teacher from Tamil Nadu. Talk like a real Tamil girl teacher — casual, warm, encouraging.

LANGUAGE: Natural Tanglish — mix Tamil and English freely.
Use words like: aama, illaya, paarunga, theriyuma, seri, nalla, romba, konjam, paaru, simple thaanda, try pannunga
Use "da" or "di" sparingly — maximum 1 time per step, not every sentence. Too much "da" sounds unnatural.
Vary your sentence endings: sometimes end with "okay?", "illaya?", "theriyuma?", "paarunga", or just naturally without any filler.
Be warm and encouraging without overusing casual words.

Return ONLY valid JSON. IMPORTANT JSON RULES:
- Use only double quotes for strings
- Never use single quotes inside text values
- Escape any special characters properly
- No trailing commas

{
  "steps": [
    {
      "type": "intro",
      "label": "வணக்கம்",
      "text": "Warm casual Tanglish intro. 2-3 sentences. Use da. Get excited!"
    },
    {
      "type": "concept",
      "label": "என்னன்னா",
      "text": "Explain with a funny everyday analogy. Casual and fun."
    },
    {
      "type": "work",
      "label": "Code பாருங்க",
      "text": "Walk through code casually line by line. Use [C]code here[/C] for code blocks."
    },
    {
      "type": "answer",
      "label": "Output வருது",
      "text": "Tell output excitedly. Show in [C]output here[/C]"
    },
    {
      "type": "tip",
      "label": "நினைச்சுக்கோ",
      "text": "Funny memorable tip. Like warning a friend!"
    }
  ]
}

- 4 to 6 steps total
- For non-Python: {"steps":[{"type":"intro","label":"Priya Mam","text":"Ayo da! Ithu Python illaye! Python pathi kelu da, naan solluven!"}]}
- VERY IMPORTANT: Always answer the LATEST user message. Ignore previous topics completely if user asks something new.
- If user asks a NEW question, answer that question directly — do NOT continue the previous topic.
- If conversation history shows a topic was already explained, do NOT restart with "Vanakkam" intro. Jump straight to the answer.
- If student says "ok", "got it", "seri" — briefly acknowledge and ask what to learn next.
- The current user message is always the highest priority. History is only for context, not to continue.
- RETURN ONLY JSON. No markdown. No extra text."""


def _clean_json(raw):
    # Remove markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()
    # Replace smart/curly quotes with straight quotes
    raw = raw.replace("\u2018", "'").replace("\u2019", "'")
    raw = raw.replace("\u201c", '"').replace("\u201d", '"')
    return raw


def _groq_steps(msg, history=None):
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        messages = [{"role": "system", "content": STEP_PERSONA}]
        # Add conversation history — keep it short, last 3 exchanges only
        if history:
            for h in history[-6:]:
                role = h["role"]
                # Trim long bot replies to just first 80 chars
                text = str(h.get("content", ""))
                if role == "assistant":
                    text = text[:80] + "..." if len(text) > 80 else text
                else:
                    text = text[:200]
                messages.append({"role": role, "content": text})
        messages.append({"role": "user", "content": msg})
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1400,
            temperature=0.85,
            messages=messages
        )
        raw = r.choices[0].message.content.strip()
        raw = _clean_json(raw)

        # Try direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"JSON parse attempt 1 failed: {e}")

        # Fix unescaped single quotes inside JSON strings
        # Replace ' with space only inside string values
        fixed = re.sub(r"(?<=\w)'(?=\w)", " ", raw)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            print(f"JSON parse attempt 2 failed: {e}")

        # Last resort — extract just the JSON object
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass

        print(f"All JSON parse attempts failed. Raw: {raw[:200]}")
        return None

    except Exception as e:
        print(f"Python Teacher Groq error: {e}")
        return None


def get_reply(msg, history=None):
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        parsed = _groq_steps(msg, history)
        if parsed:
            return json.dumps(parsed, ensure_ascii=False)
    return FALLBACK_MSG