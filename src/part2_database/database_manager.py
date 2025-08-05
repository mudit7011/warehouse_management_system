import requests
import pandas as pd
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

class BaserowManager:
    def __init__(self, api_token, base_url="https://api.baserow.io"):
        self.api_token = api_token
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Token {api_token}',
            'Content-Type': 'application/json'
        }
    
    def create_database(self, workspace_id, name):
        """Create a new database in Baserow"""
        url = f"{self.base_url}/api/applications/"
        data = {
            'type': 'database',
            'workspace': workspace_id,
            'name': name
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        return response.json() if response.status_code == 200 else None
    
    def create_table(self, database_id, name, fields):
        """Create a table with specified fields"""
        url = f"{self.base_url}/api/database/tables/"
        data = {
            'database_id': database_id,
            'name': name
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code != 200:
            return None
        
        table = response.json()
        table_id = table['id']
        
        for field in fields:
            self.create_field(table_id, field)
        
        return table
    
    def create_field(self, table_id, field_config):
        """Create a field in a table"""
        url = f"{self.base_url}/api/database/fields/"
        data = {
            'table_id': table_id,
            'type': field_config.get('type', 'text'),
            'name': field_config.get('name', 'New Field')
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        return response.json() if response.status_code == 200 else None
    
    def insert_rows(self, table_id, rows):
        """Insert multiple rows into a table"""
        url = f"{self.base_url}/api/database/rows/table/{table_id}/batch/"
        data = {'items': rows}
        
        response = requests.post(url, headers=self.headers, json=data)
        return response.json() if response.status_code == 200 else None
    
    def get_rows(self, table_id, size=100, page=1):
        """Get rows from a table"""
        url = f"{self.base_url}/api/database/rows/table/{table_id}/"
        params = {'size': size, 'page': page}
        
        response = requests.get(url, headers=self.headers, params=params)
        return response.json() if response.status_code == 200 else None

def setup_wms_database():
    """Setup the WMS database structure"""
    API_TOKEN = ""
    WORKSPACE_ID = 1
    
    manager = BaserowManager(API_TOKEN)
    
    database = manager.create_database(WORKSPACE_ID, "WMS Database")
    if not database:
        print("Failed to create database")
        return
    
    database_id = database['id']
    
    tables_config = {
        'products': [
            {'name': 'MSKU', 'type': 'text'},
            {'name': 'Product Name', 'type': 'text'},
            {'name': 'Category', 'type': 'text'},
            {'name': 'Price', 'type': 'number'},
            {'name': 'Description', 'type': 'long_text'},
            {'name': 'Status', 'type': 'single_select'}
        ],
        'sales_data': [
            {'name': 'Order ID', 'type': 'text'},
            {'name': 'SKU', 'type': 'text'},
            {'name': 'MSKU', 'type': 'text'},
            {'name': 'Quantity', 'type': 'number'},
            {'name': 'Price', 'type': 'number'},
            {'name': 'Total', 'type': 'number'},
            {'name': 'Date', 'type': 'date'},
            {'name': 'Marketplace', 'type': 'text'},
            {'name': 'Status', 'type': 'single_select'}
        ],
        'returns_data': [
            {'name': 'Return ID', 'type': 'text'},
            {'name': 'Original Order ID', 'type': 'text'},
            {'name': 'MSKU', 'type': 'text'},
            {'name': 'Quantity Returned', 'type': 'number'},
            {'name': 'Return Reason', 'type': 'text'},
            {'name': 'Return Date', 'type': 'date'},
            {'name': 'Refund Amount', 'type': 'number'},
            {'name': 'Status', 'type': 'single_select'}
        ],
        'inventory': [
            {'name': 'MSKU', 'type': 'text'},
            {'name': 'Current Stock', 'type': 'number'},
            {'name': 'Reserved Stock', 'type': 'number'},
            {'name': 'Available Stock', 'type': 'number'},
            {'name': 'Reorder Level', 'type': 'number'},
            {'name': 'Last Updated', 'type': 'date'},
            {'name': 'Location', 'type': 'text'}
        ]
    }
    
    created_tables = {}
    for table_name, fields in tables_config.items():
        table = manager.create_table(database_id, table_name, fields)
        if table:
            created_tables[table_name] = table['id']
            print(f"Created table: {table_name}")
        else:
            print(f"Failed to create table: {table_name}")
    
    return database_id, created_tables

@dataclass
class Product:
    msku: str
    product_name: str
    category: str
    price: float
    description: Optional[str] = None
    status: str = "active"

@dataclass
class SalesRecord:
    order_id: str
    sku: str
    msku: str
    quantity: int
    price: float
    total: float
    date: datetime
    marketplace: str
    status: str = "completed"

@dataclass
class ReturnRecord:
    return_id: str
    original_order_id: str
    msku: str
    quantity_returned: int
    return_reason: str
    return_date: datetime
    refund_amount: float
    status: str = "processed"

@dataclass
class InventoryRecord:
    msku: str
    current_stock: int
    reserved_stock: int
    available_stock: int
    reorder_level: int
    last_updated: datetime
    location: str