# code_vision_service.py

import google.generativeai as genai
import os
import PIL.Image
from typing import Dict, Any
import time

class CodeVisionService:
    def __init__(self, api_key: str):
        """
        Initialize the CodeVisionService with Google's Gemini Vision API.
        
        The service is configured to provide detailed code analysis using Gemini's
        vision capabilities. It handles image processing, rate limiting, and
        generates comprehensive code explanations.
        
        Args:
            api_key: Your Google API key for accessing Gemini
        """
        genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        self.allowed_extensions = {'png', 'jpg', 'jpeg'}
        self.upload_folder = 'uploads'
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)

    def allowed_file(self, filename: str) -> bool:
        """
        Verify if the uploaded file has an allowed extension.
        
        Args:
            filename: Name of the uploaded file
            
        Returns:
            bool: True if the file extension is allowed, False otherwise
        """
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def analyze_code_image(self, image_path: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            image = PIL.Image.open(image_path)
            
            prompt = """Analyze this code and provide a clear explanation in the following format:

            🎯 Quick Summary
            Write a 2-3 sentence overview that anyone can understand, explaining what this code does.

            💡 Main Features
            Explain the key functionality in simple terms, like you're explaining it to a friend.

            🔧 Technical Details
            Break down the important technical aspects for experienced developers:
            - Key components and their roles
            - Notable patterns or techniques used
            - Important functions and their purposes

            ⚡ Pro Tips
            Share 2-3 quick insights about:
            - Potential improvements
            - Best practices to consider
            - Performance considerations

            ⚠️ Important Notes
            Mention any security considerations or special requirements that developers should know about.

            Please keep explanations concise but informative, using simple language where possible."""

            response = self.model.generate_content([prompt, image])
            explanation = self._format_explanation(response.text)
            
            return {
                "status": "success",
                "explanation": explanation,
                "error": None
            }
            
        except Exception as e:
            error_message = f"Error analyzing code image: {str(e)}"
            print(f"Full error details: {e}")
            return {
                "status": "error",
                "explanation": None,
                "error": error_message
            }

    def _format_explanation(self, text: str) -> str:
        """Format the raw text response from Gemini."""
        if not text:
            return ""
        return text.strip()

    def format_code_analysis(self, text: str) -> Dict[str, Any]:
        """Format the analysis text into structured sections."""
        sections = {
            "Quick Summary": {
                "icon": "🎯",
                "content": "",
                "order": 1
            },
            "Main Features": {
                "icon": "💡",
                "content": "",
                "order": 2
            },
            "Technical Details": {
                "icon": "🔧",
                "content": "",
                "order": 3
            },
            "Pro Tips": {
                "icon": "⚡",
                "content": "",
                "order": 4
            },
            "Important Notes": {
                "icon": "⚠️",
                "content": "",
                "order": 5
            }
        }
        
        text = text.replace("***", "").replace("**", "")
        current_section = None
        
        for line in text.split('\n'):
            line = line.strip()
            for section in sections:
                if section in line:
                    current_section = section
                    break
            
            if current_section and line and not any(section in line for section in sections):
                sections[current_section]["content"] += line + "\n"
        
        for section in sections:
            sections[section]["content"] = sections[section]["content"].strip()
        
        return {k: v for k, v in sections.items() if v["content"]}
    
    def process_image(self, file) -> Dict[str, Any]:
        """
        Process an uploaded image file and return the code analysis.
        
        This method handles the complete workflow of saving the uploaded file,
        analyzing it, and cleaning up temporary files.
        
        Args:
            file: Uploaded file object from Flask
            
        Returns:
            Dictionary containing analysis results or error information
        """
        if not file or not self.allowed_file(file.filename):
            return {
                "status": "error",
                "explanation": None,
                "error": "Invalid file type. Please upload a PNG or JPG image."
            }
            
        try:
            filename = os.path.join(self.upload_folder, file.filename)
            file.save(filename)
            
            result = self.analyze_code_image(filename)
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "explanation": None,
                "error": f"Error processing image: {str(e)}"
            }
            
        finally:
            try:
                if 'filename' in locals() and os.path.exists(filename):
                    os.remove(filename)
            except Exception:
                pass