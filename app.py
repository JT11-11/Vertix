from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import time
import os

app = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Global variables
audio_queue = queue.Queue()
SAMPLE_RATE = 16000
conversation_history = []

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

def audio_callback(indata, frames, time, status):
    if status:
        print('Audio callback status:', status)
    audio_queue.put(indata.copy())

def record_audio(duration=5, device_id=None):
    print(f"🎤 Recording using device {device_id}...")
    audio_data = []
    
    if device_id is None:
        devices = list_audio_devices()
        if devices:
            device_id = devices[0]['id']
        else:
            raise ValueError("No input devices found")
    
    try:
        stream = sd.InputStream(
            device=device_id,
            callback=audio_callback,
            channels=1,
            samplerate=SAMPLE_RATE
        )
        
        with stream:
            sd.sleep(int(duration * 1000))
            while not audio_queue.empty():
                audio_data.append(audio_queue.get())
        
        if not audio_data:
            raise ValueError("No audio data recorded")
        
        audio_data = np.concatenate(audio_data, axis=0)
        temp_filename = f"temp_{int(time.time())}.wav"
        sf.write(temp_filename, audio_data, SAMPLE_RATE)
        
        return temp_filename
    
    except Exception as e:
        print(f"Error recording audio: {str(e)}")
        raise

def transcribe_audio(file_path):
    print("📝 Transcribing audio...")
    with open(file_path, 'rb') as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcript.text

def get_chatgpt_response(text):
    print("🤖 Getting AI response...")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

def conversation_loop(device_id):
    while True:
        try:
            audio_file = record_audio(device_id=device_id)
            transcription = transcribe_audio(audio_file)
            print(f"User said: {transcription}")
            
            response = get_chatgpt_response(transcription)
            print(f"AI responds: {response}")
            
            conversation_history.append({
                "user": transcription,
                "ai": response,
                "timestamp": time.strftime("%H:%M:%S")
            })
            
            os.remove(audio_file)
            
        except Exception as e:
            print(f"Error in conversation loop: {str(e)}")
            time.sleep(1)  # Prevent rapid error loops

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

if __name__ == '__main__':
    print("🚀 Starting voice chat server...")
    print("Available audio input devices:")
    for device in list_audio_devices():
        print(f"ID: {device['id']}, Name: {device['name']}")
    app.run(debug=True, port=5000)