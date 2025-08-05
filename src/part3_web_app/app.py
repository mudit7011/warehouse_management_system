# src/part3_web_app/app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pandas as pd
import os
import uuid
from werkzeug.utils import secure_filename
import json
from datetime import datetime

# Import our custom modules with error handling
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import with error handling
try:
    from part1_data_cleaning.sku_mapper import SKUMapper
    sku_mapper_available = True
except ImportError as e:
    print(f"Warning: SKU Mapper not available: {e}")
    sku_mapper_available = False
    SKUMapper = None

try:
    from part2_database.database_manager import BaserowManager
    baserow_available = True
except ImportError as e:
    print(f"Warning: Baserow Manager not available: {e}")
    baserow_available = False
    BaserowManager = None

try:
    from part4_ai_layer.text_to_sql import SQLQueryProcessor
    from part4_ai_layer.ai_query_processor import AIQueryProcessor
    ai_modules_available = True
except ImportError as e:
    print(f"Warning: AI modules not available: {e}")
    ai_modules_available = False
    SQLQueryProcessor = None
    AIQueryProcessor = None

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize components with error handling
sku_mapper = None
if sku_mapper_available:
    try:
        sku_mapper = SKUMapper()
        sku_mapper.load_master_mappings()  # Load default mappings
        print("✅ SKU Mapper initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize SKU Mapper: {e}")
        sku_mapper_available = False

# Initialize AI processor (requires GROQ_API_KEY environment variable)
ai_processor = None
sql_processor = None
ai_enabled = False

if ai_modules_available:
    try:
        ai_processor = AIQueryProcessor()
        sql_processor = SQLQueryProcessor()
        # Insert sample data for testing
        sql_processor.insert_sample_data()
        ai_enabled = True
        print("✅ AI features initialized successfully")
    except Exception as e:
        print(f"❌ AI features disabled: {e}")
        ai_processor = None
        sql_processor = None
        ai_enabled = False

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def dashboard():
    """Main dashboard"""
    stats = {
        'total_products': len(sku_mapper.master_mappings) if sku_mapper else 0,
        'processed_orders': 0,
        'pending_mappings': 0,
        'success_rate': 95.5,
        'ai_enabled': ai_enabled,
        'sku_mapper_available': sku_mapper_available,
        'baserow_available': baserow_available
    }
    return render_template('dashboard.html', stats=stats)

@app.route('/upload')
def upload_page():
    """Upload page for sales data"""
    if not sku_mapper_available:
        flash('SKU Mapper is not available. Please check the installation.')
        return redirect(url_for('dashboard'))
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing with AI sync"""
    if not sku_mapper_available or not sku_mapper:
        flash('SKU Mapper is not available.')
        return redirect(url_for('dashboard'))
    
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Process the file
            if filename.lower().endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            # Process with SKU mapper
            processed_df = sku_mapper.process_sales_data(df)
            
            # 🔥 SYNC WITH AI DATABASE (if available)
            ai_synced = False
            if ai_enabled and sql_processor and hasattr(sql_processor, 'sync_with_uploaded_data'):
                try:
                    ai_synced = sql_processor.sync_with_uploaded_data(sku_mapper)
                    if ai_synced:
                        flash('✅ Data synced with AI system - you can now query your actual data!')
                    else:
                        flash('⚠️ Data processed but AI sync failed')
                except Exception as e:
                    flash(f'⚠️ AI sync error: {str(e)}')
            
            # Save processed data
            processed_filename = f"processed_{filename}"
            processed_filepath = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)
            processed_df.to_csv(processed_filepath, index=False)
            
            # Generate results summary
            results = generate_processing_results(processed_df)
            
            return render_template('results.html', 
                                 results=results, 
                                 filename=processed_filename,
                                 original_filename=file.filename,
                                 table_html=processed_df.head(100).to_html(classes='table table-striped', table_id='results-table'),
                                 ai_synced=ai_synced)
        
        except Exception as e:
            flash(f'Error processing file: {str(e)}')
            return redirect(url_for('upload_page'))
    
    flash('Invalid file format. Please upload CSV or Excel files.')
    return redirect(request.url)

@app.route('/mappings')
def view_mappings():
    """View current SKU mappings"""
    if not sku_mapper_available or not sku_mapper:
        flash('SKU Mapper is not available.')
        return redirect(url_for('dashboard'))
    
    return render_template('mappings.html', mappings=sku_mapper.master_mappings)

@app.route('/mappings/add', methods=['POST'])
def add_mapping_web():
    """Add new mapping via web interface"""
    if not sku_mapper_available or not sku_mapper:
        flash('SKU Mapper is not available.')
        return redirect(url_for('view_mappings'))
    
    msku = request.form.get('msku', '').strip()
    skus_text = request.form.get('skus', '').strip()
    
    if not msku or not skus_text:
        flash('Please provide both MSKU and SKU variants.')
        return redirect(url_for('view_mappings'))
    
    # Parse SKUs (comma or newline separated)
    skus = [sku.strip() for sku in skus_text.replace('\n', ',').split(',') if sku.strip()]
    
    if not skus:
        flash('Please provide at least one SKU variant.')
        return redirect(url_for('view_mappings'))
    
    sku_mapper.master_mappings[msku] = skus
    flash(f'Mapping added successfully: {msku} -> {", ".join(skus)}')
    
    return redirect(url_for('view_mappings'))

@app.route('/add-sample-mappings')
def add_sample_mappings():
    """Add sample mappings for the uploaded data"""
    if not sku_mapper_available or not sku_mapper:
        flash('SKU Mapper is not available.')
        return redirect(url_for('dashboard'))
    
    # Based on your uploaded data (the SKUs I saw in your screenshot)
    sample_mappings = {
        'WIRELESS_HEADPHONES': ['X0024AAU4D', 'X0024A2EYH', 'WH001', 'HEADPHONE_BT'],
        'PHONE_ACCESSORIES': ['X0027Z4S1L', 'X0026EWNTH', 'X0027375Z'],
        'CHARGING_CABLES': ['X0025L96YB', 'X001VSXA73', 'X001W7Q1M9'],
        'PHONE_CASES': ['X001W7X2XZ', 'X0026ER40F', 'CASE_001'],
        'ELECTRONIC_ACCESSORIES': ['X0024AAU4D', 'X0024A2EYH', 'X0027Z4S1L'],
        'MOBILE_ACCESSORIES': ['X0026EWNTH', 'X0027375Z', 'X0025L96YB'],
        'TECH_GADGETS': ['X001VSXA73', 'X001W7Q1M9', 'X001W7X2XZ'],
        'DEVICE_ACCESSORIES': ['X0026ER40F'],
        # Add more generic mappings
        'GOLDEN_APPLE': ['GLD', 'GOLD_APPLE', 'Golden_Apple_001'],
        'SILVER_RING': ['SLV_RNG', 'SILVER_RING', 'Ring_Silver'],
        'BLUE_JEANS': ['BLU_JNS', 'BLUE_JEANS', 'Jeans_Blue_M']
    }
    
    # Add to existing mappings
    sku_mapper.master_mappings.update(sample_mappings)
    
    flash(f'Added {len(sample_mappings)} sample mappings successfully! Now re-upload your data to see better results.')
    return redirect(url_for('view_mappings'))

@app.route('/clear-mappings')
def clear_mappings():
    """Clear all mappings and reset to defaults"""
    if not sku_mapper_available or not sku_mapper:
        flash('SKU Mapper is not available.')
        return redirect(url_for('dashboard'))
    
    # Reset to default mappings
    sku_mapper.load_master_mappings()
    flash('Mappings reset to defaults.')
    return redirect(url_for('view_mappings'))

@app.route('/ai-chat')
def ai_chat():
    """AI chat interface"""
    if not ai_enabled:
        flash('AI features are not available. Please set GROQ_API_KEY environment variable.')
        return redirect(url_for('dashboard'))
    
    return render_template('ai_chat.html')

@app.route('/mapping-summary')
def mapping_summary():
    """Show intelligent mapping summary"""
    if not sku_mapper_available or not sku_mapper:
        flash('SKU Mapper is not available.')
        return redirect(url_for('dashboard'))
    
    if hasattr(sku_mapper, 'get_mapping_summary'):
        summary = sku_mapper.get_mapping_summary()
        return render_template('mapping_summary.html', summary=summary)
    else:
        flash('Mapping summary not available with current SKU mapper.')
        return redirect(url_for('view_mappings'))

@app.route('/sync-ai-data')
def sync_ai_data():
    """Manually sync uploaded data with AI system"""
    if not ai_enabled:
        flash('AI features are not available.')
        return redirect(url_for('dashboard'))
    
    if not sku_mapper or not hasattr(sku_mapper, 'processed_data') or sku_mapper.processed_data is None:
        flash('No processed data found. Please upload a file first.')
        return redirect(url_for('upload_page'))
    
    try:
        if hasattr(sql_processor, 'sync_with_uploaded_data'):
            success = sql_processor.sync_with_uploaded_data(sku_mapper)
            if success:
                flash('✅ Successfully synced your data with AI system!')
            else:
                flash('❌ Failed to sync data with AI system.')
        else:
            flash('AI sync functionality not available.')
    except Exception as e:
        flash(f'Error syncing data: {str(e)}')
    
    return redirect(url_for('dashboard'))

# API Routes
@app.route('/api/ai-query', methods=['POST'])
def api_ai_query():
    """Process AI query"""
    if not ai_enabled:
        return jsonify({
            'success': False,
            'error': 'AI features are not enabled'
        }), 400
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query cannot be empty'
            }), 400
        
        # Process the query with AI
        result = ai_processor.process_user_query(query)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sql-query', methods=['POST'])
def api_sql_query():
    """Execute SQL query directly"""
    if not ai_enabled:
        return jsonify({
            'success': False,
            'error': 'AI features are not enabled'
        }), 400
    
    try:
        data = request.get_json()
        sql_query = data.get('sql_query', '').strip()
        
        if not sql_query:
            return jsonify({
                'success': False,
                'error': 'SQL query cannot be empty'
            }), 400
        
        # Execute the SQL query
        df, success, error_msg = sql_processor.execute_query(sql_query)
        
        if not success:
            return jsonify({
                'success': False,
                'error': error_msg,
                'sql_query': sql_query
            }), 400
        
        return jsonify({
            'success': True,
            'data': df.to_dict('records'),
            'columns': list(df.columns),
            'row_count': len(df),
            'sql_query': sql_query
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/process-data', methods=['POST'])
def api_process_data():
    """API endpoint for processing data"""
    if not sku_mapper_available or not sku_mapper:
        return jsonify({
            'success': False,
            'error': 'SKU Mapper is not available'
        }), 400
    
    try:
        data = request.get_json()
        
        # Convert JSON data to DataFrame
        df = pd.DataFrame(data.get('data', []))
        
        # Process with SKU mapper
        processed_df = sku_mapper.process_sales_data(df)
        
        # Convert back to JSON
        result = {
            'success': True,
            'data': processed_df.to_dict('records'),
            'summary': generate_processing_results(processed_df)
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/mappings', methods=['GET'])
def get_mappings():
    """Get current SKU mappings"""
    if not sku_mapper_available or not sku_mapper:
        return jsonify({'error': 'SKU Mapper not available'}), 400
    
    return jsonify(sku_mapper.master_mappings)

@app.route('/api/mappings', methods=['POST'])
def add_mapping():
    """Add new SKU mapping"""
    if not sku_mapper_available or not sku_mapper:
        return jsonify({'success': False, 'error': 'SKU Mapper not available'}), 400
    
    try:
        data = request.get_json()
        msku = data.get('msku')
        skus = data.get('skus', [])
        
        if not msku or not skus:
            return jsonify({'success': False, 'error': 'Missing MSKU or SKUs'}), 400
        
        sku_mapper.master_mappings[msku] = skus
        
        return jsonify({'success': True, 'message': 'Mapping added successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/results/<filename>')
def view_results(filename):
    """View processing results"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        df = pd.read_csv(filepath)
        
        # Convert to HTML table for display
        table_html = df.head(100).to_html(classes='table table-striped', table_id='results-table')
        
        results = generate_processing_results(df)
        
        return render_template('results.html', 
                             table_html=table_html,
                             results=results,
                             filename=filename)
    
    except Exception as e:
        flash(f'Error loading results: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed file"""
    try:
        from flask import send_from_directory
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading file: {str(e)}')
        return redirect(url_for('dashboard'))

# Utility Functions
def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_processing_results(df):
    """Generate processing results summary with intelligent mapping info"""
    total_records = len(df)
    
    # Check if MSKU column exists
    if 'MSKU' in df.columns:
        # Handle NaN values and convert to string
        df['MSKU'] = df['MSKU'].fillna('UNCATEGORIZED_UNKNOWN').astype(str)
        mapped_records = len(df[~df['MSKU'].str.startswith('UNCATEGORIZED_', na=False)])
        unmapped_records = total_records - mapped_records
        
        # Get top products
        top_products = df['MSKU'].value_counts().head(10).to_dict()
        
        # Get intelligent category insights
        category_insights = {}
        for category, count in df['MSKU'].value_counts().items():
            if not category.startswith('UNCATEGORIZED_'):
                category_type = 'Auto-Generated'
                if 'BRAND' in category:
                    category_type = 'Brand-Based'
                elif 'NUMERIC' in category:
                    category_type = 'Pattern-Based'
                elif 'CATEGORY' in category:
                    category_type = 'Product-Based'
                
                category_insights[category] = {
                    'count': count,
                    'type': category_type,
                    'percentage': round((count / total_records) * 100, 1)
                }
    else:
        mapped_records = 0
        unmapped_records = total_records
        top_products = {}
        category_insights = {}
    
    # Calculate success rate
    success_rate = (mapped_records / total_records * 100) if total_records > 0 else 0
    
    return {
        'total_records': total_records,
        'mapped_records': mapped_records,
        'unmapped_records': unmapped_records,
        'success_rate': success_rate,
        'top_products': top_products,
        'category_insights': category_insights,
        'is_intelligent_mapping': True
    }

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500

# Health Check
@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'features': {
            'sku_mapper': sku_mapper_available,
            'ai_features': ai_enabled,
            'baserow': baserow_available
        },
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting Warehouse Management System...")
    print(f"📊 SKU Mapper Available: {sku_mapper_available}")
    print(f"🗄️  Baserow Available: {baserow_available}")
    print(f"🤖 AI Features Available: {ai_enabled}")
    
    if not ai_enabled:
        print("💡 To enable AI features:")
        print("   1. Get a free API key from: https://console.groq.com/")
        print("   2. Set environment variable: export GROQ_API_KEY=your_key_here")
        print("   3. Or add it to your .env file")
    
    print(f"\n🌐 Access your WMS at:")
    print(f"   📊 Dashboard: http://127.0.0.1:5001/")
    print(f"   📤 Upload Data: http://127.0.0.1:5001/upload")
    print(f"   🗺️  Manage Mappings: http://127.0.0.1:5001/mappings")
    if ai_enabled:
        print(f"   🤖 AI Assistant: http://127.0.0.1:5001/ai-chat")
    print(f"   🔗 Quick Sample Mappings: http://127.0.0.1:5001/add-sample-mappings")
    
    app.run(debug=True, host='0.0.0.0', port=5001)