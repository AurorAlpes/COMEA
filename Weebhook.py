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
            message = f"{message1}"
        elif status == "resolved":
            message = f"{message2}"
        else:
            message = "Unknown status"

        # Construire le sujet et le corps de l'e-mail
        subject = f"Grafana Alert: {alert_name} ({status.capitalize()})"
        body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    color: #333;
                    background-color: #f9f9f9;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    padding: 20px;
                    max-width: 600px;
                    margin: auto;
                }}
                .title {{
                    font-size: 24px;
                    font-weight: bold;
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .times {{
                    text-align: center;
                    font-size: 16px;
                    margin-bottom: 20px;
                }}
                .separator {{
                    border-top: 2px solid #ddd;
                    margin: 20px 0;
                }}
                .message {{
                    text-align: center;
                    font-size: 16px;
                    margin-bottom: 20px;
                }}
                .logo {{
                    text-align: center;
                    margin-top: 20px;
                }}
                .logo img {{
                    width: 100px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">##### {alert_name} #####</div>
                <div class="times">
                    <strong>Début :</strong> {starts_at}<br>
                    <strong>Fin :</strong> {ends_at}
                </div>
                <div class="separator"></div>
                <div class="message">{message}</div>
                <div class="logo">
                    <img src="https://via.placeholder.com/100" alt="Logo Structure">
                </div>
            </div>
        </body>
        </html>
        """

        # Envoyer l'e-mail
        send_email(subject, body, is_html=True)
        return "Email sent", 200

    return "No data received", 400


def send_email(subject, body, is_html=False):
    # Dépend de votre bibliothèque SMTP
    msg = MIMEMultipart("alternative") if is_html else MIMEMultipart()
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html" if is_html else "plain"))
    # Ajoutez le reste de la logique SMTP


# Point d'entrée de l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
