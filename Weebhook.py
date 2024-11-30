from flask import Flask, request, jsonify
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Fonction pour envoyer un e-mail
def send_email(subject, html_content):
    sender_email = os.getenv("EMAIL_USER")  # Votre email d'expédition
    sender_password = os.getenv("EMAIL_PASS")  # Votre mot de passe ou jeton SMTP
    recipient_email = os.getenv("EMAIL_DEST")  # Email destinataire

    if not sender_email or not sender_password:
        print("Erreur : Les variables d'environnement EMAIL_USER et EMAIL_PASS ne sont pas définies.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Ajouter le contenu HTML
    msg.attach(MIMEText(html_content, 'html'))

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
    alert_message = data.get('message', 'Pas de message')

    # Récupérer la valeur mesurée, par exemple la valeur "B" dans "values"
    values = "Valeur inconnue"
    for alert in data.get("alerts", []):
        # Extract the "B" value from each alert's "values"
        if "values" in alert and "B" in alert["values"]:
            values = f"B = {alert['values']['B']}"

    # Construire l'e-mail avec la valeur mesurée
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 10px;">
            <h2 style="color: #d9534f;">🚨 COMEA Alerte !</h2>
            <p><strong>Nom de l'alerte:</strong> {alert_name}</p>
            <p><strong>Statut:</strong> {data.get('state', 'Inconnu')}</p>
            <p><strong>Message:</strong> {alert_message}</p>
            <hr>
            <p><strong>Valeur Mesurée :</strong> {values}</p>
        </div>
    </body>
    </html>
    """

    send_email(f"COMEA Alerte : {alert_name}", html_content)
    return jsonify({"status": "success", "message": "Webhook reçu"}), 200


# Point d'entrée de l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
