"""
setup_edge_tts.py
-----------------
your_tts → edge-tts upgrade பண்றது.
edge-tts = Microsoft's neural TTS, free, human-like, fast!

Run: python setup_edge_tts.py
"""

import os
import sys

print("=" * 50)
print("🎙️  EDGE-TTS UPGRADER")
print("   Free + Human-like + No GPU needed!")
print("=" * 50)

# Install
print("\n📦  Installing edge-tts...")
os.system("pip install edge-tts")
print("✅  Done!")

# ── Update app.py ─────────────────────────────────────────────────────────────
print("\n📝  Updating app.py...")

app_path = "app.py"
if not os.path.exists(app_path):
    print("❌  app.py not found!")
    sys.exit(1)

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# Remove TTS import and engine
old_tts_import = "from TTS.api import TTS"
new_tts_import = "import edge_tts\nimport asyncio"

old_tts_engine = """# ── TTS engine ───────────────────────────────────────────────────────────────
tts = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False,
)"""

old_tts_engine2 = """# ── TTS engine ───────────────────────────────────────────────────────────────
tts = TTS(
    model_name="tts_models/multilingual/multi-dataset/your_tts",
    gpu=False,
)"""

new_tts_engine = """# ── Edge TTS voices per twin ─────────────────────────────────────────────────
# Each twin gets a different human-like voice
TWIN_VOICES = {
    "gobika":  "en-IN-NeerjaNeural",      # Indian female - friendly
    "teacher": "en-IN-NeerjaExpressiveNeural",  # Indian female - expressive
    "warden":  "en-IN-PrabhatNeural",     # Indian male - authoritative
    "shop":    "en-IN-NeerjaNeural",      # Indian female - warm
    "coach":   "en-IN-PrabhatNeural",     # Indian male - energetic
}
DEFAULT_VOICE = "en-IN-NeerjaNeural"
"""

new_generate_voice = '''def generate_voice(text: str, voice_file: str) -> bool:
    """
    edge-tts use பண்றது — voice_file பதிலா twin name-ஐ பார்க்கறோம்.
    voice_file = "gobika.wav" → twin = "gobika" → TWIN_VOICES["gobika"]
    """
    output_path = "static/reply.wav"
    try:
        # twin name extract பண்றோம் (e.g. "gobika.wav" → "gobika")
        twin_name  = os.path.splitext(os.path.basename(voice_file))[0]
        voice      = TWIN_VOICES.get(twin_name, DEFAULT_VOICE)

        async def _speak():
            communicate = edge_tts.Communicate(text=text, voice=voice)
            await communicate.save(output_path)

        asyncio.run(_speak())
        return True
    except Exception as e:
        print(f"❌  Edge TTS error: {e}")
        return False
'''

old_generate_voice = '''def generate_voice(text: str, voice_file: str) -> bool:
    output_path = "static/reply.wav"
    if not os.path.exists(voice_file):
        print(f"❌  Voice file missing: {voice_file}")
        return False
    try:
        tts.tts_to_file(
            text=text,
            speaker_wav=voice_file,
            language="en",
            file_path=output_path,
            length_scaler=1.25,
        )
        return True
    except Exception as e:
        print(f"❌  TTS error: {e}")
        return False'''

# Apply replacements
changed = False

if old_tts_import in content:
    content = content.replace(old_tts_import, new_tts_import)
    changed = True
    print("  ✅  TTS import replaced with edge_tts")

if old_tts_engine in content:
    content = content.replace(old_tts_engine, new_tts_engine)
    changed = True
    print("  ✅  TTS engine replaced with TWIN_VOICES")
elif old_tts_engine2 in content:
    content = content.replace(old_tts_engine2, new_tts_engine)
    changed = True
    print("  ✅  TTS engine (your_tts) replaced with TWIN_VOICES")

if old_generate_voice in content:
    content = content.replace(old_generate_voice, new_generate_voice)
    changed = True
    print("  ✅  generate_voice() updated for edge-tts")

if changed:
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅  app.py updated successfully!")
else:
    print("\n⚠️  Could not auto-update app.py.")
    print("   Manual-ஆ replace பண்ணணும் — கீழே instructions பாருங்க.")

# ── Write manual instructions ─────────────────────────────────────────────────
manual = """
MANUAL UPDATE INSTRUCTIONS (auto-update fail ஆனா இதை follow பண்ணுங்க)
========================================================================

1. app.py-ல இந்த line-ஐ REMOVE பண்ணுங்க:
   from TTS.api import TTS

2. அதுக்கு பதிலா ADD பண்ணுங்க:
   import edge_tts
   import asyncio

3. இந்த block-ஐ REMOVE பண்ணுங்க:
   tts = TTS(
       model_name="tts_models/...",
       gpu=False,
   )

4. அதுக்கு பதிலா ADD பண்ணுங்க:
   TWIN_VOICES = {
       "gobika":  "en-IN-NeerjaNeural",
       "teacher": "en-IN-NeerjaExpressiveNeural",
       "warden":  "en-IN-PrabhatNeural",
       "shop":    "en-IN-NeerjaNeural",
       "coach":   "en-IN-PrabhatNeural",
   }
   DEFAULT_VOICE = "en-IN-NeerjaNeural"

5. generate_voice() function-ஐ இப்படி மாத்துங்க:

   def generate_voice(text: str, voice_file: str) -> bool:
       output_path = "static/reply.wav"
       try:
           twin_name = os.path.splitext(os.path.basename(voice_file))[0]
           voice = TWIN_VOICES.get(twin_name, DEFAULT_VOICE)
           async def _speak():
               communicate = edge_tts.Communicate(text=text, voice=voice)
               await communicate.save(output_path)
           asyncio.run(_speak())
           return True
       except Exception as e:
           print(f"TTS error: {e}")
           return False
"""

with open("edge_tts_manual.txt", "w", encoding="utf-8") as f:
    f.write(manual)
print("\n📄  Manual instructions saved to: edge_tts_manual.txt")

# ── Test edge-tts ─────────────────────────────────────────────────────────────
print("\n🧪  Testing edge-tts now...")

test_script = """
import edge_tts
import asyncio
import os

os.makedirs("static", exist_ok=True)

async def test():
    voices_to_test = [
        ("en-IN-NeerjaNeural",           "gobika_test.wav",  "Ayyo, ithu romba easy da! Nee worry pannaathe, naan irukken!"),
        ("en-IN-NeerjaExpressiveNeural", "teacher_test.wav", "Seri da, Pythagoras theorem-la a squared plus b squared equals c squared!"),
        ("en-IN-PrabhatNeural",          "warden_test.wav",  "Gate 10 mani-ku close aagum. Late-ah vantha entry kedayaathu!"),
    ]
    for voice, filename, text in voices_to_test:
        print(f"Testing {voice}...")
        c = edge_tts.Communicate(text=text, voice=voice)
        await c.save(f"static/{filename}")
        print(f"  Saved: static/{filename}")

asyncio.run(test())
print("\\nDone! Play these files to compare voices:")
print("  static/gobika_test.wav  - Gobika voice")
print("  static/teacher_test.wav - Teacher voice")
print("  static/warden_test.wav  - Warden voice")
"""

with open("test_edge_tts.py", "w", encoding="utf-8") as f:
    f.write(test_script)
print("  ✅  test_edge_tts.py created!")

print("""
═══════════════════════════════════════════════
✅  SETUP COMPLETE!

NEXT STEPS:
───────────────────────────────────────────────
1. Test voices first:
   python test_edge_tts.py
   
   (static/ folder-la 3 .wav files varum)
   Play பண்ணி கேளுங்க — human-like-ஆ இருக்கா?

2. Happy-ஆ இருந்தா restart:
   python app.py

VOICE OPTIONS (வேற voices try பண்ண):
───────────────────────────────────────────────
Female Indian: en-IN-NeerjaNeural
Female Expressive: en-IN-NeerjaExpressiveNeural  
Male Indian: en-IN-PrabhatNeural

இந்த voices internet connection வேணும்
(edge-tts = Microsoft cloud TTS)
═══════════════════════════════════════════════
""")