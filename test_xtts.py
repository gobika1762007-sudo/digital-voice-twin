
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
