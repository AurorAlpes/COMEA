from flask import Flask, request, jsonify
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Fonction pour envoyer un e-mail
def send_email(subject, body):
    sender_email = os.getenv("EMAIL_USER")  # Charger l'e-mail depuis les variables d'environnement
    sender_password = os.getenv("EMAIL_PASS")  # Charger le mot de passe ou jeton SMTP
    recipient_email = os.getenv("EMAIL_DEST")  # Remplacer par l'adresse du destinataire

    if not sender_email or not sender_password:
        print("Erreur : Les variables d'environnement EMAIL_USER et EMAIL_PASS ne sont pas définies.")
        return

    # Configurer le message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connexion au serveur SMTP OVH
        with smtplib.SMTP('ssl0.ovh.net', 587) as server:  # Utilisez le port 587 pour STARTTLS
            server.starttls()  # Sécuriser la connexion
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print("E-mail envoyé avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'e-mail : {e}")

# Route pour gérer le webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    # Récupérer les données JSON envoyées par Grafana
    data = request.json

    # Vérifier si les données sont valides
    if not data:
        return jsonify({"status": "error", "message": "Aucune donnée reçue"}), 400

    # Reformater les données
    alert_name = data.get('title', 'Alerte sans titre')
    alert_state = data.get('state', 'Inconnu')
    alert_message = data.get('message', 'Pas de message')
    eval_matches = data.get('evalMatches', [])

    # Construire un message personnalisé
    custom_message = f"""
    🚨 **Alerte Grafana Déclenchée !**
    - **Nom de l'alerte** : {alert_name}
    - **Statut** : {alert_state}
    - **Message** : {alert_message}
    """

    # Ajouter des détails sur les correspondances d'évaluation
    if eval_matches:
        custom_message += "\n**Détails :**\n"
        for match in eval_matches:
            metric = match.get('metric', 'N/A')
            value = match.get('value', 'N/A')
            custom_message += f"  - {metric}: {value}\n"

    print(custom_message)  # Afficher le message dans les logs

    # Envoyer un e-mail avec l'alerte reformattée
    send_email(f"Alerte Grafana: {alert_name}", custom_message)

    # Répondre à Grafana
    return jsonify({"status": "success", "message": "Webhook reçu"}), 200

# Point d'entrée de l'application
if __name__ == '__main__':
    # Définir le port et l'hôte pour Render ou localhost
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
