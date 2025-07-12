from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route("/kommo-webhook", methods=["POST"])
def receber_webhook():
    data = request.get_json()

    print("Recebido:", data)

    leads = data.get("leads", [])

    if not leads:
        return jsonify({"error": "Nenhum lead encontrado"}), 400

    for lead in leads:
        email = None
        custom_fields = lead.get("custom_fields", [])
        for field in custom_fields:
            if field.get("name") == "E-mail":
                valores = field.get("values", [])
                if valores:
                    email = valores[0].get("value")
                    break

        if not email or not lead.get("id"):
            return jsonify({"error": "Lead sem ID ou email"}), 400

        print(f"Enviando e-mail para {email}...")

        resultado = enviar_email(email)
        print("Resultado envio:", resultado)

        if resultado.status_code != 200:
            return jsonify({
                "error": "Erro ao enviar e-mail",
                "status": resultado.status_code,
                "details": resultado.text
            }), 500

    return jsonify({"status": "E-mails enviados com sucesso"}), 200


def enviar_email(destinatario):
    url = f"https://api.emailmarketing.locaweb.com.br/v1/accounts/{os.getenv('LOCAWEB_ACCOUNT_ID')}/messages"

    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": os.getenv("LOCAWEB_TOKEN")
    }

    payload = {
        "subject": "Obrigado pelo cadastro!",
        "from": os.getenv("EMAIL_FROM"),
        "to": [destinatario],
        "html": "<h1>Obrigado por se cadastrar!</h1><p>Entraremos em contato em breve.</p>"
    }

    response = requests.post(url, headers=headers, json=payload)
    return response


if __name__ == "__main__":
    app.run(debug=True)
