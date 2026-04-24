from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import re
import os
import uuid
import tempfile

app = Flask(__name__)
CORS(app)

# ==================== دوال استخراج البيانات ====================

def extract_values_from_text(text):
    """استخراج القيم الطبية من النص"""
    data = {}
    
    patterns = {
        'age': r'(?:age|عمر|Age)[\s:]*(\d+)',
        'glucose': r'(?:glucose|سكر|Glucose)[\s:]*(\d+(?:\.\d+)?)',
        'systolic_bp': r'(?:systolic|الضغط الانقباضي)[\s:]*(\d+(?:\.\d+)?)',
        'diastolic_bp': r'(?:diastolic|الضغط الانبساطي)[\s:]*(\d+(?:\.\d+)?)',
        'ldl': r'(?:ldl|LDL)[\s:]*(\d+(?:\.\d+)?)',
        'genetic_risk_score': r'(?:genetic risk|الخطر الوراثي)[\s:]*(\d+(?:\.\d+)?)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                val = match.group(1)
                data[key] = float(val) if '.' in val else int(val)
            except:
                pass
    
    if re.search(r'male|ذكر|Male', text, re.IGNORECASE):
        data['gender'] = 'Male'
    elif re.search(r'female|انثى|Female', text, re.IGNORECASE):
        data['gender'] = 'Female'
    
    disease_match = re.search(r'(?:genetic disease|مرض وراثي|Diagnosis)[\s:]*([A-Za-z\s]+)', text, re.IGNORECASE)
    if disease_match:
        data['genetic_disease'] = disease_match.group(1).strip()
    
    return data

def text_to_dataset(text):
    """تحويل النص إلى DataFrame"""
    data = extract_values_from_text(text)
    
    default_values = {
        'person_id': f"P{np.random.randint(100000, 999999)}",
        'family_id': f"F{np.random.randint(100000, 999999)}",
        'age': 40,
        'gender': 'Unknown',
        'genetic_risk_score': 0.3,
        'genetic_disease': 'None',
        'glucose': 0.0,
        'systolic_bp': 0.0,
        'diastolic_bp': 0.0,
        'ldl': 0.0
    }
    
    row = {}
    for col in default_values:
        if col in data and data[col] is not None:
            row[col] = data[col]
        else:
            row[col] = default_values[col]
    
    return row

def extract_text_from_file(content, filename):
    """استخراج النص من محتوى الملف"""
    ext = filename.split('.')[-1].lower()
    text = ""
    
    try:
        if ext in ['txt']:
            text = content.decode('utf-8')
        
        elif ext in ['pdf']:
            try:
                import io
                import pdfplumber
                pdf_file = io.BytesIO(content)
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except ImportError:
                text = "PDF support requires pdfplumber"
        
        elif ext in ['xlsx', 'xls']:
            import io
            df = pd.read_excel(io.BytesIO(content))
            text = df.to_string()
        
        elif ext in ['docx']:
            try:
                import io
                import docx
                doc_file = io.BytesIO(content)
                doc = docx.Document(doc_file)
                text = "\n".join([p.text for p in doc.paragraphs])
            except ImportError:
                text = "DOCX support requires python-docx"
        
        elif ext in ['jpg', 'png', 'jpeg']:
            try:
                from PIL import Image
                import pytesseract
                import io
                img = Image.open(io.BytesIO(content))
                text = pytesseract.image_to_string(img, lang='eng+ara')
            except ImportError:
                text = "Image support requires Pillow and pytesseract"
    
    except Exception as e:
        text = f"Error reading file: {str(e)}"
    
    return text

# ==================== API Routes ====================

@app.route('/', methods=['GET'])
def home():
    """الصفحة الرئيسية"""
    return jsonify({
        'name': 'Medical Data Extractor API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'POST /extract': 'Upload file and extract medical data',
            'GET /health': 'Health check'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/extract', methods=['POST'])
def extract():
    """رفع ملف واستخراج البيانات"""
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    try:
        # قراءة محتوى الملف
        content = file.read()
        
        # استخراج النص
        text = extract_text_from_file(content, file.filename)
        
        if not text or len(text) < 10:
            return jsonify({'success': False, 'error': 'Could not extract text from file'}), 400
        
        # تحويل إلى dataset
        data = text_to_dataset(text)
        
        return jsonify({
            'success': True,
            'data': [data],
            'columns': list(data.keys()),
            'filename': file.filename,
            'message': 'Data extracted successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Vercel Handler ====================

def handler(event, context):
    """Vercel serverless function handler"""
    return app(event, context)

# للتشغيل المحلي
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)