from openai import OpenAI
import re
import os
import difflib
import time
import traceback
import subprocess
from typing import Dict, Optional, Union
from datetime import datetime

class CodeHandler:
    def __init__(self, openai_client):
        """
        Initialize CodeHandler with OpenAI client and enhanced functionality.
        
        This class provides comprehensive code generation and editing capabilities with
        automated execution, smart file naming, and robust error handling.
        
        Args:
            openai_client: An instance of the OpenAI client for API interactions
        """
        self.client = openai_client
        self.current_file = None
        self.current_code = None
        self.code_phrases = {
            'generate': [
                'write a python program',
                'create a python program',
                'write a program in python',
                'create a program in python',
                'write python code',
                'generate python code',
                'write a python script',
                'make a python program',
                'code a python program',
                'implement a python program',
                'develop a python program',
                'help me write a python program',
                'can you write a python program',
                'could you create a python program',
                'help me to write a python program',
                'i need a python program',
                'create code for',
                'write code for'
            ],
            'edit': [
                'edit the python code',
                'modify the python code',
                'update the python code',
                'fix the python code',
                'change the python code',
                'refactor the python code',
                'help me edit the python code',
                'can you modify the python code',
                'edit code in',
                'modify code in',
                'update code in',
                'change code in',
                'fix code in'
            ]
        }

    def generate_filename(self, request: str) -> str:
        """
        Generate a clean, descriptive filename based on the program's purpose.
        
        Args:
            request: The programming task description
            
        Returns:
            A user-friendly filename that describes the program's purpose
        """
        common_words = {
            'a', 'the', 'to', 'in', 'on', 'at', 'and', 'or', 'for', 'with',
            'that', 'this', 'program', 'python', 'code', 'script', 'write',
            'create', 'generate', 'make', 'develop', 'implement', 'me', 'please',
            'would', 'could', 'can', 'help'
        }
        
        words = request.lower().split()
        meaningful_words = [word for word in words if word not in common_words]
        
        base_name = '_'.join(meaningful_words[:3])
        base_name = re.sub(r'[^\w\s-]', '', base_name)
        
        counter = 1
        filename = f"{base_name}.py"
        while os.path.exists(filename):
            filename = f"{base_name}_{counter}.py"
            counter += 1
            
        return filename

    def execute_program(self, file_path: str) -> Dict[str, str]:
        """
        Execute a Python program and capture its output.
        
        Args:
            file_path: Path to the Python file to execute
            
        Returns:
            Dictionary containing execution results and output
        """
        try:
            result = subprocess.run(
                ['python', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "output": result.stdout,
                    "message": "Program executed successfully"
                }
            else:
                return {
                    "status": "error",
                    "output": result.stderr,
                    "message": "Program execution failed"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Execution error: {str(e)}"
            }

    def generate_program(self, request: str) -> Dict[str, str]:
        """
        Generate, save, and execute a Python program based on the user's request.
        
        Args:
            request: The programming task description
            
        Returns:
            Dictionary containing status, filename, execution results, and messages
        """
        try:
            system_message = """You are an expert Python programmer. Generate clean, well-documented 
            Python code that solves the user's request. Include:
            1. Clear docstrings explaining the program's purpose
            2. Detailed comments for complex logic
            3. Error handling where appropriate
            4. Input validation when needed
            Return only the code without any explanations outside the code."""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Write a Python program that {request}"}
                ]
            )
            
            code = response.choices[0].message.content
            code = code.replace('```python', '').replace('```', '').strip()
            
            # Add docstring if not present
            if not code.startswith('"""') and not code.startswith("'''"):
                code = f'"""\nPython program to {request}\n"""\n\n' + code
            
            # Generate descriptive filename
            filename = self.generate_filename(request)
            
            # Save the code
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Execute the program
            execution_result = self.execute_program(filename)
            
            return {
                "status": "success",
                "filename": filename,
                "execution": execution_result,
                "message": f"Program has been generated as {filename} and executed automatically"
            }
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Error generating program: {str(e)}\n{error_traceback}")
            return {
                "status": "error",
                "message": f"Error generating program: {str(e)}"
            }

    def edit_code(self, file_path: str, edit_request: str, code_context: Optional[str] = None) -> Dict[str, str]:
        """
        Edit existing code with intelligent modifications and automatic execution.
        
        Args:
            file_path: Path to the file to edit
            edit_request: Description of the requested changes
            code_context: Optional code context if not reading from file
            
        Returns:
            Dictionary containing status, changes made, execution results, and messages
        """
        try:
            if not file_path:
                return {"status": "error", "message": "No file path provided"}
            
            abs_file_path = os.path.abspath(file_path)
            if not os.path.exists(abs_file_path):
                return {"status": "error", "message": f"File not found: {abs_file_path}"}
            
            try:
                with open(abs_file_path, 'r', encoding='utf-8') as f:
                    current_code = f.read()
            except Exception as e:
                return {"status": "error", "message": f"Error reading file: {str(e)}"}
            
            system_message = f"""You are an expert Python programmer making specific code modifications.
            Instructions:
            1. Only modify the parts of the code that need to change based on the request
            2. Keep all other code exactly as is
            3. Add comments above changed sections explaining modifications
            4. Return ONLY the modified code without any markdown or additional text
            
            Current code:
            {current_code}"""
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Make these specific changes: {edit_request}"}
                ]
            )
            
            modified_code = response.choices[0].message.content
            modified_code = modified_code.replace('```python', '').replace('```', '').strip()
            backup_path = f"{abs_file_path}.backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(current_code)
            with open(abs_file_path, 'w', encoding='utf-8') as f:
                f.write(modified_code)
            execution_result = self.execute_program(abs_file_path)
            diff = self.generate_compact_diff(current_code, modified_code)
            
            return {
                "status": "success",
                "changes": diff,
                "execution": execution_result,
                "message": f"Code has been updated in {file_path} and executed automatically",
                "backup_path": backup_path
            }
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Error editing code: {str(e)}\n{error_traceback}")
            return {
                "status": "error",
                "message": f"Error editing code: {str(e)}"
            }

    def generate_compact_diff(self, original: str, modified: str) -> str:
        """
        Generate a clear, readable diff showing only the changed lines.
        
        Args:
            original: Original code content
            modified: Modified code content
            
        Returns:
            String containing only the meaningful changes
        """
        diff_lines = []
        for line in difflib.unified_diff(
            original.splitlines(),
            modified.splitlines(),
            fromfile='original',
            tofile='modified',
            lineterm=''
        ):
            if line.startswith('+') or line.startswith('-'):
                diff_lines.append(line)
        
        return '\n'.join(diff_lines) if diff_lines else "No changes were necessary"
    def parse_code_request(self, text: str) -> Optional[Dict[str, str]]:
        """
        Parse user requests with improved natural language understanding.
        
        This method has been enhanced to better understand various ways users might
        phrase their code-related requests, including more colloquial expressions
        and context-aware interpretation.
        
        Args:
            text: The user's input text
            
        Returns:
            Dictionary containing request type and details, or None if not a code request
        """
        text_lower = text.lower()
        for phrase in self.code_phrases['generate']:
            if phrase in text_lower:
                task = text_lower
                
                for remove_phrase in self.code_phrases['generate']:
                    task = task.replace(remove_phrase, '')
                task = task.strip(' .,?!')
                
                task_parts = []
                for part in task.split(' and '):
                    task_parts.append(part.strip())
                
                final_task = ' and '.join(task_parts)
                
                return {
                    "type": "generate",
                    "request": final_task,
                    "original_text": text  
                }
        
        for phrase in self.code_phrases['edit']:
            if phrase in text_lower:
                file_patterns = [
                    r'in file (\S+\.py)',
                    r'in (\S+\.py)',
                    r'(\S+\.py) file',
                    r'edit (\S+\.py)',
                    r'modify (\S+\.py)',
                    r'update (\S+\.py)',
                    r'fix (\S+\.py)',
                    r'in file (\S+)(?!\.py)',
                    r'edit (\S+)(?!\.py)',
                    r'modify (\S+)(?!\.py)'
                ]
                
                file_path = None
                for pattern in file_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        file_path = match.group(1)
                        if not file_path.endswith('.py'):
                            file_path += '.py'
                        break
                
                edit_instruction = text_lower
                if file_path:
                    edit_instruction = edit_instruction.replace(file_path, '').strip()
                    for phrase in self.code_phrases['edit']:
                        edit_instruction = edit_instruction.replace(phrase, '').strip()
                
                return {
                    "type": "edit",
                    "request": edit_instruction,
                    "file_path": file_path,
                    "original_text": text
                }
        
        if ('python' in text_lower and 
            ('program' in text_lower or 'code' in text_lower or 'script' in text_lower)):
            request = text_lower
            for word in ['python', 'program', 'code', 'script']:
                request = request.replace(word, '')
            request = request.strip()
            
            return {
                "type": "generate",
                "request": request,
                "original_text": text
            }
        
        return None
    