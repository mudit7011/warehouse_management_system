from groq import Groq
import sqlite3
import pandas as pd
import json
from typing import Dict, List, Any, Tuple
import re
import os
from datetime import datetime

class SQLQueryProcessor:
    def __init__(self, api_key: str = None, db_path: str = None):
        api_key = api_key or os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("Groq API key is required. Set GROQ_API_KEY environment variable or pass api_key parameter.")
        
        self.client = Groq(api_key=api_key)
        self.db_path = db_path or "wms_data.db"
        self.model = "llama3-8b-8192"
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize SQLite database with sample schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_data (
            id INTEGER PRIMARY KEY,
            order_id TEXT,
            sku TEXT,
            msku TEXT,
            quantity INTEGER,
            price REAL,
            total REAL,
            date TEXT,
            marketplace TEXT,
            status TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            msku TEXT UNIQUE,
            product_name TEXT,
            category TEXT,
            price REAL,
            description TEXT,
            status TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY,
            msku TEXT,
            current_stock INTEGER,
            reserved_stock INTEGER,
            available_stock INTEGER,
            reorder_level INTEGER,
            last_updated TEXT,
            location TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS returns_data (
            id INTEGER PRIMARY KEY,
            return_id TEXT,
            original_order_id TEXT,
            msku TEXT,
            quantity_returned INTEGER,
            return_reason TEXT,
            return_date TEXT,
            refund_amount REAL,
            status TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_schema_info(self) -> str:
        """Get database schema information for AI context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        schema_info = []
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            column_info = []
            for col in columns:
                column_info.append(f"{col[1]} ({col[2]})")
            
            schema_info.append(f"Table: {table_name}\nColumns: {', '.join(column_info)}")
        
        conn.close()
        return "\n\n".join(schema_info)
    
    def text_to_sql(self, user_query: str) -> Tuple[str, bool]:
        """Convert natural language query to SQL using Groq"""
        schema = self.get_schema_info()
        
        system_prompt = f"""You are a SQL expert. Convert natural language queries to SQL based on this database schema:

{schema}

IMPORTANT RULES:
1. ONLY return the SQL query, nothing else
2. Use proper SQLite syntax
3. If the query is unclear or unsafe, return exactly: INVALID_QUERY
4. Focus on SELECT statements primarily
5. Use appropriate JOINs when referencing multiple tables
6. For aggregations, use GROUP BY appropriately
7. Always use proper WHERE clauses for filtering

EXAMPLES:
User: "Show me top selling products"
Response: SELECT msku, SUM(quantity) as total_sold FROM sales_data GROUP BY msku ORDER BY total_sold DESC LIMIT 10

User: "What's the current inventory for all products?"
Response: SELECT msku, current_stock, available_stock FROM inventory

User: "Show sales by marketplace"
Response: SELECT marketplace, COUNT(*) as order_count, SUM(total) as total_sales FROM sales_data GROUP BY marketplace"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            if "INVALID_QUERY" in sql_query or self._is_unsafe_query(sql_query):
                return "INVALID_QUERY", False
            
            return sql_query, True
            
        except Exception as e:
            print(f"Error generating SQL with Groq: {e}")
            return "INVALID_QUERY", False
    
    def _is_unsafe_query(self, query: str) -> bool:
        """Basic safety check for SQL queries"""
        unsafe_patterns = [
            r'\bDROP\b',
            r'\bDELETE\b',
            r'\bUPDATE\b',
            r'\bINSERT\b',
            r'\bALTER\b',
            r'\bCREATE\b',
            r'--',
            r'/\*',
            r'\*/',
            r';.*\w'
        ]
        
        query_upper = query.upper()
        for pattern in unsafe_patterns:
            if re.search(pattern, query_upper):
                return True
        return False
    
    def execute_query(self, sql_query: str) -> Tuple[pd.DataFrame, bool, str]:
        """Execute SQL query and return results"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(sql_query, conn)
            conn.close()
            return df, True, "Success"
        except Exception as e:
            return pd.DataFrame(), False, str(e)
    
    def add_calculated_field(self, df: pd.DataFrame, field_definition: str) -> pd.DataFrame:
        """Add calculated fields to DataFrame using Groq AI"""
        system_prompt = """You are a pandas expert. Given a DataFrame and a field definition, provide ONLY the Python code to add the calculated field.

RULES:
1. Return ONLY the pandas assignment statement
2. Use 'df' as the DataFrame variable name
3. Handle potential errors with appropriate conditions
4. Use proper pandas syntax

EXAMPLES:
Input: "Add profit margin as (price - cost) / price * 100"
Output: df['profit_margin'] = ((df['price'] - df['cost']) / df['price'] * 100).fillna(0)

Input: "Add total sales as quantity * price"
Output: df['total_sales'] = df['quantity'] * df['price']"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"DataFrame columns: {list(df.columns)}\nField to add: {field_definition}"}
                ],
                temperature=0.1,
                max_tokens=150
            )
            
            code = response.choices[0].message.content.strip()
            
            code = code.replace('```python', '').replace('```', '').strip()
            
            local_vars = {'df': df, 'pd': pd}
            exec(code, {"__builtins__": {}}, local_vars)
            return local_vars['df']
            
        except Exception as e:
            print(f"Error adding calculated field: {e}")
            return df
    
    def process_natural_query(self, user_query: str) -> Dict[str, Any]:
        """Process a natural language query end-to-end"""
        sql_query, sql_success = self.text_to_sql(user_query)
        
        if not sql_success:
            return {
                'success': False,
                'error': 'Could not convert query to SQL',
                'sql_query': None,
                'data': None
            }
        
        df, exec_success, error_msg = self.execute_query(sql_query)
        
        if not exec_success:
            return {
                'success': False,
                'error': error_msg,
                'sql_query': sql_query,
                'data': None
            }
        
        return {
            'success': True,
            'sql_query': sql_query,
            'data': df.to_dict('records'),
            'columns': list(df.columns),
            'row_count': len(df)
        }

    def sync_with_uploaded_data(self, sku_mapper_instance):
        """Sync the AI database with actual uploaded data"""
        try:
            if not sku_mapper_instance or not hasattr(sku_mapper_instance, 'processed_data') or sku_mapper_instance.processed_data is None:
                print("❌ No processed data found to sync")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM sales_data")
            cursor.execute("DELETE FROM products") 
            cursor.execute("DELETE FROM inventory")
            print("🧹 Cleared existing sample data")
            
            df = sku_mapper_instance.processed_data
            print(f"📊 Syncing {len(df)} records")
            
            original_sku_col = None
            for col in df.columns:
                if col not in ['MSKU', 'processed_at', 'mapping_method'] and any(term in col.lower() for term in ['sku', 'product', 'item', 'order']):
                    original_sku_col = col
                    break
            
            if not original_sku_col:
                original_sku_col = df.columns[0]
            
            print(f"Using '{original_sku_col}' as original SKU column")
            
            for idx, row in df.iterrows():
                cursor.execute('''
                INSERT INTO sales_data (order_id, sku, msku, quantity, price, total, date, marketplace, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    f'ORD_{idx+1:06d}',
                    str(row.get(original_sku_col, '')),
                    str(row.get('MSKU', 'UNKNOWN')),
                    int(row.get('Quantity', 1)) if pd.notna(row.get('Quantity')) else 1,
                    float(row.get('Price', 0)) if pd.notna(row.get('Price')) else 0,
                    float(row.get('Total', 0)) if pd.notna(row.get('Total')) else 0,
                    str(row.get('Order Date', '2025-01-01'))[:10],  # Ensure date format
                    str(row.get('Marketplace', 'Direct')),
                    'completed'
                ))
            
            msku_counts = df['MSKU'].value_counts()
            for msku, count in msku_counts.items():
                if pd.isna(msku) or str(msku).startswith('UNCATEGORIZED'):
                    continue
                    
                cursor.execute('''
                INSERT OR REPLACE INTO products (msku, product_name, category, price, description, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    str(msku),
                    str(msku).replace('_', ' ').title(),
                    self._categorize_msku(str(msku)),
                    float(df[df['MSKU'] == msku]['Price'].mean()) if 'Price' in df.columns else 10.0,
                    f'Intelligent auto-categorized product group with {count} items',
                    'active'
                ))
            
            for msku, count in msku_counts.items():
                if pd.isna(msku) or str(msku).startswith('UNCATEGORIZED'):
                    continue
                    
                cursor.execute('''
                INSERT OR REPLACE INTO inventory (msku, current_stock, reserved_stock, available_stock, reorder_level, last_updated, location)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(msku),
                    count * 10,
                    count,       
                    count * 9,  
                    max(5, count // 2), 
                    datetime.now().strftime('%Y-%m-%d'),
                    'Warehouse A'
                ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Successfully synced {len(df)} records with AI database")
            print(f"📦 Created {len(msku_counts)} product groups")
            return True
            
        except Exception as e:
            print(f"❌ Error syncing data: {e}")
            return False

    def _categorize_msku(self, msku):
        """Categorize MSKU for product table"""
        msku_upper = msku.upper()
        
        if 'BRAND' in msku_upper:
            return 'Branded Products'
        elif 'ENTERTAINMENT' in msku_upper:
            return 'Entertainment'  
        elif 'ELECTRONICS' in msku_upper:
            return 'Electronics'
        elif 'SUNGLASSES' in msku_upper:
            return 'Accessories'
        elif 'NUMERIC' in msku_upper:
            return 'Orders'
        else:
            return 'General'

    def insert_sample_data(self):
        """Insert sample data for testing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sample_sales = [
            ('ORD001', 'SKU001', 'MSKU001', 5, 19.99, 99.95, '2024-01-01', 'Amazon', 'completed'),
            ('ORD002', 'SKU002', 'MSKU002', 3, 29.99, 89.97, '2024-01-02', 'eBay', 'completed'),
            ('ORD003', 'SKU001', 'MSKU001', 2, 19.99, 39.98, '2024-01-03', 'Amazon', 'completed'),
            ('ORD004', 'SKU003', 'MSKU003', 1, 49.99, 49.99, '2024-01-04', 'Shopify', 'completed'),
            ('ORD005', 'SKU002', 'MSKU002', 4, 29.99, 119.96, '2024-01-05', 'eBay', 'completed'),
        ]
        
        cursor.executemany('''
        INSERT OR REPLACE INTO sales_data 
        (order_id, sku, msku, quantity, price, total, date, marketplace, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_sales)
        
        sample_products = [
            ('MSKU001', 'Wireless Headphones', 'Electronics', 19.99, 'Bluetooth wireless headphones', 'active'),
            ('MSKU002', 'Coffee Mug', 'Home & Kitchen', 29.99, 'Ceramic coffee mug', 'active'),
            ('MSKU003', 'Desk Lamp', 'Office', 49.99, 'LED desk lamp with adjustable brightness', 'active'),
        ]
        
        cursor.executemany('''
        INSERT OR REPLACE INTO products 
        (msku, product_name, category, price, description, status)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_products)
        
        sample_inventory = [
            ('MSKU001', 150, 10, 140, 20, '2024-01-01', 'Warehouse A'),
            ('MSKU002', 200, 15, 185, 30, '2024-01-01', 'Warehouse B'),
            ('MSKU003', 75, 5, 70, 15, '2024-01-01', 'Warehouse A'),
        ]
        
        cursor.executemany('''
        INSERT OR REPLACE INTO inventory 
        (msku, current_stock, reserved_stock, available_stock, reorder_level, last_updated, location)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_inventory)
        
        conn.commit()
        conn.close()
        print("Sample data inserted successfully!")