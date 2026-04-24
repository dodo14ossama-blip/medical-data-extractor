from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import random
import os
import tempfile

app = Flask(__name__)
CORS(app)

def extract_values(text):
    """استخراج القيم الطبية من النص"""
    data = {
        'age': 40,
        'glucose': 0,
        'systolic_bp': 0,
        'diastolic_bp': 0,
        'ldl': 0,
        'hdl': 0,
        'triglycerides': 0,
        'genetic_risk_score': 0.3,
        'gender': 'Unknown',
        'genetic_disease': 'None'
    }
    
    # استخراج العمر
    age_match = re.search(r'(?:age|عمر|Age)[\s:]*(\d+)', text, re.IGNORECASE)
    if age_match:
        data['age'] = int(age_match.group(1))
    
    # استخراج السكر
    glucose_match = re.search(r'(?:glucose|سكر|Glucose|blood sugar)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if glucose_match:
        data['glucose'] = float(glucose_match.group(1))
    
    # استخراج الضغط الانقباضي
    sbp_match = re.search(r'(?:systolic|Systolic|الضغط الانقباضي)[\s:]*(\d+)', text, re.IGNORECASE)
    if sbp_match:
        data['systolic_bp'] = int(sbp_match.group(1))
    
    # استخراج الضغط الانبساطي
    dbp_match = re.search(r'(?:diastolic|Diastolic|الضغط الانبساطي)[\s:]*(\d+)', text, re.IGNORECASE)
    if dbp_match:
        data['diastolic_bp'] = int(dbp_match.group(1))
    
    # استخراج LDL
    ldl_match = re.search(r'(?:ldl|LDL)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if ldl_match:
        data['ldl'] = float(ldl_match.group(1))
    
    # استخراج HDL
    hdl_match = re.search(r'(?:hdl|HDL)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if hdl_match:
        data['hdl'] = float(hdl_match.group(1))
    
    # استخراج الدهون الثلاثية
    tri_match = re.search(r'(?:triglycerides|Triglycerides|الدهون الثلاثية)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if tri_match:
        data['triglycerides'] = float(tri_match.group(1))
    
    # استخراج المخاطر الوراثية
    risk_match = re.search(r'(?:genetic risk|Genetic Risk|الخطر الوراثي)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if risk_match:
        data['genetic_risk_score'] = float(risk_match.group(1))
    
    # استخراج الجنس
    if re.search(r'male|ذكر|Male', text, re.IGNORECASE):
        data['gender'] = 'Male'
    elif re.search(r'female|انثى|Female', text, re.IGNORECASE):
        data['gender'] = 'Female'
    
    # استخراج الأمراض الوراثية
    disease_match = re.search(r'(?:genetic disease|Genetic Disease|مرض وراثي|Diagnosis)[\s:]*([A-Za-z\s]+)', text, re.IGNORECASE)
    if disease_match:
        data['genetic_disease'] = disease_match.group(1).strip()
    
    return data

def extract_text_from_file(content, filename):
    """استخراج النص من الملف حسب نوعه"""
    ext = filename.split('.')[-1].lower()
    text = ""
    
    if ext == 'txt':
        text = content.decode('utf-8')
    
    elif ext == 'pdf':
        try:
            import io
            import pdfplumber
            pdf = pdfplumber.open(io.BytesIO(content))
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except ImportError:
            text = "[PDF text extraction requires pdfplumber]"
    
    elif ext in ['xlsx', 'xls']:
        try:
            import io
            import pandas as pd
            df = pd.read_excel(io.BytesIO(content))
            text = df.to_string()
        except ImportError:
            text = "[Excel extraction requires pandas]"
    
    elif ext == 'docx':
        try:
            import io
            import docx
            doc = docx.Document(io.BytesIO(content))
            text = "\n".join([p.text for p in doc.paragraphs])
        except ImportError:
            text = "[Word extraction requires python-docx]"
    
    elif ext in ['jpg', 'png', 'jpeg']:
        try:
            from PIL import Image
            import pytesseract
            import io
            img = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(img, lang='eng+ara')
        except ImportError:
            text = "[OCR requires Pillow and pytesseract]"
    
    else:
        text = str(content)
    
    return text

def calculate_risk(data):
    """حساب نسبة الخطورة بناءً على البيانات"""
    risk = 0.0
    
    # العمر (25% من المخاطر)
    if data['age'] > 60:
        risk += 0.25
    elif data['age'] > 40:
        risk += 0.125
    
    # السكر (20% من المخاطر)
    if data['glucose'] > 200:
        risk += 0.2
    elif data['glucose'] > 140:
        risk += 0.1
    
    # الضغط (15% من المخاطر)
    if data['systolic_bp'] > 160:
        risk += 0.15
    elif data['systolic_bp'] > 140:
        risk += 0.075
    
    # LDL (15% من المخاطر)
    if data['ldl'] > 190:
        risk += 0.15
    elif data['ldl'] > 130:
        risk += 0.075
    
    # المخاطر الوراثية (15% من المخاطر)
    risk += data['genetic_risk_score'] * 0.15
    
    # HDL (5% من المخاطر) - عكسي
    if data['hdl'] > 60:
        risk -= 0.05
    elif data['hdl'] < 40:
        risk += 0.05
    
    # الدهون الثلاثية (5% من المخاطر)
    if data['triglycerides'] > 200:
        risk += 0.05
    
    return max(0, min(risk, 0.95))

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'running',
        'name': 'Medical Data Extractor API',
        'version': '4.0.0',
        'endpoints': {
            'GET /': 'API information',
            'GET /health': 'Health check',
            'POST /extract': 'Upload file and extract medical data',
            'POST /predict': 'Extract and predict risk'
        },
        'supported_files': {
            'text': '.txt',
            'pdf': '.pdf (requires pdfplumber)',
            'excel': '.xlsx, .xls (requires pandas)',
            'word': '.docx (requires python-docx)',
            'images': '.jpg, .png (requires Pillow + pytesseract)'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/extract', methods=['POST'])
def extract_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    try:
        content = file.read()
        text = extract_text_from_file(content, file.filename)
        data = extract_values(text)
        
        data['person_id'] = f"P{random.randint(100000, 999999)}"
        data['family_id'] = f"F{random.randint(100000, 999999)}"
        
        return jsonify({
            'success': True,
            'data': data,
            'filename': file.filename,
            'extracted_text_length': len(text)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict_risk():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    try:
        content = file.read()
        text = extract_text_from_file(content, file.filename)
        data = extract_values(text)
        
        risk_score = calculate_risk(data)
        
        if risk_score < 0.3:
            risk_category = "Low Risk"
            risk_emoji = "🟢"
            risk_color = "green"
            risk_description = "Low probability of genetic diseases. Continue healthy lifestyle."
        elif risk_score < 0.6:
            risk_category = "Medium Risk"
            risk_emoji = "🟡"
            risk_color = "orange"
            risk_description = "Moderate probability - consider genetic counseling and lifestyle changes."
        else:
            risk_category = "High Risk"
            risk_emoji = "🔴"
            risk_color = "red"
            risk_description = "High probability - genetic testing recommended. Consult a specialist."
        
        recommendations = []
        if risk_score > 0.5:
            if data['glucose'] > 140:
                recommendations.append("Monitor blood glucose regularly")
            if data['systolic_bp'] > 140:
                recommendations.append("Monitor blood pressure and consider medication")
            if data['ldl'] > 130:
                recommendations.append("Consider cholesterol-lowering diet and medication")
            if data['genetic_risk_score'] > 0.5:
                recommendations.append("Schedule genetic counseling appointment")
        
        if not recommendations:
            recommendations = ["Continue healthy lifestyle", "Annual checkup recommended"]
        
        data['person_id'] = f"P{random.randint(100000, 999999)}"
        data['family_id'] = f"F{random.randint(100000, 999999)}"
        
        return jsonify({
            'success': True,
            'data': data,
            'risk_assessment': {
                'score': round(risk_score, 3),
                'percentage': f"{risk_score*100:.1f}%",
                'category': risk_category,
                'emoji': risk_emoji,
                'color': risk_color,
                'description': risk_description,
                'recommendations': recommendations
            },
            'filename': file.filename
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

handler = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
