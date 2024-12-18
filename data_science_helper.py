# data_analysis_service.py
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
import json
import google.generativeai as genai
from scipy.stats import chi2_contingency

class DataAnalysisService:
    def __init__(self, api_key: str):
        """Initialize the data analysis service with Gemini API"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.allowed_extensions = {'csv', 'xlsx', 'xls'}

    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def _generate_visualizations(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate visualizations based on data types"""
        visualizations = []
        
        try:
            # For numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) >= 2:
                # Correlation heatmap
                corr_matrix = df[numeric_cols].corr()
                fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale='RdBu'
                ))
                fig.update_layout(title='Correlation Matrix')
                visualizations.append({
                    "type": "heatmap",
                    "title": "Correlation Matrix",
                    "plot": json.loads(fig.to_json())
                })
                fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1])
                visualizations.append({
                    "type": "scatter",
                    "title": f"{numeric_cols[0]} vs {numeric_cols[1]}",
                    "plot": json.loads(fig.to_json())
                })
                
                for col in numeric_cols[:3]:
                    fig = px.box(df, y=col)
                    visualizations.append({
                        "type": "box",
                        "title": f"Distribution of {col}",
                        "plot": json.loads(fig.to_json())
                    })

            cat_cols = df.select_dtypes(include=['object']).columns
            if len(cat_cols) > 0:
                for col in cat_cols[:3]:  
                    value_counts = df[col].value_counts().head(10)  
                    fig = px.bar(
                        x=value_counts.index, 
                        y=value_counts.values,
                        title=f"Top Categories in {col}"
                    )
                    visualizations.append({
                        "type": "bar",
                        "title": f"Distribution of {col}",
                        "plot": json.loads(fig.to_json())
                    })

                    # Pie chart for proportion
                    fig = px.pie(
                        values=value_counts.values,
                        names=value_counts.index,
                        title=f"Proportion of Categories in {col}"
                    )
                    visualizations.append({
                        "type": "pie",
                        "title": f"Proportion of {col}",
                        "plot": json.loads(fig.to_json())
                    })

        except Exception as e:
            print(f"Error generating visualizations: {str(e)}")
            
        return visualizations

    def analyze_data(self, file_path: str) -> Dict[str, Any]:
        """Analyze uploaded data file using Gemini"""
        try:
            # Read data
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            stats = self._get_basic_stats(df)
            prompt = self._generate_analysis_prompt(df, stats)
            response = self.model.generate_content(prompt)
            analysis = self._format_analysis(response.text)
            visualizations = self._generate_visualizations(df)

            return {
                "status": "success",
                "analysis": analysis,
                "visualizations": visualizations,
                "statistics": stats,
                "sample_data": df.head().to_dict(),
                "columns": list(df.columns)
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def _generate_analysis_prompt(self, df: pd.DataFrame, stats: Dict) -> str:
        """Generate analysis prompt for Gemini"""
        return f"""Analyze this dataset and provide insights in the following format:

        📊 Dataset Overview
        - Number of records: {len(df)}
        - Number of features: {len(df.columns)}
        - Features: {', '.join(df.columns)}

        Please provide:
        1. Key insights about the data
        2. Potential business implications
        3. Recommended visualizations
        4. Possible ML models that could be applied
        5. Data quality issues if any

        Data Sample:
        {df.head().to_string()}

        Basic Statistics:
        {stats}

        Format the response in clear HTML with proper headings and paragraphs. 
        Use bullet points where appropriate. Keep the analysis business-focused."""

    def _format_analysis(self, text: str) -> str:
        """Format the analysis text with proper HTML styling"""
        text = text.replace('**', '')
        text = text.replace('##', '')
        
        text = text.replace('📊 Dataset Overview', 
                          '<h3 class="text-xl font-bold text-gray-800 mb-4">📊 Dataset Overview</h3>')
        text = text.replace('Key insights', 
                          '<h3 class="text-xl font-bold text-gray-800 mt-6 mb-4">💡 Key Insights</h3>')
        text = text.replace('Potential business implications', 
                          '<h3 class="text-xl font-bold text-gray-800 mt-6 mb-4">💼 Business Implications</h3>')

        lines = text.split('\n')
        formatted_lines = []
        in_list = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('•'):
                if not in_list:
                    formatted_lines.append('<ul class="list-disc pl-6 space-y-2 mb-4">')
                    in_list = True
                formatted_lines.append(f'<li class="text-gray-700">{line[1:].strip()}</li>')
            else:
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                if line:
                    formatted_lines.append(f'<p class="text-gray-700 mb-4">{line}</p>')
        
        if in_list:
            formatted_lines.append('</ul>')
            
        return '\n'.join(formatted_lines)

    def _get_basic_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate basic statistics for the dataset"""
        stats = {
            "numeric_summary": df.describe().to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "data_types": df.dtypes.astype(str).to_dict()
        }
        return stats

    def generate_custom_visualization(self, df: pd.DataFrame, viz_type: str, 
                                   params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate custom visualization based on user request"""
        try:
            if viz_type == "scatter":
                fig = px.scatter(df, x=params.get("x"), y=params.get("y"))
            elif viz_type == "bar":
                fig = px.bar(df, x=params.get("x"), y=params.get("y"))
            elif viz_type == "line":
                fig = px.line(df, x=params.get("x"), y=params.get("y"))
            elif viz_type == "histogram":
                fig = px.histogram(df, x=params.get("x"))
            else:
                raise ValueError(f"Unsupported visualization type: {viz_type}")

            return {
                "status": "success",
                "plot": json.loads(fig.to_json())
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }