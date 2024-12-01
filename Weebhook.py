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
    if not data or "alerts" not in data:
        return jsonify({"status": "error", "message": "Aucune alerte reçue"}), 400

    alerts = data["alerts"]

    for alert in alerts:
        alert_status = alert.get("status", "unknown")
        alert_name = alert.get("alertname", "Alerte sans titre")
        timestamp = alert.get("timestamp", "Inconnue")
        alert_data = alert.get("data", {})

        # Construire un contenu HTML dynamique pour chaque alerte
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 10px;">
                <h2 style="color: #d9534f;">🚨 Alerte Grafana</h2>
                <p><strong>Nom de l'alerte :</strong> {alert_name}</p>
                <p><strong>Statut :</strong> {alert_status}</p>
                <p><strong>Date :</strong> {timestamp}</p>
                <h3>Données :</h3>
                <ul>
        """
        for key, value in alert_data.items():
            html_content += f"<li><strong>{key} :</strong> {value}</li>"

        html_content += """
                </ul>
            </div>
        </body>
        </html>
        """

        # Envoyer un email pour chaque alerte
        send_email(f"Alerte Grafana : {alert_name}", html_content)

    return jsonify({"status": "success", "message": "Webhook reçu et traité"}), 200


# Point d'entrée de l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
