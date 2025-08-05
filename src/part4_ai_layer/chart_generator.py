import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

class ChartGenerator:
    def __init__(self):
        self.chart_types = {
            'bar': self._create_bar_chart,
            'line': self._create_line_chart,
            'pie': self._create_pie_chart,
            'scatter': self._create_scatter_chart,
            'histogram': self._create_histogram,
            'box': self._create_box_plot,
            'heatmap': self._create_heatmap,
            'area': self._create_area_chart,
            'donut': self._create_donut_chart
        }
        
        self.color_palettes = {
            'default': px.colors.qualitative.Set3,
            'blues': px.colors.sequential.Blues,
            'greens': px.colors.sequential.Greens,
            'reds': px.colors.sequential.Reds
        }
    
    def suggest_chart_type(self, df: pd.DataFrame, user_intent: str = "") -> str:
        """Enhanced chart type suggestion based on data characteristics and user intent"""
        if df.empty:
            return 'bar'
            
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
        date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        intent_lower = user_intent.lower()
        
        chart_keywords = {
            'bar': ['bar', 'column', 'vertical'],
            'line': ['line', 'trend', 'time', 'over time', 'timeline'],
            'pie': ['pie', 'distribution', 'percentage', 'proportion'],
            'scatter': ['scatter', 'correlation', 'relationship', 'vs'],
            'histogram': ['histogram', 'frequency', 'distribution'],
            'box': ['box', 'quartile', 'outlier', 'spread'],
            'heatmap': ['heatmap', 'correlation matrix', 'heat'],
            'area': ['area', 'stacked area', 'filled'],
            'donut': ['donut', 'doughnut']
        }
        
        for chart_type, keywords in chart_keywords.items():
            if any(keyword in intent_lower for keyword in keywords):
                return chart_type
        
        num_rows = len(df)
        
        if date_cols and numeric_cols:
            return 'line'
        
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            unique_categories = df[categorical_cols[0]].nunique()
            
            if unique_categories <= 8 and num_rows <= 50:
                return 'pie'
            elif unique_categories <= 20:
                return 'bar'
            else:
                return 'histogram'
        
        elif len(numeric_cols) >= 3:
            return 'heatmap'
        elif len(numeric_cols) == 2:
            return 'scatter'
        elif len(numeric_cols) == 1:
            return 'histogram'
        
        return 'bar'
    
    def create_chart(self, df: pd.DataFrame, chart_type: str, config: Dict[str, Any] = None) -> str:
        """Create chart based on type and configuration with enhanced error handling"""
        if df.empty:
            raise ValueError("Cannot create chart from empty data")
        
        if chart_type not in self.chart_types:
            chart_type = 'bar'
        
        config = config or {}

        try:
            df_processed = self._preprocess_data(df)
            
            fig = self.chart_types[chart_type](df_processed, config)
            
            fig = self._apply_enhanced_styling(fig, chart_type, config)
            
            return self._safe_json_conversion(fig)
            
        except Exception as e:
            return self._create_fallback_chart(df, str(e))

    def _safe_json_conversion(self, fig: go.Figure) -> str:
        """Safely convert plotly figure to JSON, handling numpy/pandas types"""
        try:
            fig_dict = fig.to_dict()
            
            fig_dict = self._convert_numpy_types(fig_dict)
            
            return json.dumps(fig_dict, default=str)
            
        except Exception as e:
            try:
                return fig.to_json()
            except:
                return json.dumps({
                    "data": [],
                    "layout": {"title": {"text": f"Chart Error: {str(e)}"}}
                })

    def _convert_numpy_types(self, obj):
        """Recursively convert numpy/pandas types to native Python types"""
        if isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess data for better chart rendering"""
        df_clean = df.copy()
        
        numeric_cols = df_clean.select_dtypes(include=['number']).columns
        categorical_cols = df_clean.select_dtypes(include=['object', 'category']).columns
        
        df_clean[numeric_cols] = df_clean[numeric_cols].fillna(0)
        
        df_clean[categorical_cols] = df_clean[categorical_cols].fillna('Unknown')
        
        if len(df_clean) > 1000:
            df_clean = df_clean.head(1000)
        
        return df_clean
    
    def _apply_enhanced_styling(self, fig: go.Figure, chart_type: str, config: Dict[str, Any]) -> go.Figure:
        """Apply enhanced styling to charts"""
        fig.update_layout(
            template="plotly_white",
            font=dict(size=12, family="Arial, sans-serif"),
            title_font_size=16,
            title_x=0.5,
            showlegend=True,
            margin=dict(l=60, r=60, t=80, b=60),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            hovermode='closest'
        )
        
        if chart_type in ['bar', 'line', 'scatter']:
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
        
        return fig
    
    def _get_best_columns(self, df: pd.DataFrame) -> Tuple[str, str]:
        """Get the best x and y columns for charting"""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        x_col = categorical_cols[0] if categorical_cols else df.columns[0]
        y_col = numeric_cols[0] if numeric_cols else df.columns[1] if len(df.columns) > 1 else df.columns[0]
        
        return x_col, y_col
    
    def _create_bar_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Enhanced bar chart creation"""
        x_col, y_col = self._get_best_columns(df)
        x_col = config.get('x_column', x_col)
        y_col = config.get('y_column', y_col)
        
        if len(df) > 20:
            df_agg = df.groupby(x_col)[y_col].agg(['sum', 'count']).reset_index()
            df_agg.columns = [x_col, y_col, 'count']
            df_agg = df_agg[[x_col, y_col]]
        else:
            df_agg = df
        
        if len(df_agg) > 15:
            df_agg = df_agg.nlargest(15, y_col)
        
        fig = px.bar(
            df_agg, x=x_col, y=y_col,
            title=config.get('title', f'{y_col} by {x_col}'),
            color=y_col,
            color_continuous_scale='viridis',
            text=y_col
        )
        
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        
        return fig
    
    def _create_line_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Enhanced line chart creation"""
        x_col, y_col = self._get_best_columns(df)
        x_col = config.get('x_column', x_col)
        y_col = config.get('y_column', y_col)
        
        fig = px.line(
            df, x=x_col, y=y_col,
            title=config.get('title', f'{y_col} over {x_col}'),
            markers=True,
            line_shape='spline'
        )
        
        fig.update_traces(
            line=dict(width=3),
            marker=dict(size=8)
        )
        
        return fig
    
    def _create_pie_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Enhanced pie chart creation"""
        x_col, y_col = self._get_best_columns(df)
        names_col = config.get('names_column', x_col)
        values_col = config.get('values_column', y_col)
        
        df_agg = df.groupby(names_col)[values_col].sum().reset_index()
        
        if len(df_agg) > 10:
            df_top = df_agg.nlargest(9, values_col)
            others_sum = df_agg.nsmallest(len(df_agg) - 9, values_col)[values_col].sum()
            if others_sum > 0:
                others_row = pd.DataFrame({names_col: ['Others'], values_col: [others_sum]})
                df_agg = pd.concat([df_top, others_row], ignore_index=True)
            else:
                df_agg = df_top
        
        fig = px.pie(
            df_agg, names=names_col, values=values_col,
            title=config.get('title', f'Distribution of {values_col}'),
            hole=0.0
        )
        
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Value: %{value}<br>Percentage: %{percent}<extra></extra>'
        )
        
        return fig
    
    def _create_donut_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create donut chart (pie chart with hole)"""
        fig = self._create_pie_chart(df, config)
        fig.update_traces(hole=0.4)
        return fig
    
    def _create_scatter_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Enhanced scatter plot creation"""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if len(numeric_cols) < 2:
            return self._create_bar_chart(df, config)
        
        x_col = config.get('x_column', numeric_cols[0])
        y_col = config.get('y_column', numeric_cols[1])
        
        fig = px.scatter(
            df, x=x_col, y=y_col,
            title=config.get('title', f'{y_col} vs {x_col}'),
            opacity=0.7,
            size_max=10
        )
        
        return fig
    
    def _create_histogram(self, df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Enhanced histogram creation"""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if not numeric_cols:
            return self._create_bar_chart(df, config)
        
        x_col = config.get('x_column', numeric_cols[0])
        
        fig = px.histogram(
            df, x=x_col,
            title=config.get('title', f'Distribution of {x_col}'),
            nbins=min(30, len(df.dropna()) // 2),
            marginal="box"
        )
        
        return fig
    
    def _create_box_plot(self, df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Enhanced box plot creation"""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if not numeric_cols:
            return self._create_bar_chart(df, config)
        
        y_col = config.get('y_column', numeric_cols[0])
        
        fig = px.box(
            df, y=y_col,
            title=config.get('title', f'Box Plot of {y_col}'),
            points="outliers"
        )
        
        return fig
    
    def _create_heatmap(self, df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create correlation heatmap for numeric data"""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if len(numeric_cols) < 2:
            return self._create_bar_chart(df, config)
        
        corr_matrix = df[numeric_cols].corr()
        
        fig = px.imshow(
            corr_matrix,
            title=config.get('title', 'Correlation Heatmap'),
            color_continuous_scale='RdBu',
            aspect="auto"
        )
        
        return fig
    
    def _create_area_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create area chart"""
        x_col, y_col = self._get_best_columns(df)
        x_col = config.get('x_column', x_col)
        y_col = config.get('y_column', y_col)
        
        fig = px.area(
            df, x=x_col, y=y_col,
            title=config.get('title', f'{y_col} over {x_col}')
        )
        
        return fig
    
    def _create_fallback_chart(self, df: pd.DataFrame, error_msg: str) -> str:
        """Create a simple fallback chart when main chart creation fails"""
        try:
            if len(df.columns) >= 2:
                fig = go.Figure(data=[
                    go.Bar(x=df.iloc[:10, 0], y=df.iloc[:10, 1])
                ])
                fig.update_layout(
                    title=f"Fallback Chart (Error: {error_msg})",
                    template="plotly_white"
                )
                return fig.to_json()
            else:
                fig = go.Figure()
                fig.update_layout(
                    title=f"No Data Available (Error: {error_msg})",
                    template="plotly_white",
                    annotations=[
                        dict(
                            text="No data available to display",
                            xref="paper", yref="paper",
                            x=0.5, y=0.5, xanchor='center', yanchor='middle',
                            showarrow=False,
                            font=dict(size=16, color="gray")
                        )
                    ]
                )
                return fig.to_json()
        except Exception:
            return json.dumps({
                "data": [],
                "layout": {
                    "title": {"text": f"Chart Error: {error_msg}"},
                    "template": "plotly_white"
                }
            })

    def get_available_chart_types(self) -> List[str]:
        """Get list of available chart types"""
        return list(self.chart_types.keys())
    
    def validate_data_for_chart(self, df: pd.DataFrame, chart_type: str) -> Tuple[bool, str]:
        """Validate if data is suitable for the requested chart type"""
        if df.empty:
            return False, "Data is empty"
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        validations = {
            'pie': (len(categorical_cols) >= 1 and len(numeric_cols) >= 1, 
                   "Pie charts need at least one categorical and one numeric column"),
            'scatter': (len(numeric_cols) >= 2, 
                       "Scatter plots need at least two numeric columns"),
            'heatmap': (len(numeric_cols) >= 2, 
                       "Heatmaps need at least two numeric columns"),
            'histogram': (len(numeric_cols) >= 1, 
                         "Histograms need at least one numeric column"),
            'box': (len(numeric_cols) >= 1, 
                   "Box plots need at least one numeric column")
        }
        
        if chart_type in validations:
            condition, message = validations[chart_type]
            if not condition:
                return False, message
        
        return True, "Data is valid for this chart type"
    
    def create_chart_with_validation(self, df: pd.DataFrame, chart_type: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create chart with comprehensive validation and error handling"""
        try:
            is_valid, validation_message = self.validate_data_for_chart(df, chart_type)
            
            if not is_valid:
                suggested_type = self.suggest_chart_type(df)
                return {
                    'success': False,
                    'error': validation_message,
                    'suggested_chart_type': suggested_type,
                    'chart_data': None
                }
            
            chart_json = self.create_chart(df, chart_type, config)
            
            return {
                'success': True,
                'chart_data': chart_json,
                'chart_type': chart_type,
                'data_summary': self._generate_data_summary(df)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'suggested_chart_type': 'bar',
                'chart_data': None
            }
    
    def _generate_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics for the data"""
        return {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'numeric_columns': len(df.select_dtypes(include=['number']).columns),
            'categorical_columns': len(df.select_dtypes(include=['object', 'category']).columns),
            'missing_values': df.isnull().sum().sum(),
            'column_names': df.columns.tolist()
        }

    def create_multiple_charts(self, df: pd.DataFrame, chart_types: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """Create multiple chart types for the same data"""
        if chart_types is None:
            suggested = self.suggest_chart_type(df)
            chart_types = [suggested]
            
            if suggested == 'bar':
                chart_types.extend(['pie', 'line'])
            elif suggested == 'line':
                chart_types.extend(['bar', 'area'])
            elif suggested == 'pie':
                chart_types.extend(['bar', 'donut'])
            else:
                chart_types.extend(['bar', 'pie'])
        
        results = {}
        for chart_type in chart_types[:3]:
            result = self.create_chart_with_validation(df, chart_type)
            results[chart_type] = result
        
        return results

    def get_chart_recommendations(self, df: pd.DataFrame, user_query: str = "") -> Dict[str, Any]:
        """Get chart recommendations based on data characteristics and user query"""
        primary_suggestion = self.suggest_chart_type(df, user_query)
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        recommendations = {
            'primary_suggestion': primary_suggestion,
            'alternative_suggestions': [],
            'reasoning': '',
            'data_insights': {
                'best_x_column': None,
                'best_y_column': None,
                'interesting_patterns': []
            }
        }
        
        all_suitable = []
        for chart_type in self.chart_types.keys():
            is_valid, _ = self.validate_data_for_chart(df, chart_type)
            if is_valid and chart_type != primary_suggestion:
                all_suitable.append(chart_type)
        
        recommendations['alternative_suggestions'] = all_suitable[:3]
        
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            recommendations['reasoning'] = f"Data has {len(categorical_cols)} categorical and {len(numeric_cols)} numeric columns, ideal for comparison charts"
            recommendations['data_insights']['best_x_column'] = categorical_cols[0]
            recommendations['data_insights']['best_y_column'] = numeric_cols[0]
        elif len(numeric_cols) >= 2:
            recommendations['reasoning'] = f"Multiple numeric columns detected, good for correlation analysis"
        else:
            recommendations['reasoning'] = "Limited data structure, using basic visualization"
        
        return recommendations