#app.py
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
from gtts import gTTS
from playsound import playsound
import webbrowser
from music_service import YouTubeHelper
from doc_writer import DocumentHandler
from code_service import CodeHandler
from code_explainer import CodeVisionService
import os
from data_science_helper import DataAnalysisService
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)
client = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')  
weather_service = WeatherService()
youtube_helper = YouTubeHelper()
document_handler = DocumentHandler(client) 
code_handler=CodeHandler(client)
code_vision_service = CodeVisionService(GOOGLE_API_KEY)
data_analysis_service = DataAnalysisService(GOOGLE_API_KEY)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 5
CHUNK_DURATION = 0.1  
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
            while True:
                time.sleep(0.1) 
                
                current_time = time.time()
                if (current_time - audio_recorder.last_voice_activity > SILENCE_DURATION and 
                    audio_recorder.recording_active):
                    audio_recorder.recording_active = False
                    print("Silence detected - stopping recording")
                    break
        
        if not audio_recorder.audio_buffer:
            raise ValueError("No audio data recorded")
        
        audio_data = np.concatenate(audio_recorder.audio_buffer, axis=0)
        temp_filename = f"temp_{int(time.time())}.wav"
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
DOCUMENT_KEYWORDS = {
    'create': ['type', 'write', 'create', 'make', 'generate', 'compose'],
    'edit': ['edit', 'modify', 'change', 'update', 'revise'],
    'read': ['read', 'show', 'display', 'open', 'view']
}

def handle_document_command(text):
    """
    Handle document-related commands with improved parsing and response generation.
    This function centralizes all document operations for better maintenance and reliability.
    """
    text_lower = text.lower()
    
    command_type = None
    
    if any(keyword in text_lower for keyword in DOCUMENT_KEYWORDS['create']):
        doc_type, filename, content, generate_content = document_handler.parse_document_command(text)
        if doc_type == 'word':
            return document_handler.create_word_document(content, filename, generate_content)
        else:
            return document_handler.create_text_file(content, filename, generate_content)
    
    elif any(keyword in text_lower for keyword in DOCUMENT_KEYWORDS['edit']):
        filepath, edit_instructions = document_handler.parse_edit_command(text)
        if filepath and edit_instructions:
            result = document_handler.edit_document(filepath, edit_instructions)
            if "successfully edited" in result:
                return f"I've updated the document '{filepath}' with your requested changes. The edits have been saved."
            return result
    
    elif any(keyword in text_lower for keyword in DOCUMENT_KEYWORDS['read']):
        words = text.split()
        for word in words:
            if word.endswith('.txt') or word.endswith('.docx'):
                content = document_handler.read_document(word)
                if content:
                    return f"Here's the content of {word}:\n\n{content}"
                else:
                    return f"I couldn't find or read the file named {word}. Please make sure it exists and try again."
        return "Please specify which file you'd like me to read."
    
    return None


def get_chatgpt_response(text, emotion):
    """
    Enhanced get_chatgpt_response function with improved document handling integration.
    Now includes better context awareness and more natural responses.
    """
    print("🤖 Getting AI response...")
    
    text_lower = text.lower()
    code_request = code_handler.parse_code_request(text)
    if code_request:
        if code_request["type"] == "generate":
            result = code_handler.generate_program(code_request["request"])
            if result["status"] == "success":
                return f"I've created your program and saved it as {result['filename']}"
            else:
                return f"Sorry, there was an error: {result['message']}"
        elif code_request["type"] == "edit":
            if code_request["file_path"]:
                result = code_handler.edit_code(code_request["file_path"], code_request["request"])
                if result["status"] == "success":
                    return f"I've updated the code in {code_request['file_path']}"
                else:
                    return f"Sorry, there was an error: {result['message']}"
            else:
                return "Please specify which file you'd like me to edit."
    
    if (('play' in text_lower or 'find' in text_lower or 'search' in text_lower) and 
        ('song' in text_lower or 'music' in text_lower or 'youtube' in text_lower)):
        query = text_lower
        for word in ['play', 'find', 'search', 'for', 'song', 'music', 'youtube', 'on', 'please', 'can', 'you']:
            query = query.replace(word, '')
        query = query.strip()
        
        if query:
            return youtube_helper.search_and_play(query)
        else:
            return "What song would you like me to search for?"

    doc_response = handle_document_command(text)
    if doc_response:
        return doc_response

    if any(word in text_lower for word in ['weather', 'temperature', 'forecast']):
        city, forecast_days = weather_service.parse_weather_query(text)
        if city:
            weather_data = weather_service.get_weather(city, forecast_days)
            return weather_service.format_weather_response(weather_data, city, forecast_days)

    system_message = f"""You are a helpful assistant responding to a user. Based on their detected emotional state of {emotion}, adjust your response style appropriately:

    joy: match their positive energy while staying focused
    sadness: be supportive and solution-oriented
    anger: remain composed and address concerns directly
    fear: provide clear, reassuring responses
    surprise: offer relevant context and explanation
    disgust: maintain objectivity and professionalism
    neutral: engage in balanced conversation

    Never explicitly mention or comment on the user's emotional state
    
    You can help users with various tasks:
    1. Play music:
       - "Play [song name]"
       - "Search for [song name]"
       - "Find [song name] on YouTube"
    
    2. Work with documents:
       - Create: "Write a document about [topic]", "Create an essay on [subject]"
       - Edit: "Edit [filename] to make it more formal", "Update [filename] with new information"
       - Read: "Show me what's in [filename]", "Read [filename] to me"
    
    Always be helpful and professional while being mindful of their emotional state."""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content


def text_to_speech(text):
    """Convert text to speech and play it"""
    try:
        audio_file = f"response_{int(time.time())}.mp3"
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(audio_file)
        playsound(audio_file)
        os.remove(audio_file)
    except Exception as e:
        print(f"Error in text to speech: {str(e)}")


def conversation_loop(device_id):
    """Main conversation loop with improved document handling"""
    while True:
        try:
            audio_file = record_audio(device_id=device_id)
            
            transcription = transcribe_audio(audio_file)
            print(f"User said: {transcription}")
            
            dominant_emotion, emotion_scores = emotion_detector.detect_emotion(transcription)
            print(f"Detected emotion: {dominant_emotion}")
            response = get_chatgpt_response(transcription, dominant_emotion)
            print(f"AI responds: {response}")

            if len(response) > 300 and any(keyword in transcription.lower() for keyword in ['write', 'create', 'generate', 'edit']):
                speech_text = "I've processed your document request. " + response.split('\n')[0]
                text_to_speech(speech_text)
            else:
                text_to_speech(response)
            
            conversation_history.append({
                "user": transcription,
                "emotion": dominant_emotion,
                "emotion_scores": emotion_scores,
                "ai": response,
                "timestamp": time.strftime("%H:%M:%S")
            })
            
            os.remove(audio_file)
            
        except Exception as e:
            error_msg = f"Error in conversation loop: {str(e)}"
            print(error_msg)
            text_to_speech("I encountered an error processing your request. Please try again.")
            time.sleep(1)

    

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

@app.route('/code_explainer')
def code_explainer():
    """Render the code explainer page"""
    return render_template('code_asker.html')


@app.route('/analyze_code', methods=['POST'])
def analyze_code():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
        
    file = request.files['file']
    
    try:
        result = code_vision_service.process_image(file)
        
        if result['status'] == 'success':
            formatted_sections = code_vision_service.format_code_analysis(result['explanation'])
            return jsonify({
                'status': 'success',
                'sections': formatted_sections
            })
        else:
            return jsonify({
                'status': 'error',
                'error': result.get('error', 'Analysis failed')
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })
    
@app.route('/data-assistant')
def data_assistant():
    return render_template('data_science_helper.html')

@app.route('/analyze_data', methods=['POST'])
def analyze_data():
    print("Received analyze_data request")  # Debug 
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'error': 'No file uploaded'})
    
    file = request.files['file']
    if not file or not data_analysis_service.allowed_file(file.filename):
        return jsonify({'status': 'error', 'error': 'Invalid file type. Please upload a CSV or Excel file.'})
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        print(f"Saving file to: {filepath}")  # Debug 
        file.save(filepath)
        

        print("Analyzing data...")  # Debug 
        result = data_analysis_service.analyze_data(filepath)
        
        # Clean up
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in analyze_data: {str(e)}")  # Debug 
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({
            'status': 'error',
            'error': f'Error processing file: {str(e)}'
        })

@app.route('/generate_visualization', methods=['POST'])
def generate_visualization():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['data', 'type', 'params']):
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameters'
            })
        df = pd.DataFrame(data['data'])
        result = data_analysis_service.generate_custom_visualization(
            df, data['type'], data['params']
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in generate_visualization: {str(e)}")  # Debug 
        return jsonify({
            'status': 'error',
            'error': f'Error generating visualization: {str(e)}'
        })


if __name__ == '__main__':
    print("🚀 Starting voice chat server with emotion detection...")
    print("Available audio input devices:")
    for device in list_audio_devices():
        print(f"ID: {device['id']}, Name: {device['name']}")
    app.run(debug=True, port=5000)