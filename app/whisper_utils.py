# whisper_utils.py

from faster_whisper import WhisperModel
import tempfile
import os

# Load Whisper model once
model = WhisperModel("base", device="cpu", compute_type="int8")  # You can also use "small" if needed

def transcribe_audio(file_path):
    try:
        segments, _ = model.transcribe(file_path)
        transcript = " ".join([segment.text.strip() for segment in segments])
        return transcript.strip()
    except Exception as e:
        print(f"Transcription error: {e}")
        return ""

