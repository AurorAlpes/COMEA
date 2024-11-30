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

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Ici, on utilise du HTML pour le corps de l'e-mail
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 10px;">
            <h2 style="color: #d9534f;">🚨 Alerte Grafana Déclenchée !</h2>
            <p><strong>Nom de l'alerte:</strong> {subject}</p>
            <p><strong>Statut:</strong> {body.get('alert_state', 'Inconnu')}</p>
            <p><strong>Message:</strong> {body.get('alert_message', 'Pas de message')}</p>

            <hr style="border: 1px solid #ddd;">

            <h4 style="color: #5bc0de;">Détails :</h4>
            <ul>
    """

    for match in body.get('evalMatches', []):
        metric = match.get('metric', 'N/A')
        value = match.get('value', 'N/A')
        html_body += f"<li><strong>{metric}:</strong> {value}</li>"

    html_body += """
            </ul>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP('ssl0.ovh.net', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print("E-mail envoyé avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'e-mail : {e}")

# Route pour gérer le webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    if not data:
        return jsonify({"status": "error", "message": "Aucune donnée reçue"}), 400

    alert_name = data.get('title', 'Alerte sans titre')
    alert_state = data.get('state', 'Inconnu')
    alert_message = data.get('message', 'Pas de message')
    eval_matches = data.get('evalMatches', [])

    custom_message = {
        'alert_state': alert_state,
        'alert_message': alert_message,
        'evalMatches': eval_matches
    }

    # Envoyer l'e-mail avec le format HTML
    send_email(f"Alerte Grafana: {alert_name}", custom_message)

    return jsonify({"status": "success", "message": "Webhook reçu"}), 200

# Point d'entrée de l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
