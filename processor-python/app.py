import os
import json
import secrets
import requests
import bcrypt
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configurazione del database tramite variabili d'ambiente con fallback per Docker
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),  # 'db' è il nome del servizio nel docker-compose.yml
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),  # Inserisci la password impostata nel docker-compose
    'database': os.getenv('DB_NAME', 'synccore_db'),
    'port': int(os.getenv('DB_PORT', 3306))
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")

# --- HELPER: Recupera l'API Key reale dell'utente dal DB ---
def resolve_api_key(api_key, employee_id, domain):
    if api_key:
        return api_key
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT api_key FROM users 
            WHERE (employee_id = %s AND employee_id IS NOT NULL AND employee_id != '') 
               OR (domain = %s AND domain IS NOT NULL AND domain != '')
            LIMIT 1
        """
        cursor.execute(query, (employee_id, domain))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            return row['api_key']
    except Exception as e:
        print(f"[Python Error] Errore risoluzione API Key: {e}")
    
    return "unassigned_key"

@app.route('/api/submissions', methods=['GET'])
def get_submissions():
    api_key = request.headers.get('X-API-Key')

    if not api_key:
        return jsonify({"error": "Chiave API mancante"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE api_key = %s", (api_key,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "Chiave API non valida"}), 403

        query = """
            SELECT id, name, email, message, created_at 
            FROM submissions 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """
        cursor.execute(query, (user['id'],))
        submissions = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({"submissions": submissions}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- REGISTRAZIONE DINAMICA ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    domain = data.get('domain', '').strip().lower()
    employee_id = data.get('employee_id', '').strip()

    if not email or not password:
        return jsonify({"error": "Email e Password sono obbligatorie"}), 400

    if domain:
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    else:
        domain = None

    if not employee_id:
        employee_id = None

    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    new_api_key = f"sk_live_{secrets.token_hex(16)}"

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO users (email, password_hash, api_key, domain, employee_id) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (email, hashed_password, new_api_key, domain, employee_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message": "Registrazione completata con successo!",
            "email": email,
            "api_key": new_api_key
        }), 201

    except mysql.connector.Error as err:
        if err.errno == 1062:
            return jsonify({"error": "Email, Dominio o Matricola già registrati nel sistema."}), 400
        return jsonify({"error": str(err)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    identifier = data.get('identifier', '').strip()
    password = data.get('password', '').strip()
    auth_type = data.get('auth_type', 'email')

    if not identifier or not password:
        return jsonify({"error": "Identificativo e Password sono obbligatori"}), 400

    if auth_type == 'domain':
        identifier = identifier.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT id, email, password_hash, api_key, domain, employee_id 
            FROM users 
            WHERE email = %s OR domain = %s OR employee_id = %s
        """
        cursor.execute(query, (identifier, identifier, identifier))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return jsonify({
                    "status": "success",
                    "email": user['email'],
                    "domain": user['domain'],
                    "employee_id": user['employee_id'],
                    "api_key": user['api_key']
                }), 200

        return jsonify({"error": "Credenziali errate (Identificativo o Password non validi)"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-lead', methods=['POST'])
def test_lead():
    data = request.get_json() or {}
    api_key = data.get('api_key')

    if not api_key:
        return jsonify({"error": "API Key mancante"}), 400

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    name = "Mario Rossi (Test)"
    email = "mario.test@azienda.it"
    message = "Richiesta di prova inviata direttamente dalla Dashboard per verificare l'integrazione AI."
    status = "processed"
    
    ai_analysis = json.dumps({
        "intento": "Richiesta di Test / Demo",
        "priorita": "Media",
        "sintesi": "Lead di prova generato automaticamente dal sistema SyncCore.",
        "bozza_risposta": "Grazie per aver effettuato il test della piattaforma SyncCore!"
    })

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO events (api_key, timestamp, name, email, message, status, ai_analysis) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (api_key, timestamp, name, email, message, status, ai_analysis))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Lead di prova inserito con successo!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- PROCESS INGESTION ---
@app.route('/process', methods=['POST'])
def process_data():
    api_key = request.headers.get("X-API-Key", "")
    employee_id = request.headers.get("X-Employee-ID", "")
    domain = request.headers.get("X-Domain", "")
    
    data = request.get_json() or {}
    
    if not data:
        return jsonify({"error": "Payload vuoto"}), 400

    actual_api_key = resolve_api_key(api_key, employee_id, domain)

    name = data.get("name", "N/A")
    email = data.get("email", "N/A")
    message = data.get("message", "")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    prompt = f"""
Sei un assistente AI B2B. Analizza la seguente richiesta ed estrai le informazioni in formato JSON:
Nome: {name}
Email: {email}
Messaggio: "{message}"

Rispondi ESCLUSIVAMENTE in JSON con le chiavi: "intento", "priorita", "sintesi", "bozza_risposta".
"""

    status = "processed"
    ai_analysis_str = "{}"

    try:
        response = requests.post(OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=5)
        raw_ai = response.json().get("response", "{}")
        ai_analysis_str = raw_ai if isinstance(raw_ai, str) else json.dumps(raw_ai)
    except Exception as e:
        status = "fallback_no_ai"
        ai_analysis_str = json.dumps({"error": f"AI Engine non raggiungibile: {str(e)}"})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO events (api_key, timestamp, name, email, message, status, ai_analysis) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (actual_api_key, timestamp, name, email, message, status, ai_analysis_str))
        conn.commit()
        event_id = cursor.lastrowid
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Errore Database MySQL: {str(e)}"}), 500

    return jsonify({"status": "success", "db_id": event_id, "api_key": actual_api_key, "raw_input": data}), 200

@app.route('/api/events', methods=['GET'])
def get_events():
    api_key = request.args.get("api_key", "")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM events WHERE api_key = %s ORDER BY id DESC LIMIT 50", (api_key,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({"error": f"Errore Database MySQL: {str(e)}"}), 500

if __name__ == '__main__':
    print("[Python Engine] Server attivo su 0.0.0.0:5000...")
    # ✅ host='0.0.0.0' permette l'ascolto da tutte le interfacce di rete del container
    app.run(host='0.0.0.0', port=5000, debug=True)