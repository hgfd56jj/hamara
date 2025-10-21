import os
import tempfile
import logging
import requests
from flask import Flask, request, jsonify
from pydub import AudioSegment
import speech_recognition as sr

# ------------------ Logging ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)

app = Flask(__name__)

# ------------------ Telegram Config ------------------
# שים כאן את פרטי הבוט שלך
TELEGRAM_BOT_TOKEN = "8183670381:AAEkIUh-P7pU6HbMmHY_eqjSU2_6Qfnqnic"
TELEGRAM_CHAT_ID = "7820835795"

# ------------------ Helper Functions ------------------

def add_silence(input_path: str) -> AudioSegment:
    audio = AudioSegment.from_file(input_path, format="wav")
    silence = AudioSegment.silent(duration=1000)
    return silence + audio + silence

def recognize_speech(audio_segment: AudioSegment) -> str:
    recognizer = sr.Recognizer()
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_wav:
            audio_segment.export(temp_wav.name, format="wav")
            with sr.AudioFile(temp_wav.name) as source:
                data = recognizer.record(source)
            text = recognizer.recognize_google(data, language="he-IL")
            logging.info(f"Recognized text: {text}")
            return text
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        logging.error(f"Speech recognition error: {e}")
        return ""

def send_to_telegram(text: str, file_url: str):
    message = f"🎙️ הודעה חדשה מהמערכת:\n\n{text}\n\n🔗 קובץ ההקלטה:\n{file_url}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

# ------------------ API Endpoint ------------------

@app.route("/upload_audio", methods=["GET"])
def upload_audio():
    file_url = request.args.get("file_url")
    if not file_url:
        return jsonify({"error": "Missing 'file_url' parameter"}), 400

    logging.info(f"Downloading audio from: {file_url}")
    try:
        response = requests.get(file_url, timeout=15)
        if response.status_code != 200:
            return jsonify({"error": "Failed to download audio file"}), 400

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_input:
            temp_input.write(response.content)
            temp_input.flush()

            processed_audio = add_silence(temp_input.name)
            recognized_text = recognize_speech(processed_audio)

            if recognized_text:
                send_to_telegram(recognized_text, file_url)
                return jsonify({"recognized_text": recognized_text})
            else:
                send_to_telegram("❌ לא זוהה דיבור.", file_url)
                return jsonify({"recognized_text": ""})

    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# ------------------ Run ------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
