from flask import Flask, request, jsonify
import requests
import os

print(">>> Iniciando app.py")  # Teste de vida

app = Flask(__name__)

LOCAWEB_TOKEN = "SEU_TOKEN_DA_LOCAWEB"
EMAIL_FROM = "seuemail@seudominio.com.br"
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
    url = "https://emailmarketing.api.locaweb.com.br/v1/messages/send"
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

@app.route("/kommo-webhook", methods=["POST"])
def receber_webhook():
    if request.is_json:
     data = request.form.to_dict(flat=False)


    lead = data.get('leads', [{}])[0]
    lead_id = lead.get('id')
    nome = lead.get('name', 'Contato')
    email = None

    if 'custom_fields' in lead:
        for field in lead['custom_fields']:
            if 'email' in field.get('name', '').lower():
                email = field.get('values', [{}])[0].get('value')
                break

    if not email or not lead_id:
        return jsonify({"error": "Lead sem e-mail ou ID"}), 400

    if lead_ja_processado(lead_id):
        return jsonify({"message": "Lead já processado"}), 200

    status, resposta = enviar_email_locaweb(nome, email)

    if status in [200, 202]:
        registrar_lead(lead_id)
        return jsonify({"message": "E-mail enviado com sucesso"}), 200
    else:
        return jsonify({"error": "Erro ao enviar e-mail", "detalhes": resposta}), 500

if __name__ == "__main__":
    print(">>> Rodando servidor Flask...")
    app.run(port=5000, debug=True)
