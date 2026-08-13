"""
📱 WHATSAPP — Green API (formule GRATUITE : 200 msg/jour)
Créez un compte gratuit sur https://green-api.com
"""
import requests, logging
from config import NOMS_NIVEAUX, DRIVE_LINKS

log = logging.getLogger(__name__)

# ─── Green API — collez vos identifiants ici ────────────────────
GREEN_INSTANCE = "VOTRE_INSTANCE_ID"   # ex: "1101234567"
GREEN_TOKEN    = "VOTRE_TOKEN_ICI"     # ex: "abc123..."
# ────────────────────────────────────────────────────────────────

def num(telephone):
    """Normalise le numéro → 221771343499@c.us (format Green API)"""
    n = telephone.strip().replace(" ","").replace("-","").replace("+","")
    return f"{n}@c.us"

def envoyer_message(telephone, texte):
    url = f"https://api.green-api.com/waInstance{GREEN_INSTANCE}/sendMessage/{GREEN_TOKEN}"
    try:
        r = requests.post(url, json={"chatId": num(telephone), "message": texte}, timeout=15)
        r.raise_for_status()
        log.info(f"✅ Message → {telephone}")
        return {"ok": True}
    except Exception as e:
        log.error(f"❌ Erreur WhatsApp {telephone}: {e}")
        return {"ok": False, "error": str(e)}

def envoyer_livraison(telephone, niveau, prenom=""):
    """Envoie les 3 messages de livraison au client."""
    nom = NOMS_NIVEAUX.get(niveau, niveau)
    lien = DRIVE_LINKS.get(niveau, "")
    salut = f"Bonjour {prenom} !" if prenom else "Bonjour !"

    m1 = f"""✅ Paiement reçu ! Merci 🙏

{salut} Votre cahier *{nom}* est confirmé.
Voici votre lien de téléchargement 👇"""

    m2 = f"""📥 *Votre cahier MES EXERCICES :*
{lien}

Ce lien est *personnel et illimité* — imprimez autant de fois que vous voulez ! 🖨️"""

    m3 = """📋 *Instructions d'impression :*
• Format A4, recto/verso
• "Ajuster à la page" dans les paramètres
• 50 feuilles = cahier 100 pages ✅

Bonne chance à votre enfant ! 🌟
📚 *MES EXERCICES* — +221 77 134 34 99"""

    ok = all([
        envoyer_message(telephone, m1)["ok"],
        envoyer_message(telephone, m2)["ok"],
        envoyer_message(telephone, m3)["ok"],
    ])
    if ok: log.info(f"📬 Livraison complète → {telephone} ({niveau})")
    return ok

def envoyer_confirmation_attente(telephone, niveau, montant):
    """Instructions de paiement envoyées au client."""
    nom = NOMS_NIVEAUX.get(niveau, niveau)
    msg = f"""Bonjour ! 👋 Merci pour votre commande *{nom}* 📚

💰 *Montant : {montant:,} FCFA*

*Wave 📱 :* Envoyez au *+221 77 134 34 99*
Message : "Cahier {niveau.upper()}"

*Orange Money 🟠 :* Envoyez au *+221 77 134 34 99*
Puis envoyez votre reçu ici

✅ Cahier envoyé automatiquement en *moins de 5 minutes* !"""
    return envoyer_message(telephone, msg)["ok"]

def envoyer_relance(telephone, niveau, prenom=""):
    salut = f"Bonjour {prenom} !" if prenom else "Bonjour !"
    nom = NOMS_NIVEAUX.get(niveau, niveau)
    msg = f"""{salut} 👋

Tout s'est bien passé avec le cahier *{nom}* ? 😊
Des questions sur l'impression ? On est là !

📚 *MES EXERCICES* — +221 77 134 34 99"""
    return envoyer_message(telephone, msg)["ok"]
