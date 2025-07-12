from flask import Flask, request, jsonify
import requests
import os

print(">>> Iniciando app.py")

app = Flask(__name__)

# Carrega variáveis de ambiente (usadas no Render.com)
LOCAWEB_TOKEN = os.getenv("LOCAWEB_TOKEN")
EMAIL_FROM = os.getenv("EMAIL_FROM")

# Arquivo local para registrar os leads já processados
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
    url = "https://emailmarketing.locaweb.com.br/api"
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
        print(">>> Dados recebidos:", data)

        leads = data.get('leads', [])
        if not leads:
            return jsonify({"error": "Nenhum lead fornecido"}), 400

        lead = leads[0]
        print(">>> Lead recebido:", lead)

        lead_id = lead.get('id')
        nome = lead.get('name', 'Contato')
        email = None

        print(">>> Lead ID:", lead_id)
        print(">>> Nome:", nome)
        print(">>> Custom Fields:", lead.get('custom_fields', []))

        if 'custom_fields' in lead:
            for field in lead['custom_fields']:
                if 'email' in field.get('name', '').lower():
                    email = field.get('values', [{}])[0].get('value')

        print(">>> Email:", email)

        if not lead_id or not email:
            return jsonify({"error": "Lead sem ID ou email"}), 400

        if lead_ja_processado(lead_id):
            return jsonify({"message": "Lead já processado"}), 200

        status, resposta = enviar_email_locaweb(nome, email)

        if status in [200, 202]:
            registrar_lead(lead_id)
            return jsonify({"message": "E-mail enviado com sucesso"}), 200
        else:
            return jsonify({"error": "Erro ao enviar e-mail", "detalhes": resposta}), 500

    except Exception as e:
        print(">>> Erro no processamento:", str(e))
        return jsonify({"error": "Erro no processamento", "mensagem": str(e)}), 500

if __name__ == "__main__":
    print(">>> Rodando servidor Flask...")
    app.run(port=5000, debug=True)