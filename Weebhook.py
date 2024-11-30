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
# Route pour gérer le webhook
@app.route('/webhook', methods=['POST'])
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    if not data:
        return jsonify({"status": "error", "message": "Aucune donnée reçue"}), 400

    # Initialiser les valeurs par défaut
    alert_name = "Alerte sans titre"
    alert_message = "Pas de message"
    alert_value_b = "Valeur inconnue"

    try:
        # Vérifier que les alertes sont présentes
        if "alerts" in data and isinstance(data["alerts"], list) and data["alerts"]:
            # Traiter la première alerte (ou étendre pour plusieurs alertes si nécessaire)
            first_alert = data["alerts"][0]

            # Récupérer le nom de l'alerte
            alert_name = first_alert.get("labels", {}).get("alertname", "Alerte sans titre")

            # Récupérer la valeur de 'B' si disponible
            if "values" in first_alert and isinstance(first_alert["values"], dict):
                alert_value_b = first_alert["values"].get("B", "Valeur inconnue")

            # Construire un message à partir des annotations
            alert_message = first_alert.get("annotations", {}).get("description", "Pas de description disponible")

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

        # Envoyer l'email
        send_email(f"COMEA Alerte : {alert_name}", html_content)

        return jsonify({"status": "success", "message": "Webhook traité et email envoyé"}), 200

    except Exception as e:
        print(f"Erreur lors du traitement du webhook : {e}")
        return jsonify({"status": "error", "message": "Erreur interne lors du traitement"}), 500


# Point d'entrée de l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
