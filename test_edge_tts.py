
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
print("\nDone! Play these files to compare voices:")
print("  static/gobika_test.wav  - Gobika voice")
print("  static/teacher_test.wav - Teacher voice")
print("  static/warden_test.wav  - Warden voice")
