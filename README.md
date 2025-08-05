# Warehouse Management System (WMS)

A comprehensive Warehouse Management System built with Python, Flask, and AI-powered data processing capabilities using Groq API.

## Loom Video Link

https://www.loom.com/share/8d6622b6ca2d441da97c17f89200168c?sid=e1ddd997-3935-4f69-b4ae-32966a4c5ece

## Features

### Part 1: Data Cleaning and Management
- **SKU Mapper GUI**: Python Tkinter application for mapping SKUs to Master SKUs
- **Flexible Input Processing**: Support for CSV and Excel files
- **Data Validation**: SKU format validation and error handling
- **Batch Processing**: Process large datasets efficiently

### Part 2: Database Management
- **Relational Database**: SQLite database with proper relationships
- **Data Models**: Products, Sales, Inventory, and Returns tables
- **API Integration**: Ready for Baserow or other no-code database solutions

### Part 3: Web Application
- **Flask Web App**: User-friendly interface for data upload and processing
- **Dashboard**: Key metrics and statistics visualization
- **File Upload**: Drag-and-drop interface for sales data
- **Results Visualization**: Interactive tables and charts

### Part 4: AI-Powered Features
- **Natural Language Queries**: Ask questions in plain English
- **Text-to-SQL**: Convert natural language to SQL queries using Groq AI
- **Auto Chart Generation**: Create visualizations automatically
- **Smart Data Analysis**: AI-assisted data insights

## Tech Stack

- **Backend**: Python, Flask, SQLite
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **AI**: Groq API (Free tier available)
- **Visualization**: Plotly.js
- **Data Processing**: Pandas, NumPy
- **GUI**: Tkinter (for standalone application)

## Setup Instructions

### Prerequisites
1. Python 3.8 or higher
2. Groq API key (free at https://console.groq.com/)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/mudit7011/warehouse_management_system.git
   cd warehouse-management-system


### Usage Guide
1. **Upload Data**
-Navigate to the dashboard
-Click "Upload File" or drag & drop your CSV/Excel file
-The system will automatically process and map SKUs to Master SKUs
2. **View Results**
-Processing Results: View mapping statistics and success rates
-Data Preview: See processed data with assigned MSKUs
-Top Products: View most frequent product categories
3. **AI-Powered Queries**
-After uploading data, access the AI chat feature:

Example queries:

"Show me top selling products"
"Create a bar chart of sales by marketplace"
"What's the current inventory level?"
"Generate a pie chart of product categories"

4. **Start the script**
-Run this file in your terminal:

```bash

python src/part3_web_app/app.py

```
