
import asyncio
import cv2
import websockets
import time
import traceback
import os

from hume import HumeStreamClient, HumeClientException
from hume.models.config import FaceConfig
from collections import deque



# Configurations
HUME_FACE_FPS = 1 / 3  # 3 FPS

# Webcam setup
cam = cv2.VideoCapture(0)
TEMP_FILE = 'temp.jpg'
TEMP_WAV_FILE = 'temp.wav'

# Global variables
recording = False
recording_data = []
stop_loop = False  # New global variable


#This function takes the Hume API result and extracts tiredness scores.
def process_tiredness_scores(result):
    tiredness_scores = []
    for face in result.get('face', {}).get('predictions', []):
        for emotion in face.get('emotions', []):
            if emotion['name'] == 'Tiredness':
                tiredness_scores.append((face['face_id'], emotion['score']))
    return tiredness_scores


# Add a new function to play alert sound
def play_alert_sound():
    # Replace with your actual path
    sound_file = '/Users/tauhid/Driving/DriverAttention.mp3'
    if os.path.exists(sound_file):
        os.system(f'afplay {sound_file}')
    else:
        print(f"Alert sound file not found: {sound_file}")



async def webcam_loop():
    global stop_loop
    score_threshold = 0.55  # The score threshold for fatigue
    time_span = 8  # Time span in seconds to check for two occurrences
    recent_high_scores = deque()  # Stores timestamps of recent high scores

    while not stop_loop:
        try:
            client = HumeStreamClient("zlNqvdiibDrb0x9Ex7IN09YG3VSrtpeZRnxRlVrCgnzf0j01")
            config = FaceConfig(identify_faces=True)
            async with client.connect([config]) as socket:
                print("(Connected to Hume API!)")
                while True:
                    if not recording:
                        _, frame = cam.read()
                        cv2.imwrite(TEMP_FILE, frame)
                        result = await socket.send_file(TEMP_FILE)
                        tiredness_scores = process_tiredness_scores(result)
                        print("Tiredness Scores:", tiredness_scores)

                        current_time = time.time()
                        # Check each face's tiredness score
                        for face_id, score in tiredness_scores:
                            if score > score_threshold:
                                recent_high_scores.append(current_time)
                                # Remove timestamps outside the time span window
                                while recent_high_scores and current_time - recent_high_scores[0] > time_span:
                                    recent_high_scores.popleft()

                                # Check if condition is met to send notification and sound
                                if len(recent_high_scores) >= 2:
                                    print("Driver is fatigued!")
                                    play_alert_sound()  # Play alert sound
                                    recent_high_scores.clear()  # Clear the timestamps

                        await asyncio.sleep(1 / 3)
        except websockets.exceptions.ConnectionClosedError:
            print("Connection lost. Attempting to reconnect in 1 seconds.")
            time.sleep(1)
        except HumeClientException:
            print(traceback.format_exc())
            stop_loop = True  # Stop the loop on a HumeClientException
            break
        except Exception:
            print(traceback.format_exc())



asyncio.run(webcam_loop())

