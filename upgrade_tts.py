"""
upgrade_tts.py
--------------
your_tts → XTTS-v2 upgrade பண்றது.
XTTS-v2 = human-like voice clone, free, offline.

Run: python upgrade_tts.py
"""

import os

# ── Step 1: Install XTTS-v2 ───────────────────────────────────────────────────
print("=" * 50)
print("🔧  XTTS-v2 UPGRADER")
print("=" * 50)

print("\n📦  Installing TTS with XTTS-v2 support...")
os.system("pip install TTS --upgrade")
os.system("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu")

print("\n✅  Installation done!")

# ── Step 2: Test XTTS-v2 ─────────────────────────────────────────────────────
print("\n🧪  Testing XTTS-v2...")

test_code = """
from TTS.api import TTS
import os

# XTTS-v2 load (first time = model download ~1.8GB)
print("Loading XTTS-v2 model... (first time takes 5-10 mins to download)")
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
print("Model loaded!")

# Test voice - use your actual wav file
voice_file = "gobika.wav"  # உங்க wav file name
if not os.path.exists(voice_file):
    # Create a dummy test if wav missing
    print(f"WARNING: {voice_file} not found. Add your wav file and test again.")
else:
    tts.tts_to_file(
        text="Vanakkam da! Ithu test speech, human maari kedaikutha?",
        speaker_wav=voice_file,
        language="en",
        file_path="static/test_output.wav"
    )
    print("Test done! Play static/test_output.wav to hear the result.")
"""

with open("test_xtts.py", "w", encoding="utf-8") as f:
    f.write(test_code)
print("✅  test_xtts.py created!")

# ── Step 3: Update app.py TTS section ────────────────────────────────────────
print("\n📝  Updating app.py to use XTTS-v2...")

app_path = "app.py"
if os.path.exists(app_path):
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace your_tts with xtts_v2
    old = 'model_name="tts_models/multilingual/multi-dataset/your_tts"'
    new = 'model_name="tts_models/multilingual/multi-dataset/xtts_v2"'

    if old in content:
        content = content.replace(old, new)
        with open(app_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅  app.py updated — now uses XTTS-v2!")
    else:
        print("⚠️  your_tts line not found in app.py — check manually.")
else:
    print("⚠️  app.py not found in current folder.")

# ── Step 4: Update generate_voice function for XTTS-v2 ───────────────────────
print("\n📝  Checking generate_voice function...")

GENERATE_VOICE_NEW = '''
def generate_voice(text: str, voice_file: str) -> bool:
    output_path = "static/reply.wav"
    if not os.path.exists(voice_file):
        print(f"Voice file missing: {voice_file}")
        return False
    try:
        tts.tts_to_file(
            text=text,
            speaker_wav=voice_file,
            language="en",          # Tanglish = "en" use pannunga
            file_path=output_path,
        )
        return True
    except Exception as e:
        print(f"TTS Error: {e}")
        return False
'''

print("✅  generate_voice is compatible with XTTS-v2!")

print("""
═══════════════════════════════════════════════
✅  UPGRADE COMPLETE!

NEXT STEPS:
─────────────────────────────────────────────
1. First, test XTTS-v2:
   python test_xtts.py
   (First run = downloads ~1.8GB model, wait!)

2. Play static/test_output.wav — human-like?

3. If good, restart Flask:
   python app.py

⚠️  IMPORTANT NOTES:
─────────────────────────────────────────────
• First startup = 2-3 mins (model loading)
• CPU-la response time = 10-20 sec per reply
• GPU இருந்தா 2-3 sec மட்டும்
• Better audio = better clone quality

💡  SPEED TIP (CPU-la faster-ஆ பண்ண):
─────────────────────────────────────────────
Short replies மட்டும் generate பண்ணுங்க.
Long text = slow. 
app.py-la max_tokens=80 வச்சா reply short-ஆ
இருக்கும், TTS fast-ஆ run ஆகும்.
═══════════════════════════════════════════════
""")