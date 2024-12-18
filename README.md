# Vertix

**Hackathon Submission:** LLM Agents Hackathon hosted by Berkeley's Center for Responsible, Decentralized Intelligence. 

## Track: Applications Track

Develop innovative LLM-based agents for various domains, including:
- Coding assistants
- Customer service
- Regulatory compliance
- Data science
- AI scientists
- Personal assistants

**Focus Areas:**
1. **Hard-Design Problems:** Novel domain-specific tools.
2. **Soft-Design Problems:** High-fidelity human simulations and improved AI agent interfaces.
## Overview

This project is a "Jarvis-like" AI assistant that leverages Large Language Models (LLMs) to understand user emotions and respond empathetically. It also provides a range of functionalities including weather forecasts, music playback, code generation and explanation, and data visualization insights—all in one integrated system.

## Features

### Emotion-Aware Conversational Assistant
- Uses a Hugging Face emotion detection model to assess the user's emotional state.
- Adjusts responses based on the detected emotion (e.g., more empathetic if user is sad).

### Everyday Tasks
- **Weather**: Ask "What's the weather in [city]?" to get current or forecasted conditions.
- **Music**: Say "Play [song name]" to automatically open and play the top YouTube match.
- **Code Generation**: Command the assistant to "Write a Python program that does X", and it will generate, save, and execute code locally.
- **Documents**:  
  - Create documents ("Create an essay about [topic]").  
  - Edit documents ("Edit [filename] to make it more formal").  
  - Read documents ("Show me what's in [filename]").

### Code Explainer
- Upload a screenshot/image of code.
- The assistant provides a multi-sectioned (carousel-like) explanation of the code's functionality, technical details, best practices, and potential improvements.

### Data Analysis & Visualization
- Upload a CSV/XLSX file.
- The assistant provides:
  - Dataset insights and business implications.
  - Recommended visualizations, potential ML models, and data quality checks.
- Automatically generates Plotly-based visualizations (e.g., correlation heatmaps, bar charts, scatter plots).

## Architecture

- **Backend**: Flask (Python)
- **LLM Integration**:  
  - OpenAI API for GPT-based text responses and code generation  
  - Google Generative AI (Gemini) for code and data insights
- **Emotion Detection**: Hugging Face Transformers
- **Visualization**: Plotly
- **Audio I/O**: `sounddevice` and `soundfile` for voice input; `gTTS` and `playsound` for speech output
- **Data Processing**: Pandas, NumPy, SciPy

## Setup Instructions

### Prerequisites
- Python 3.9+ recommended
- API keys:
  - `OPENAI_API_KEY` for OpenAI
  - `GOOGLE_API_KEY` for Google Gemini
  - `WEATHER_API_KEY` for OpenWeatherMap

### Environment Variables
Set these environment variables in your shell or in a `.env` file:
```bash
export OPENAI_API_KEY="YOUR_OPENAI_KEY"
export GOOGLE_API_KEY="YOUR_GOOGLE_KEY"
export WEATHER_API_KEY="YOUR_WEATHER_KEY"
```
## Installation

### Clone the Repository:
```bash
git clone https://github.com/yourusername/llm-berkeley-hackathon.git
cd llm-berkeley-hackathon
```
### Install Dependencies:  
```bash  
pip install openai google-generativeai transformers gTTS playsound youtube_search requests plotly pandas scipy flask sounddevice soundfile python-docx werkzeug  
```

### Running the App  
```bash  
python app.py
```
After the server starts, open your browser and go to:  
```
http://localhost:5000  
```

### Usage  
##Voice Commands:  
From the web interface, choose an audio device and start the conversation.  
Examples:  
```
"What's the weather in San Francisco tomorrow?"  
"Play 'Imagine Dragons Believer' on YouTube."  
"Write a Python script that prints the Fibonacci sequence."  
"Create an essay about the impact of climate change on agriculture."  
```

## Code Explainer:  
Go to /code_explainer, upload an image of code, and receive a detailed, card-based explanation.  

## Data Visualization:  
Visit /data-assistant, upload a CSV/Excel file, and get an HTML-based analysis plus Plotly visualizations.  

### Things to note:  
- Make sure your microphone is configured if using voice and your voice is crips and clear for a more accurate transcription. 
- The assistant attempts to be context-aware and provide empathetic responses but it is not 100% accurate. 
- Resource requirements may be high due to LLM usage—run on a machine with sufficient resources.
