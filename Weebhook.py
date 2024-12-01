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

    if not data:
        return jsonify({"status": "error", "message": "Aucune donnée reçue"}), 400

    try:
        # Initialiser un message vide pour les valeurs
        alert_data = "Aucune donnée disponible"

        # Vérifier que les alertes sont présentes
        if "alerts" in data and isinstance(data["alerts"], list) and data["alerts"]:
            # Traiter la première alerte
            first_alert = data["alerts"][0]
            test = data["description"]
            # Récupérer les données envoyées dans 'data'
            alert_data = first_alert.get("data", {})

        # Construire un message à partir des données reçues
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 10px;">
                <h2 style="color: #d9534f;">🚨 Alerte Grafana</h2>
                <p><strong>Données :</strong> {test}</p>
                <ul>
        """

        # Ajouter chaque clé et valeur dans un <li> HTML
        for key, value in alert_data.items():
            html_content += f"<li><strong>{key} :</strong> {value}</li>"

        html_content += """
                </ul>
            </div>
        </body>
        </html>
        """

        # Envoyer l'email
        send_email("Alerte Grafana", html_content)

        return jsonify({"status": "success", "message": "Webhook traité et email envoyé"}), 200

    except Exception as e:
        print(f"Erreur lors du traitement du webhook : {e}")
        return jsonify({"status": "error", "message": "Erreur interne lors du traitement"}), 500



# Point d'entrée de l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
