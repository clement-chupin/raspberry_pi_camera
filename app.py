from flask import Flask, render_template, Response, send_from_directory, request, redirect, url_for
from picamera2 import Picamera2

from libcamera import Transform
import threading
import time
import os
from datetime import datetime
import cv2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
import RPi.GPIO as GPIO
import numpy as np

# -----------------------------
# PARAMÈTRES CAMÉRA
# -----------------------------
preview_size = (640, 480)
preview_fps = 10

record_size = (1920, 1080)
record_bitrate = 10000000  # 10 Mbps
record_framerate = 18  # valeur par défaut

led_blink_speed = 0.2
# -----------------------------
# PARAMÈTRES GPIO
# -----------------------------
BUTTON_PIN = 17  # Bouton (broche physique 11)
LED_PIN = 18     # LED    (broche physique 12)

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, GPIO.LOW)

# -----------------------------
# APP & CAMERA
# -----------------------------
app = Flask(__name__)
picam2 = Picamera2()

recording = False
rec_thread = None
led_thread = None
output_filename = ""
video_start_time = 0

VIDEO_DIR = "/home/pi/Desktop/videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

lock = threading.Lock()
vintage_mode = False  # mode vintage ON/OFF

# -----------------------------
# FONCTIONS CAMÉRA
# -----------------------------
def init_camera_preview():
    """Configure preview permanent (flux lores)"""
    global picam2
    picam2.stop()
    config = picam2.create_preview_configuration(
        main={"size": record_size, "format": "RGB888"},
        # lores={"size": preview_size},
        transform=Transform(hflip=1, vflip=1),  # rotation 180°
        controls={"FrameRate": preview_fps}
    )
    picam2.configure(config)
    picam2.start()

def record_video():
    """Enregistrement de la vidéo"""
    global recording, output_filename, video_start_time, record_framerate, picam2

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(VIDEO_DIR, f"rec_{ts}.h264")

    encoder = H264Encoder(
        framerate=record_framerate, 
        enable_sps_framerate=True, 
        bitrate=record_bitrate)
    
    encoder.framerate = record_framerate
    video_config = picam2.create_video_configuration(
        main={"size": record_size}, #, "FrameRate" : record_framerate
        transform=Transform(hflip=1, vflip=1),
        controls={"FrameRate": record_framerate}
    )

    picam2.switch_mode(video_config)

    video_start_time = time.time()
    picam2.start_recording(encoder, output_filename)
    print(f"Recording started: {output_filename} ({record_framerate} fps)")

    while recording:
        time.sleep(0.1)

    picam2.stop_recording()
    duration = int(time.time() - video_start_time)
    new_name = output_filename.replace(".h264", f"_{duration}s_fps{record_framerate}.h264")
    os.rename(output_filename, new_name)
    print(f"Recording stopped and saved: {new_name}")

    init_camera_preview()



def led_blink():
    """Fait clignoter la LED pendant l'enregistrement"""
    while recording:
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(led_blink_speed)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(led_blink_speed)
    GPIO.output(LED_PIN, GPIO.LOW)

def button_listener():
    """Surveillance du bouton"""
    global recording, rec_thread, led_thread
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            time.sleep(0.1)
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                with lock:
                    if not recording:
                        recording = True
                        rec_thread = threading.Thread(target=record_video)
                        led_thread = threading.Thread(target=led_blink)
                        rec_thread.start()
                        led_thread.start()
                        print("Recording triggered by button")
                    else:
                        recording = False
                        print("Recording stopped by button")
                while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    time.sleep(0.1)
        time.sleep(0.1)

# -----------------------------
# FILTRE VINTAGE
# -----------------------------

def apply_vintage(frame):
    # Matrice sépia (3x3)
    sepia_filter = np.array([[0.272, 0.534, 0.131],
                             [0.349, 0.686, 0.168],
                             [0.393, 0.769, 0.189]])
    sepia = cv2.transform(frame, sepia_filter)

    # Limiter à [0,255]
    sepia = np.clip(sepia, 0, 255).astype(np.uint8)

    # Ajout d’un peu de bruit
    noise = np.random.normal(0, 10, frame.shape).astype(np.uint8)
    vintage = cv2.addWeighted(sepia, 0.9, noise, 0.1, 0)

    return vintage


# -----------------------------
# FLUX FLASK
# -----------------------------
init_camera_preview()

@app.route('/')
def index():
    files = sorted([f for f in os.listdir(VIDEO_DIR) ], reverse=True) #if f.endswith(".h264")
    return render_template('index.html', files=files, fps=record_framerate, vintage=vintage_mode)

def gen_frames():
    while True:
        frame = picam2.capture_array() #"lores"
        if vintage_mode:
            frame = apply_vintage(frame)
        ret, jpeg = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/download/<path:filename>')
def download(filename):
    return send_from_directory(VIDEO_DIR, filename, as_attachment=True)

@app.route('/set_fps/<int:fps>')
def set_fps(fps):
    global record_framerate
    if fps in [18, 24]:
        record_framerate = fps
        print(f"FPS set to {fps}")
    return redirect(url_for('index'))

@app.route('/toggle_vintage')
def toggle_vintage():
    global vintage_mode
    vintage_mode = not vintage_mode
    return redirect(url_for('index'))

# -----------------------------
# MAIN
# -----------------------------
if __name__ == '__main__':
    try:
        button_thread = threading.Thread(target=button_listener, daemon=True)
        button_thread.start()
        app.run(host='0.0.0.0', port=8000)
    except KeyboardInterrupt:
        GPIO.cleanup()
    finally:
        GPIO.cleanup()
