import os
from docx import Document
from docx.shared import Pt
import time
from openai import OpenAI

class DocumentHandler:
    def __init__(self, openai_client):
        self.base_path = os.getcwd()
        self.docs_folder = os.path.join(self.base_path, "generated_documents")
        self.client = openai_client
        try:
            os.makedirs(self.docs_folder, exist_ok=True)
            print(f"Documents will be saved in: {self.docs_folder}")
        except Exception as e:
            print(f"Error creating directory: {str(e)}")
    
    def generate_content(self, prompt):
        """Generate content using GPT-4 with specific requirements"""
        try:
            formatted_prompt = f"""Write a detailed essay with the following requirements:
            Topic: {prompt}
            Length: 1500 words
            Style: Academic
            Structure: Introduction, Main Body (with clear sections), and Conclusion
            
            Please write this as a formal academic essay with proper citations and structure."""

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """You are an expert academic writer. Create well-researched, 
                    structured essays with clear arguments and supporting evidence. Use formal academic language 
                    and proper citations. Focus on providing comprehensive analysis and insights."""},
                    {"role": "user", "content": formatted_prompt}
                ],
                max_tokens=2500,  
                temperature=0.7    
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Content generation error: {str(e)}")
            return f"Error generating content: {str(e)}"

    def create_text_file(self, text, filename=None, generate_content=False):
        """Create a simple text file with the given content"""
        try:
            # Ensure directory exists
            os.makedirs(self.docs_folder, exist_ok=True)
            
            if generate_content:
                text = self.generate_content(text)
                
            if filename is None:
                filename = f"document_{int(time.time())}.txt"
            
            filepath = os.path.abspath(os.path.join(self.docs_folder, filename))
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            
            print(f"Created text file at: {filepath}")
            return f"I've created a text file '{filename}' with your content in the {self.docs_folder} folder."
        except Exception as e:
            print(f"Text file creation error: {str(e)}")
            return f"Error creating text file: {str(e)}"
    
    def create_word_document(self, text, filename=None, generate_content=False):
        """Create a Word document with the given content"""
        try:
            os.makedirs(self.docs_folder, exist_ok=True)
            
            if generate_content:
                text = self.generate_content(text)
            
            if filename is None:
                filename = f"document_{int(time.time())}.docx"
            
            filepath = os.path.abspath(os.path.join(self.docs_folder, filename))
            
            doc = Document()
            doc.add_paragraph(text)
            doc.save(filepath)
            
            print(f"Created Word document at: {filepath}")
            return f"I've created a Word document '{filename}' with your content in the {self.docs_folder} folder."
        except Exception as e:
            print(f"Word document creation error: {str(e)}")
            return f"Error creating Word document: {str(e)}"
    
    def parse_document_command(self, text):
        """Parse the command to determine document type and content"""
        text_lower = text.lower()
        
        generate_content = any(word in text_lower for word in [
            'write me', 'generate', 'create an essay', 'write an essay',
            'write a report', 'write a letter', 'need an essay',
            'economic essay', 'research paper', 'analysis'
        ])
        
        doc_type = 'word' if ('essay' in text_lower or generate_content) else 'text'
        
        filename = None
        if 'name it' in text_lower or 'call it' in text_lower or 'save it as' in text_lower:
            parts = text.split()
            for i, word in enumerate(parts):
                if word.lower() in ['it', 'as'] and i + 1 < len(parts):
                    filename = parts[i + 1].strip('" ')
                    if not filename.endswith('.txt') and not filename.endswith('.docx'):
                        filename += '.txt' if doc_type == 'text' else '.docx'
                    text = text.replace(f"name it {filename}", "").replace(f"call it {filename}", "").replace(f"save it as {filename}", "")
                    break
        
        content = text
        remove_phrases = [
            'type', 'write', 'create', 'make', 'generate', 
            'a document', 'a file', 'containing', 'with', 
            'that says', 'an essay', 'about', 'on the topic of'
        ]
        
        for phrase in remove_phrases:
            content = content.replace(phrase, '')
        content = content.strip()
        
        return doc_type, filename, content, generate_content