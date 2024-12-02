from flask import Flask, request, jsonify
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)


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
        
        # Fonction pour formater les heures
        def format_time(iso_time):
            if not iso_time:
                return "Unknown time"
            try:
                # Traiter les formats avec ou sans millisecondes
                if "." in iso_time:
                    return datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S (UTC)")
                else:
                    return datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S (UTC)")
            except ValueError:
                return "Invalid time format"
        
        # Récupérer les heures de début et de fin
        starts_at = format_time(alert.get("startsAt"))
        ends_at = format_time(alert.get("endsAt")) if status == "resolved" else "En cours"
        
        # Déterminer le message à afficher
        if status == "firing":
            message = f"{message1}\n"
        elif status == "resolved":
            message = f"{message2}\n"
        else:
            message = "Unknown status"

        # Construire le sujet et le corps de l'e-mail
        subject = f"Grafana Alert: {alert_name} ({status.capitalize()})"
        body = (
            f"Nom d'alerte: {alert_name}\n"
            f"Status: {status}\n"
            f"Début d'événement: {starts_at}\n"
            f"Fin d'événement: {ends_at}\n"
            f"{message}"
        )
        
        # Envoyer l'e-mail
        send_email(subject, body)
        return "Email sent", 200

    return "No data received", 400



# Point d'entrée de l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
