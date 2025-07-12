@app.route('/kommo-webhook', methods=["POST"])
def receber_webhook():
    if not request.is_json:
        return jsonify({"error": "Conteúdo não é JSON"}), 400

    try:
        data = request.get_json()
        print(">>> Dados recebidos:", data)

        leads = data.get('leads')
        if not leads or not isinstance(leads, list):
            return jsonify({"error": "Formato inválido de leads"}), 400

        lead = leads[0]
        print(">>> LEAD EXTRAÍDO:", lead)

        lead_id = lead.get('id')
        nome = lead.get('name', 'Contato')
        email = None

        print(">>> ID:", lead_id)
        print(">>> Nome:", nome)

        if 'custom_fields' in lead:
            for field in lead['custom_fields']:
                nome_campo = normalizar(field.get('name', ''))
                print(">>> Campo encontrado:", nome_campo)

                if 'email' in nome_campo:
                    valores = field.get('values', [])
                    if valores and isinstance(valores, list):
                        email = valores[0].get('value')

        print(">>> Email extraído:", email)

        if not lead_id or not email:
            return jsonify({"error": "Lead sem ID ou email"}), 400

        if lead_ja_processado(lead_id):
            return jsonify({"message": "Lead já processado"}), 200

        status, resposta = enviar_email_locaweb(nome, email)

        if status in [200, 202]:
            registrar_lead(lead_id)
            return jsonify({"message": "E-mail enviado com sucesso"}), 200
        else:
            return jsonify({"error": "Erro ao enviar e-mail", "detalhes": resposta, "status": status}), 500

    except Exception as e:
        return jsonify({"error": "Erro no processamento", "mensagem": str(e)}), 500
