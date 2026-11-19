from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import base64
import numpy as np
import cv2
from deepface import DeepFace
from collections import deque, Counter

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# Larger buffer for more stable emotion detection
emotion_buffer = deque(maxlen=7)

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/teacher")
def teacher():
    return render_template("teacher.html")

@app.route("/student")
def student():
    return render_template("student.html")


# ================= WEBRTC =================

@socketio.on("offer")
def handle_offer(data):
    emit("offer", data, broadcast=True, include_self=False)

@socketio.on("answer")
def handle_answer(data):
    emit("answer", data, broadcast=True, include_self=False)

@socketio.on("ice-candidate")
def handle_ice(data):
    emit("ice-candidate", data, broadcast=True, include_self=False)


# ================= CHAT =================

@socketio.on("chat_message")
def handle_chat(data):
    # Broadcast message to everyone (teacher + student)
    emit("chat_message", data, broadcast=True)


# ================= EMOTION DETECTION =================

@socketio.on("send_frame")
def detect_emotion(data):
    try:
        if not data:
            return

        image_data = data.split(",")[1]
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return

        # Resize for speed
        frame = cv2.resize(frame, (320, 240))

        result = DeepFace.analyze(
            frame,
            actions=['emotion'],
            enforce_detection=False,
            detector_backend='opencv'   # fastest backend
        )

        dominant = result[0]['dominant_emotion']
        scores   = result[0]['emotion']          # full probability dict

        # ── IMPROVED MAPPING ──────────────────────────────────────────
        # FRUSTRATED  → angry  (primary)  OR  disgust with high score
        # CONFUSED    → fear   OR  disgust (mild)  OR  surprise (low)
        # BORED       → sad   OR  neutral with low "happy" component
        # NEUTRAL     → happy OR  neutral (high happy component)

        angry_score   = scores.get('angry', 0)
        disgust_score = scores.get('disgust', 0)
        fear_score    = scores.get('fear', 0)
        sad_score     = scores.get('sad', 0)
        surprise_score= scores.get('surprise', 0)
        happy_score   = scores.get('happy', 0)
        neutral_score = scores.get('neutral', 0)

        if dominant == 'angry' or (dominant == 'disgust' and angry_score > 15):
            current_emotion = "FRUSTRATED"

        elif dominant in ['fear', 'surprise'] or (
                dominant == 'disgust' and angry_score <= 15) or (
                fear_score > 20 and dominant != 'angry'):
            current_emotion = "CONFUSED"

        elif dominant == 'sad' or (
                dominant == 'neutral' and sad_score > 20 and happy_score < 10):
            current_emotion = "BORED"

        else:   # happy or neutral (engaged)
            current_emotion = "NEUTRAL"
        # ──────────────────────────────────────────────────────────────

        emotion_buffer.append(current_emotion)
        stable_emotion = Counter(emotion_buffer).most_common(1)[0][0]

        emit("emotion_to_teacher", {"emotion": stable_emotion}, broadcast=True)

    except Exception as e:
        print("Emotion Error:", e)


# ================= RUN =================

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)