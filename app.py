from flask import Flask, request, jsonify
import requests
import os

print(">>> Iniciando app.py")  # Teste de vida

app = Flask(__name__)

LOCAWEB_TOKEN = "3NqLaUxVGAL5pBzsdY5esprtWWzVxBgqs8QH2iTxBtEr"
EMAIL_FROM = "luna@fausp.edu.br"
LEADS_REGISTRADOS = "processed_leads.txt"

def lead_ja_processado(lead_id):
    if not os.path.exists(LEADS_REGISTRADOS):
        return False
    with open(LEADS_REGISTRADOS, 'r') as f:
        return str(lead_id) in f.read()

def registrar_lead(lead_id):
    with open(LEADS_REGISTRADOS, 'a') as f:
        f.write(f"{lead_id}\n")

def enviar_email_locaweb(nome, email):
    url = "https://emailmarketing.api.locaweb.com.br/v1"
    headers = {
        "Authorization": f"Token {LOCAWEB_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "from": EMAIL_FROM,
        "to": email,
        "subject": "Bem-vindo!",
        "html": f"<p>Olá {nome}, obrigado por se conectar conosco!</p>"
    }

    response = requests.post(url, headers=headers, json=data)
    return response.status_code, response.text

@app.route('/')
def home():
    return 'API Kommo-Locaweb online!'

@app.route('/kommo-webhook', methods=["POST"])
def receber_webhook():
    if not request.is_json:
        return jsonify({"error": "Conteúdo não é JSON"}), 400

    try:
        data = request.get_json()

        lead = data.get('leads', [{}])[0]
        lead_id = lead.get('id')
        nome = lead.get('name', 'Contato')
        email = None

        if 'custom_fields' in lead:
            for field in lead['custom_fields']:
                if 'email' in field.get('name', '').lower():
                    email = field.get('values', [{}])[0].get('value')

        if nome and email:
            status, resposta = enviar_email_locaweb(nome, email)
            return {'status': 'Webhook recebido com sucesso'}, 200
        else:
            return jsonify({"error": "Dados incompletos"}), 400

    except Exception as e:
        return jsonify({"error": "Erro no processamento", "mensagem": str(e)}), 500
