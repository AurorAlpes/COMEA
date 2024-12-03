from flask import Flask, request, jsonify
import locale
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)


def send_email(subject, content, is_html=False):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")
    recipient_email = os.getenv("EMAIL_DEST")

    if not sender_email or not sender_password:
        print("Erreur : Les variables d'environnement EMAIL_USER et EMAIL_PASS ne sont pas définies.")
        return

    # Préparer le message en fonction du type de contenu
    msg = MIMEText(content, 'html' if is_html else 'plain')
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

        
        # Fonction de formatage de la date
        def format_time(iso_time):
            if not iso_time:
                return "Unknown time"
            try:
                # Vérifier et normaliser les millisecondes
                if "." in iso_time:
                    base_time, milliseconds = iso_time.split(".")
                    milliseconds = milliseconds.rstrip("Z")  # Supprimer le 'Z' à la fin
                    milliseconds = milliseconds[:6]  # Limiter à 6 chiffres
                    iso_time = f"{base_time}.{milliseconds}Z"
                
                # Conversion de la chaîne de date en objet datetime
                date_obj = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S.%fZ" if "." in iso_time else "%Y-%m-%dT%H:%M:%SZ")
                
                # Listes personnalisées pour les jours et mois en français
                days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
                months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
                
                # Extraire les composants de la date
                day_name = days[date_obj.weekday()]  # Nom du jour
                day = date_obj.day  # Jour du mois
                month_name = months[date_obj.month - 1]  # Nom du mois
                year = date_obj.year  # Année
                hour = date_obj.strftime("%H")  # Heure
                minute = date_obj.strftime("%M")  # Minute
                
                # Retourner la date formatée
                return f"{day_name} {day} {month_name} {year} à {hour}h{minute} (UTC)"
            
            except ValueError:
                return "Invalid time format"

        
        # Récupérer les heures de début et de fin
        starts_at = format_time(alert.get("startsAt"))
        ends_at = format_time(alert.get("endsAt")) if status == "resolved" else "En cours"
        
        # Déterminer le message à afficher
        if status == "firing":
            subject = f"{alert_name} en cours - COMEA alerte"
            message = f"{message1}"
        elif status == "resolved":
            subject = f"[Fin d'événement] {alert_name} - COMEA alerte"
            message = f"{message2}"
        else:
            message = "Unknown status"

        # Construire le sujet et le corps de l'e-mail
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
                            width: 550px;
                        }}
                        .footer {{
                            background-color: #f4f4f4;
                            border-radius: 8px;
                            padding: 10px;
                            text-align: center;
                            margin-top: 20px;
                            font-size: 14px;
                            color: #555;
                            border: 1px solid #ddd;
                        }}
                        .footer img {{
                            width: 150px;
                            margin-top: 10px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="title">{alert_name}</div>
                        <div class="times">
                            <strong>Début :</strong> {starts_at}<br>
                            <strong>Fin :</strong> {ends_at}
                        </div>
                        <div class="separator"></div>
                        <div class="message">{message}</div>
                
                        <!-- Encadré d'explication -->
                        <div class="footer">
                            <p><i>Ce service est fourni et opéré par le COMEA</strong></i>
                            <img src="https://raw.githubusercontent.com/AurorAlpes/COMEA/b50d6143240d132a583bc5a4a45221bf163a812e/logo%20comea.svg" alt="comea.space">
                            <div class="logo">
                                <img src="https://raw.githubusercontent.com/AurorAlpes/COMEA/refs/heads/main/Design%20sans%20titre.png" alt="OFRAME, IRAP, CNRS, ONERA, CLS, CEA, THALES ">
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """

        # Envoyer l'e-mail
        send_email(subject, body, is_html=True)  # Indiquer que le contenu est HTML
        return "Email sent", 200

    return "No data received", 400



# Point d'entrée de l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
