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
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Initialize the Gemini Vision model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Configure service settings
        self.allowed_extensions = {'png', 'jpg', 'jpeg'}
        self.upload_folder = 'uploads'
        
        # Create uploads directory if it doesn't exist
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

    def _format_explanation(self, explanation: str) -> str:
        """Format the explanation for better readability and structure."""
        sections = explanation.split('\n\n')
        formatted_sections = []
        
        section_icons = {
            'quick summary': '🎯',
            'main features': '💡',
            'technical details': '🔧',
            'pro tips': '⚡',
            'important notes': '⚠️'
        }
        
        for section in sections:
            section = section.strip()
            lower_section = section.lower()
            
            for marker, icon in section_icons.items():
                if marker in lower_section:
                    if not section.startswith(icon):
                        section = f"{icon} {section}"
                    section = f"<div class='section {marker.replace(' ', '-')}'>{section}</div>"
                    break
            
            formatted_sections.append(section)
        
        return '\n\n'.join(formatted_sections)
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
            # Save the uploaded file
            filename = os.path.join(self.upload_folder, file.filename)
            file.save(filename)
            
            # Analyze the image
            result = self.analyze_code_image(filename)
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "explanation": None,
                "error": f"Error processing image: {str(e)}"
            }
            
        finally:
            # Clean up the temporary file
            try:
                if 'filename' in locals() and os.path.exists(filename):
                    os.remove(filename)
            except Exception:
                pass