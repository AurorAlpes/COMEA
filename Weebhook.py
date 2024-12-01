from flask import Flask, request, jsonify
from datetime import datetime
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

def format_time(iso_time):
    """
    Convertit une chaîne de temps ISO 8601 en un format lisible (UTC).
    Gère les cas avec ou sans fractions de secondes.
    """
    if not iso_time:  # Vérifie si la date est vide ou None
        return "En cours"
    try:
        # Cas avec fractions de secondes
        return datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S (UTC)")
    except ValueError:
        # Cas sans fractions de secondes
        return datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S (UTC)")


# Route pour gérer le webhook
@app.route("/webhook", methods=["POST"])
def grafana_webhook():
    data = request.json
    if data:
        # Récupérer les informations nécessaires
        status = data.get("status", "unknown")  # "firing" ou "resolved"
        alert = data.get("alerts", [{}])[0]  # Premier élément de la liste d'alertes
        alert_name = alert.get("labels", {}).get("alertname", "No alert name")
        message1 = alert.get("annotations", {}).get("summary", "No description")
        message2 = alert.get("annotations", {}).get("description", "No description")
        value = alert.get("valueString", "No value provided")
        starts_at = format_time(alert.get("startsAt"))
        ends_at = format_time(alert.get("endsAt"))

        # Choisir le message en fonction du statut
        if status == "firing":
            message = message1
        elif status == "resolved":
            message = message2
        else:
            message = "Unknown status"

        # Construire le sujet et le corps de l'e-mail
        subject = f"Grafana Alert: {alert_name}"
        body = (
            f"Alert Name: {alert_name}\n"
            f"Status: {status}\n"
            f"Start Time: {starts_at}\n"
            f"End Time: {ends_at}\n"
            f"Message: {message}"
        )
        
        # Envoyer l'e-mail
        send_email(subject, body)
        return "Email sent", 200

    return "No data received", 400



# Point d'entrée de l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
