from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    # Récupérer les données envoyées par Grafana
    data = request.json

    # Remodeler les données pour le mail
    custom_message = f"""
    Alerte Grafana déclenchée !
    Nom de l'alerte : {data.get('title', 'N/A')}
    Statut : {data.get('state', 'N/A')}
    Description : {data.get('message', 'N/A')}
    """
    
    print(custom_message)  # Debug dans les logs ou envoyer par mail ici

    # Répondre à Grafana
    return jsonify({"status": "success", "message": "Webhook received"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
