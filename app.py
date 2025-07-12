from flask import Flask, request, jsonify
import requests
import os
import unicodedata
import re

print(">>> Iniciando app.py")

app = Flask(__name__)

LOCAWEB_TOKEN = os.getenv("LOCAWEB_TOKEN")
EMAIL_FROM = os.getenv("EMAIL_FROM", "luna@fausp.edu.br")  # Valor padrão caso não esteja definido

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
    
    print(f">>> Enviando email para: {email}")
    print(f">>> Dados do email: {data}")
    
    response = requests.post(url, headers=headers, json=data)
    return response.status_code, response.text

def normalizar(texto):
    """Normaliza texto removendo acentos e convertendo para minúsculas"""
    if not texto:
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()

def extrair_email_do_lead(lead):
    """Extrai email do lead com múltiplas estratégias"""
    email = None
    
    # Estratégia 1: Buscar em custom_fields
    if 'custom_fields' in lead:
        for field in lead['custom_fields']:
            nome_campo = normalizar(field.get('name', ''))
            print(f">>> Analisando campo: '{field.get('name')}' -> normalizado: '{nome_campo}'")
            
            # Buscar por variações de email
            if any(palavra in nome_campo for palavra in ['email', 'e-mail', 'e_mail', 'mail']):
                valores = field.get('values', [])
                if valores and isinstance(valores, list) and len(valores) > 0:
                    email_value = valores[0].get('value')
                    if email_value and '@' in email_value:  # Validação básica de email
                        email = email_value
                        print(f">>> Email encontrado em custom_fields: {email}")
                        break
    
    # Estratégia 2: Buscar diretamente no lead (caso o Kommo envie assim)
    if not email and 'email' in lead:
        email = lead['email']
        print(f">>> Email encontrado diretamente no lead: {email}")
    
    return email

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

        # Verificar se há leads no payload
        if 'leads' not in data or not data['leads']:
            return jsonify({"error": "Nenhum lead encontrado no payload"}), 400

        lead = data['leads'][0]  # Pegar o primeiro lead
        lead_id = lead.get('id')
        nome = lead.get('name', 'Contato')
        
        # Extrair email usando função melhorada
        email = extrair_email_do_lead(lead)

        print(f">>> Lead ID: {lead_id} (tipo: {type(lead_id)})")
        print(f">>> Nome: {nome}")
        print(f">>> Email extraído: {email}")
        print(f">>> EMAIL_FROM configurado: {EMAIL_FROM}")
        print(f">>> LOCAWEB_TOKEN configurado: {'Sim' if LOCAWEB_TOKEN else 'Não'}")

        # Validações
        if not lead_id:
            return jsonify({"error": "Lead sem ID"}), 400
            
        if not email:
            return jsonify({"error": "Email não encontrado no lead", "lead_data": lead}), 400
            
        if not LOCAWEB_TOKEN:
            return jsonify({"error": "Token da LocaWeb não configurado"}), 500

        # Verificar se já foi processado
        if lead_ja_processado(lead_id):
            return jsonify({"message": "Lead já processado"}), 200

        # Enviar email
        status, resposta = enviar_email_locaweb(nome, email)
        print(f">>> Status do envio: {status}")
        print(f">>> Resposta da LocaWeb: {resposta}")

        if status in [200, 202]:
            registrar_lead(lead_id)
            return jsonify({
                "message": "E-mail enviado com sucesso",
                "lead_id": lead_id,
                "email": email,
                "status": status
            }), 200
        else:
            return jsonify({
                "error": "Erro ao enviar e-mail", 
                "detalhes": resposta,
                "status": status
            }), 500

    except Exception as e:
        print(f">>> Erro no processamento: {str(e)}")
        return jsonify({"error": "Erro no processamento", "mensagem": str(e)}), 500

if __name__ == "__main__":
    print(">>> Rodando servidor Flask...")
    print(f">>> EMAIL_FROM: {EMAIL_FROM}")
    print(f">>> LOCAWEB_TOKEN: {'Configurado' if LOCAWEB_TOKEN else 'NÃO CONFIGURADO'}")
    app.run(host='0.0.0.0', port=5000, debug=True)