from groq import Groq
from typing import Dict, Any, List
import json
import os
import pandas as pd

class AIQueryProcessor:
    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("Groq API key is required. Set GROQ_API_KEY environment variable.")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama3-8b-8192"
        
        from .text_to_sql import SQLQueryProcessor
        from .chart_generator import ChartGenerator
        
        self.sql_processor = SQLQueryProcessor(api_key)
        self.chart_generator = ChartGenerator()
    
    def process_user_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user query and determine appropriate action"""
        intent = self._classify_intent(query)
        
        if intent == 'data_query':
            return self._handle_data_query(query, context)
        elif intent == 'chart_request':
            return self._handle_chart_request(query, context)
        elif intent == 'calculation':
            return self._handle_calculation_request(query, context)
        else:
            return {
                'success': False,
                'error': 'Could not understand the query',
                'intent': intent,
                'suggestion': 'Try asking for data (e.g., "show me sales data") or charts (e.g., "create a bar chart of sales")'
            }
    
    def _classify_intent(self, query: str) -> str:
        """Classify user intent using Groq AI"""
        system_prompt = """Classify the user's intent into exactly one of these categories:

data_query - User wants to retrieve, filter, or view data from the database
chart_request - User wants to create a visualization, graph, or chart
calculation - User wants to add calculated fields or perform mathematical operations
other - Everything else

Return ONLY the category name, nothing else."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,
                max_tokens=20
            )
            
            intent = response.choices[0].message.content.strip().lower()
            
            valid_intents = ['data_query', 'chart_request', 'calculation', 'other']
            return intent if intent in valid_intents else 'other'
            
        except Exception as e:
            print(f"Error classifying intent: {e}")
            return 'other'
    
    def _handle_data_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data retrieval queries"""
        result = self.sql_processor.process_natural_query(query)
        
        if result['success'] and result['data']:
            df = pd.DataFrame(result['data'])
            suggested_chart = self.chart_generator.suggest_chart_type(df, query)
            result['suggested_chart'] = suggested_chart
            result['type'] = 'data'
        
        return result
    
    def _handle_chart_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chart creation requests"""
        data_result = self.sql_processor.process_natural_query(query)
        
        if not data_result['success']:
            return data_result
        
        df = pd.DataFrame(data_result['data'])
        
        chart_type = self._extract_chart_type(query)
        if not chart_type:
            chart_type = self.chart_generator.suggest_chart_type(df, query)
        
        try:
            result = self.chart_generator.create_chart_with_validation(df, chart_type)
    
            if result['success']:
                return {
                    'success': True,
                    'type': 'chart',
                    'chart_data': result['chart_data'],
                    'chart_type': chart_type,
                    'data': data_result['data'],
                    'sql_query': data_result['sql_query'],
                    'data_summary': result.get('data_summary', {})
                }
            else:
                fallback_result = self.chart_generator.create_chart_with_validation(
                    df, result['suggested_chart_type']
                )
                
                if fallback_result['success']:
                    return {
                        'success': True,
                        'type': 'chart',
                        'chart_data': fallback_result['chart_data'],
                        'chart_type': result['suggested_chart_type'],
                        'data': data_result['data'],
                        'sql_query': data_result['sql_query'],
                        'message': f"Used {result['suggested_chart_type']} instead of {chart_type}: {result['error']}"
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Could not create chart: {result["error"]}',
                        'data': data_result['data']
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': f'Error creating chart: {str(e)}',
                'data': data_result.get('data', [])
            }
    
    def _handle_calculation_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle calculation and field addition requests"""
        return {
            'success': False,
            'error': 'Calculation requests are not fully implemented yet',
            'suggestion': 'Try asking for data queries or chart requests instead'
        }
    
    def _extract_chart_type(self, query: str) -> str:
        """Extract chart type from natural language query"""
        query_lower = query.lower()
        
        chart_keywords = {
            'bar': ['bar', 'column'],
            'line': ['line', 'trend', 'over time'],
            'pie': ['pie', 'distribution', 'percentage'],
            'scatter': ['scatter', 'correlation', 'relationship'],
            'histogram': ['histogram', 'frequency'],
            'box': ['box', 'quartile', 'outlier']
        }
        
        for chart_type, keywords in chart_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return chart_type
        
        return None