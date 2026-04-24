from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import random

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

def calculate_risk(data):
    """حساب نسبة الخطورة بناءً على البيانات"""
    risk = 0.0
    
    # العمر (30% من المخاطر)
    if data['age'] > 60:
        risk += 0.3
    elif data['age'] > 40:
        risk += 0.15
    
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
    
    # المخاطر الوراثية (20% من المخاطر)
    risk += data['genetic_risk_score'] * 0.2
    
    return min(risk, 0.95)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'running',
        'name': 'Medical Data Extractor API',
        'version': '3.0.0',
        'endpoints': {
            'GET /': 'API information',
            'GET /health': 'Health check',
            'POST /extract': 'Upload file and extract medical data',
            'POST /predict': 'Extract and predict risk'
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
        text = content.decode('utf-8') if file.filename.endswith('.txt') else str(content)
        data = extract_values(text)
        
        data['person_id'] = f"P{random.randint(100000, 999999)}"
        data['family_id'] = f"F{random.randint(100000, 999999)}"
        
        return jsonify({'success': True, 'data': data, 'filename': file.filename})
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
        text = content.decode('utf-8') if file.filename.endswith('.txt') else str(content)
        data = extract_values(text)
        
        risk_score = calculate_risk(data)
        
        if risk_score < 0.3:
            risk_category = "Low Risk"
            risk_emoji = "🟢"
            risk_description = "Low probability of genetic diseases"
        elif risk_score < 0.6:
            risk_category = "Medium Risk"
            risk_emoji = "🟡"
            risk_description = "Moderate probability - consider genetic counseling"
        else:
            risk_category = "High Risk"
            risk_emoji = "🔴"
            risk_description = "High probability - genetic testing recommended"
        
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
                'description': risk_description
            },
            'filename': file.filename
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

handler = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
