from flask import Flask, request, jsonify
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# Fonction pour envoyer un e-mail
def send_email(subject, html_content):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")
    recipient_email = os.getenv("EMAIL_DEST")

    if not sender_email or not sender_password:
        print("Erreur : Les variables d'environnement EMAIL_USER et EMAIL_PASS ne sont pas définies.")
        return

    msg = MIMEText(html_content, 'html')
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

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

    if not data or 'alerts' not in data:
        return jsonify({"status": "error", "message": "Payload invalide"}), 400

    # Construire un e-mail en HTML à partir des alertes reçues
    subject = data.get("title", "Alerte Grafana")
    alerts = data.get("alerts", [])
    status = data.get("status", "unknown").capitalize()

    # Générer le contenu HTML
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; color: #333; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); padding: 20px;">
            <h2 style="color: #d9534f; text-align: center;">🚨 {subject} 🚨</h2>
            <p><strong>Statut :</strong> {status}</p>
            <hr style="border: 1px solid #eaeaea;">
    """

    # Ajouter les détails pour chaque alerte
    for alert in alerts:
        alert_name = alert["labels"].get("alertname", "Nom inconnu")
        description = alert["annotations"].get("description", "Pas de description")
        value_b = alert.get("values", {}).get("B", "Valeur inconnue")
        zone = alert["labels"].get("zone", "Zone inconnue")
        runbook_url = alert["annotations"].get("runbook_url", "#")

        # Contenu HTML pour l'email
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 10px;">
                <h2 style="color: #d9534f;">🚨 COMEA Alerte Déclenchée !</h2>
                <p><strong>Nom de l'alerte :</strong> {alert_name}</p>
                <p><strong>Message :</strong> {alert_message}</p>
                <p><strong>Valeur Mesurée (B) :</strong> {alert_value_b}</p>
            </div>
        </body>
        </html>
        """

    Envoyer l'e-mail
    send_email(subject, html_content)
    return jsonify({"status": "success", "message": "Notification envoyée"}), 200

# Point d'entrée de l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
