from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import time
import os
from weather_service import WeatherService
from transformers import pipeline

app = Flask(__name__)
client = OpenAI(api_key='API-Key')
weather_service = WeatherService()

emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=True
)

class EmotionDetector:
    def __init__(self):
        self.emotions_history = []
        
    def detect_emotion(self, text):
        try:
            emotions = emotion_classifier(text)[0]
            emotions.sort(key=lambda x: x['score'], reverse=True)
            dominant_emotion = emotions[0]['label']
            
            self.emotions_history.append({
                'text': text,
                'dominant_emotion': dominant_emotion,
                'all_emotions': emotions,
                'timestamp': time.strftime("%H:%M:%S")
            })
            
            return dominant_emotion, emotions
        except Exception as e:
            print(f"Error detecting emotion: {str(e)}")
            return "neutral", []
    
    def get_emotion_history(self):
        return self.emotions_history

emotion_detector = EmotionDetector()

audio_queue = queue.Queue()
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
conversation_history = []

# Voice activity detection parameters
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 5
CHUNK_DURATION = 0.1  # Process audio in 100ms chunks
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

class AudioRecorder:
    def __init__(self):
        self.recording_active = False
        self.last_voice_activity = 0
        self.audio_buffer = []
        
    def reset(self):
        self.recording_active = False
        self.last_voice_activity = 0
        self.audio_buffer = []

audio_recorder = AudioRecorder()

def list_audio_devices():
    """List all available audio input devices"""
    devices = sd.query_devices()
    input_devices = []
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            input_devices.append({
                'id': i,
                'name': device['name'],
                'channels': device['max_input_channels']
            })
    return input_devices

def detect_voice_activity(audio_data):
    """Detect if there is voice activity in the audio data"""
    chunks = np.array_split(audio_data, max(1, len(audio_data) // CHUNK_SIZE))
    rms_values = [np.sqrt(np.mean(chunk**2)) for chunk in chunks]
    return max(rms_values) > SILENCE_THRESHOLD

def audio_callback(indata, frames, time_info, status):
    """Callback for audio stream"""
    """Callback function for audio stream"""
    if status:
        print('Audio callback status:', status)
    
    if indata.shape[1] > 1:
        indata = np.mean(indata, axis=1, keepdims=True)

    if detect_voice_activity(indata):
        audio_recorder.last_voice_activity = time.time()
        if not audio_recorder.recording_active:
            audio_recorder.recording_active = True
            print("Voice detected - recording started")
    
    if audio_recorder.recording_active:
        audio_recorder.audio_buffer.append(indata.copy())

def record_audio(device_id=None):
    """Record audio with improved quality and silence detection"""
    print(f"🎤 Recording using device {device_id}...")
    audio_recorder.reset()
    
    if device_id is None:
        devices = list_audio_devices()
        if devices:
            device_id = devices[0]['id']
        else:
            raise ValueError("No input devices found")
    
    try:
        with sd.InputStream(
            device=device_id,
            channels=1,
            samplerate=SAMPLE_RATE,
            callback=audio_callback,
            blocksize=CHUNK_SIZE
        ):
            audio_recorder.recording_active = True
            audio_recorder.last_voice_activity = time.time()
            
            # Keep recording until sufficient silence is detected
            while True:
                time.sleep(0.1)  # Reduce CPU usage
                
                current_time = time.time()
                if (current_time - audio_recorder.last_voice_activity > SILENCE_DURATION and 
                    audio_recorder.recording_active):
                    audio_recorder.recording_active = False
                    print("Silence detected - stopping recording")
                    break
        
        if not audio_recorder.audio_buffer:
            raise ValueError("No audio data recorded")
        
        audio_data = np.concatenate(audio_data, axis=0)
        temp_filename = f"temp_{int(time.time())}.wav"
        
        # Save to temporary WAV file
        sf.write(temp_filename, audio_data, SAMPLE_RATE)
        
        return temp_filename
    
    except Exception as e:
        print(f"Error recording audio: {str(e)}")
        raise

def transcribe_audio(file_path):
    """Transcribe audio file using OpenAI Whisper"""
    print("📝 Transcribing audio...")
    try:
        with open(file_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        raise

def get_chatgpt_response(text, emotion):
    """Get response from ChatGPT with emotion awareness"""
    print("🤖 Getting AI response...")
    
    # Check if it's a weather-related query
    if any(word in text.lower() for word in ['weather', 'temperature', 'forecast']):
        city, forecast_days = weather_service.parse_weather_query(text)
        if city:
            weather_data = weather_service.get_weather(city, forecast_days)
            return weather_service.format_weather_response(weather_data, city, forecast_days)
    
    # Include emotion context in the system message
    system_message = f"""You are a helpful assistant that is aware the user's current emotional state appears to be {emotion}. 
    If the emotion is:
    - joy: maintain an upbeat and encouraging tone
    - sadness: be empathetic and supportive
    - anger: remain calm and understanding
    - fear: be reassuring and clear
    - surprise: acknowledge their reaction and provide clear context
    - disgust: be professional and objective
    - neutral: maintain a balanced, friendly tone
    
    Always ensure your response is helpful and professional while being mindful of their emotional state."""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

def conversation_loop(device_id):
    """Main conversation loop"""
    while True:
        try:
            # Record audio
            audio_file = record_audio(device_id=device_id)
            
            # Transcribe audio to text
            transcription = transcribe_audio(audio_file)
            print(f"User said: {transcription}")
            
            # Detect emotion
            dominant_emotion, emotion_scores = emotion_detector.detect_emotion(transcription)
            print(f"Detected emotion: {dominant_emotion}")
            
            # Get emotion-aware response
            response = get_chatgpt_response(transcription, dominant_emotion)
            print(f"AI responds: {response}")
            
            # Store in conversation history
            conversation_history.append({
                "user": transcription,
                "emotion": dominant_emotion,
                "emotion_scores": emotion_scores,
                "ai": response,
                "timestamp": time.strftime("%H:%M:%S")
            })
            
            # Cleanup temporary audio file
            os.remove(audio_file)
            
        except Exception as e:
            print(f"Error in conversation loop: {str(e)}")
            time.sleep(1)

# Flask routes
@app.route('/')
def home():
    devices = list_audio_devices()
    return render_template('index.html', devices=devices)

@app.route('/devices')
def get_devices():
    return jsonify(list_audio_devices())

@app.route('/start', methods=['POST'])
def start_conversation():
    device_id = request.json.get('deviceId')
    if device_id is not None:
        device_id = int(device_id)
    
    thread = threading.Thread(target=conversation_loop, args=(device_id,))
    thread.daemon = True
    thread.start()
    return jsonify({"status": "Conversation started", "deviceId": device_id})

@app.route('/get_messages')
def get_messages():
    return jsonify(conversation_history)

@app.route('/emotion_history')
def get_emotion_history():
    return jsonify(emotion_detector.get_emotion_history())

if __name__ == '__main__':
    print("🚀 Starting voice chat server with emotion detection...")
    print("Available audio input devices:")
    for device in list_audio_devices():
        print(f"ID: {device['id']}, Name: {device['name']}")
    app.run(debug=True, port=5000)