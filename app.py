from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import logging
import hashlib
import hmac
from dotenv import load_dotenv
from datetime import datetime

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configurações da API
LOCAWEB_BASE_URL = "https://api.smtplw.com.br/v1"
LOCAWEB_TOKEN = os.getenv("LOCAWEB_TOKEN")
LOCAWEB_ACCOUNT_ID = os.getenv("LOCAWEB_ACCOUNT_ID")
EMAIL_FROM = os.getenv("EMAIL_FROM")
KOMMO_SECRET = os.getenv("KOMMO_WEBHOOK_SECRET", "")

def validar_webhook_kommo(data, signature):
    """
    Valida a assinatura do webhook do Kommo para garantir autenticidade
    """
    if not KOMMO_SECRET or not signature:
        logger.warning("Webhook sem validação de assinatura configurada")
        return True  # Permitir se não houver secret configurado
    
    try:
        expected_signature = hmac.new(
            KOMMO_SECRET.encode('utf-8'),
            str(data).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Erro na validação do webhook: {str(e)}")
        return False

def extrair_email_lead(lead):
    """
    Extrai o email do lead a partir dos custom_fields
    """
    try:
        custom_fields = lead.get("custom_fields", [])
        
        # Procurar por diferentes variações do campo email
        email_field_names = ["E-mail", "Email", "email", "EMAIL", "e-mail"]
        
        for field in custom_fields:
            field_name = field.get("name", "")
            if field_name in email_field_names:
                valores = field.get("values", [])
                if valores and len(valores) > 0:
                    email = valores[0].get("value", "").strip()
                    if email and "@" in email:
                        return email
        
        # Se não encontrou nos custom_fields, tentar no campo direto
        if "email" in lead:
            return lead["email"]
            
        return None
    except Exception as e:
        logger.error(f"Erro ao extrair email do lead: {str(e)}")
        return None

def enviar_email_marketing(destinatario, lead_data=None):
    """
    Envia email através da API do Email Marketing Locaweb
    """
    try:
        url = f"{LOCAWEB_BASE_URL}/messages"
        
        headers = {
            "Content-Type": "application/json",
            "X-Auth-Token": LOCAWEB_TOKEN
        }
        
        # Personalizar conteúdo baseado nos dados do lead
        nome_lead = "Cliente"
        if lead_data:
            nome_lead = lead_data.get("name", "Cliente")
        
        payload = {
            "subject": "Obrigado pelo seu interesse!",
            "from": EMAIL_FROM,
            "to": [destinatario],
            "html": f"""
            <html>
            <body>
                <h1>Olá {nome_lead}!</h1>
                <p>Obrigado por se cadastrar em nosso sistema.</p>
                <p>Nossa equipe entrará em contato em breve para dar continuidade ao seu atendimento.</p>
                <br>
                <p>Atenciosamente,<br>
                Equipe de Atendimento</p>
            </body>
            </html>
            """,
            "text": f"Olá {nome_lead}! Obrigado por se cadastrar. Nossa equipe entrará em contato em breve."
        }
        
        logger.info(f"Enviando email para: {destinatario}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"Email enviado com sucesso para {destinatario}")
            return {"success": True, "message": "Email enviado com sucesso"}
        else:
            logger.error(f"Erro ao enviar email: {response.status_code} - {response.text}")
            return {
                "success": False, 
                "error": f"Erro da API: {response.status_code}",
                "details": response.text
            }
            
    except requests.exceptions.Timeout:
        logger.error("Timeout ao enviar email")
        return {"success": False, "error": "Timeout na requisição"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de conexão ao enviar email: {str(e)}")
        return {"success": False, "error": f"Erro de conexão: {str(e)}"}
    except Exception as e:
        logger.error(f"Erro inesperado ao enviar email: {str(e)}")
        return {"success": False, "error": f"Erro inesperado: {str(e)}"}

@app.route("/", methods=["POST"])
def health_check():
    """
    Endpoint de verificação de saúde da aplicação
    """
    return jsonify({
        "status": "online",
        "service": "Kommo-Locaweb Integration",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }), 200

@app.route("/kommo-webhook", methods=["POST"])
def receber_webhook():
    """
    Endpoint principal para receber webhooks do Kommo CRM
    """
    try:
        # Obter dados da requisição
        data = request.get_json()
        signature = request.headers.get("X-Kommo-Signature", "")
        
        logger.info(f"Webhook recebido: {datetime.now().isoformat()}")
        logger.debug(f"Dados recebidos: {data}")
        
        # Validar dados de entrada
        if not data:
            logger.error("Dados vazios recebidos no webhook")
            return jsonify({"error": "Dados não fornecidos"}), 400
        
        # Validar assinatura do webhook (se configurada)
        if not validar_webhook_kommo(data, signature):
            logger.error("Assinatura do webhook inválida")
            return jsonify({"error": "Webhook não autorizado"}), 401
        
        # Processar leads
        leads = data.get("leads", [])
        
        if not leads:
            logger.warning("Nenhum lead encontrado no webhook")
            return jsonify({"warning": "Nenhum lead encontrado"}), 200
        
        resultados = []
        emails_enviados = 0
        erros = []
        
        for i, lead in enumerate(leads):
            try:
                lead_id = lead.get("id")
                lead_name = lead.get("name", f"Lead {i+1}")
                
                logger.info(f"Processando lead {lead_id}: {lead_name}")
                
                # Extrair email do lead
                email = extrair_email_lead(lead)
                
                if not email:
                    erro_msg = f"Lead {lead_id} sem email válido"
                    logger.warning(erro_msg)
                    erros.append(erro_msg)
                    resultados.append({
                        "lead_id": lead_id,
                        "status": "erro",
                        "message": "Email não encontrado"
                    })
                    continue
                
                if not lead_id:
                    erro_msg = f"Lead sem ID válido (email: {email})"
                    logger.warning(erro_msg)
                    erros.append(erro_msg)
                    resultados.append({
                        "email": email,
                        "status": "erro",
                        "message": "ID do lead não encontrado"
                    })
                    continue
                
                # Enviar email
                resultado_envio = enviar_email_marketing(email, lead)
                
                if resultado_envio["success"]:
                    emails_enviados += 1
                    resultados.append({
                        "lead_id": lead_id,
                        "email": email,
                        "status": "sucesso",
                        "message": "Email enviado com sucesso"
                    })
                else:
                    erros.append(f"Erro ao enviar email para {email}: {resultado_envio['error']}")
                    resultados.append({
                        "lead_id": lead_id,
                        "email": email,
                        "status": "erro",
                        "message": resultado_envio["error"]
                    })
                    
            except Exception as e:
                erro_msg = f"Erro ao processar lead {i+1}: {str(e)}"
                logger.error(erro_msg)
                erros.append(erro_msg)
                resultados.append({
                    "lead_index": i+1,
                    "status": "erro",
                    "message": str(e)
                })
        
        # Preparar resposta
        response_data = {
            "status": "processado",
            "total_leads": len(leads),
            "emails_enviados": emails_enviados,
            "erros": len(erros),
            "timestamp": datetime.now().isoformat(),
            "resultados": resultados
        }
        
        if erros:
            response_data["detalhes_erros"] = erros
        
        # Determinar status code da resposta
        if emails_enviados > 0:
            status_code = 200 if len(erros) == 0 else 207  # 207 = Multi-Status
        else:
            status_code = 400 if len(erros) > 0 else 200
        
        logger.info(f"Processamento concluído: {emails_enviados} emails enviados, {len(erros)} erros")
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Erro crítico no webhook: {str(e)}")
        return jsonify({
            "error": "Erro interno do servidor",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/test-email", methods=["POST"])
def test_email():
    """
    Endpoint para testar o envio de email (apenas para desenvolvimento)
    """
    try:
        data = request.get_json()
        email = data.get("email")
        
        if not email:
            return jsonify({"error": "Email não fornecido"}), 400
        
        resultado = enviar_email_marketing(email, {"name": "Teste"})
        
        if resultado["success"]:
            return jsonify({"message": "Email de teste enviado com sucesso"}), 200
        else:
            return jsonify({"error": resultado["error"]}), 500
            
    except Exception as e:
        logger.error(f"Erro no teste de email: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Tratamento de erros globais
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint não encontrado"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Método não permitido"}), 405

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno: {str(error)}")
    return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == "__main__":
    # Verificar configurações essenciais
    if not LOCAWEB_TOKEN:
        logger.error("LOCAWEB_TOKEN não configurado")
    if not LOCAWEB_ACCOUNT_ID:
        logger.error("LOCAWEB_ACCOUNT_ID não configurado")
    if not EMAIL_FROM:
        logger.error("EMAIL_FROM não configurado")
    
    logger.info("Iniciando aplicação Kommo-Locaweb Integration")
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))