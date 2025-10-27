import speech_recognition as sr

# File WAV đã chuyển từ MP3
wav_file = "heymirror.wav"

# Khởi tạo recognizer
recognizer = sr.Recognizer()

with sr.AudioFile(wav_file) as source:
    audio_data = recognizer.record(source)
    try:
        # Nhận diện bằng Google Web Speech API
        text = recognizer.recognize_google(audio_data)
        print(f"[SERVER] Recognized text: {text}")
        if "hey mirror" in text.lower():
            print("[SERVER] Command recognized: Hey Mirror!")
        else:
            print("[SERVER] No trigger recognized.")
    except sr.UnknownValueError:
        print("[SERVER] Could not understand audio.")
    except sr.RequestError as e:
        print(f"[SERVER] Recognition error: {e}")
