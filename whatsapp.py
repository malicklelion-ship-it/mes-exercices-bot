import requests
import logging

log = logging.getLogger(__name__)

# --- Green API - identifiants ---
GREEN_INSTANCE = "710722708786"
GREEN_TOKEN    = "219438e83e1a4e929a867f34e27565a560c00bb08f6a4a6089"   # <-- remplacez par votre vrai token
# --------------------------------

NOMS_NIVEAUX = {
    "maternelle": "Maternelle",
    "ci":         "CI - Cours d'Initiation",
    "cp":         "CP - Cours Preparatoire",
    "ce1":        "CE1",
    "ce2":        "CE2",
    "cm1":        "CM1",
    "cm2":        "CM2",
    "cem1":       "CEM1 (6eme)",
    "cem2":       "CEM2 - BFEM",
    "pack":       "Pack Complet (9 niveaux)",
}

DRIVE_LINKS = {
    "maternelle": "https://drive.google.com/file/d/1kqocCbOlYSFfSJotNPSK3dp36EcCavuW/view?usp=drive_link",
    "ci":         "https://drive.google.com/file/d/1b_GLMYrqK5GN60szlarfKOf5Lh9Erx3d/view?usp=drive_link",
    "cp":         "https://drive.google.com/file/d/1Ie39rU54ahU9QVtPBChhBUmRgBVRrIL3/view?usp=drive_link",
    "ce1":        "https://drive.google.com/file/d/1H0SHtPG2IDS96omT9iPNj3fOnhexPAFf/view?usp=drive_link",
    "ce2":        "https://drive.google.com/file/d/1YkCeMJSLKQgP24Rk2bCtq-YNhNZHd4YT/view?usp=drive_link",
    "cm1":        "https://drive.google.com/file/d/1Mt0dgDr_zq0KNg7eeRKujBWsC01mWCq6/view?usp=drive_link",
    "cm2":        "https://drive.google.com/file/d/1rBHg-39IYHSyaPE8DrmZuAWeoI4eRnzg/view?usp=drive_link",
    "cem1":       "https://drive.google.com/file/d/1QDU8lRaNR7qXTv8LhzRak4Oy-Vxs41KK/view?usp=drive_link",
    "cem2":       "https://drive.google.com/file/d/1jdyGLh6NiqSH9HgBEcEiSoWuP-nimCme/view?usp=drive_link",
    "pack":       "Voir les 9 liens ci-dessus",
}

PRIX = {
    "maternelle": 1000, "ci": 1000, "cp": 1000,
    "ce1": 1000, "ce2": 1000, "cm1": 1000, "cm2": 1000,
    "cem1": 1200, "cem2": 1500, "pack": 6000,
}

BASE_URL = f"https://7107.api.greenapi.com/waInstance{GREEN_INSTANCE}"

def envoyer_message(telephone, texte):
    """Envoie un message texte simple via Green API."""
    numero = telephone.strip().replace("+", "").replace(" ", "")
    if not numero.endswith("@c.us"):
        numero = numero + "@c.us"
    url = f"{BASE_URL}/sendMessage/{GREEN_TOKEN}"
    payload = {"chatId": numero, "message": texte}
    try:
        r = requests.post(url, json=payload, timeout=15)
        log.info(f"Green API sendMessage: {r.status_code} - {r.text[:100]}")
        return r.status_code == 200
    except Exception as e:
        log.error(f"Erreur envoi message: {e}")
        return False

def envoyer_livraison(telephone, nom, niveau, ref):
    """Envoie le message de livraison avec le lien du cahier."""
    nom_niveau = NOMS_NIVEAUX.get(niveau, niveau)

    if niveau == "pack":
        # Pour le pack, envoyer tous les liens
        liens = ""
        for niv, lien in DRIVE_LINKS.items():
            if niv != "pack":
                liens += f"\n- {NOMS_NIVEAUX[niv]} : {lien}"
        message = (
            f"Bonjour {nom} ! Merci pour votre commande MES EXERCICES.\n\n"
            f"Votre Pack Complet (9 niveaux) est pret !\n\n"
            f"Vos 9 cahiers :{liens}\n\n"
            f"Reference : {ref}\n"
            f"Bon apprentissage ! Pour toute question : +221 77 134 34 99"
        )
    else:
        lien = DRIVE_LINKS.get(niveau, "")
        message = (
            f"Bonjour {nom} ! Merci pour votre commande MES EXERCICES.\n\n"
            f"Votre cahier {nom_niveau} est pret !\n\n"
            f"Telechargez-le ici :\n{lien}\n\n"
            f"Reference : {ref}\n"
            f"Bon apprentissage ! Pour toute question : +221 77 134 34 99"
        )
    return envoyer_message(telephone, message)

def envoyer_confirmation_attente(telephone, nom, niveau, ref):
    """Envoie une confirmation de reception de commande."""
    nom_niveau = NOMS_NIVEAUX.get(niveau, niveau)
    prix = PRIX.get(niveau, 0)
    message = (
        f"Bonjour {nom} !\n\n"
        f"Votre commande MES EXERCICES a ete recue.\n\n"
        f"Niveau : {nom_niveau}\n"
        f"Montant : {prix:,} FCFA\n"
        f"Reference : {ref}\n\n"
        f"Votre cahier vous sera envoye sous 5 minutes apres confirmation du paiement.\n"
        f"Contact : +221 77 134 34 99"
    )
    return envoyer_message(telephone, message)

def envoyer_relance(telephone, nom, niveau, ref):
    """Envoie un message de relance si paiement non confirme."""
    nom_niveau = NOMS_NIVEAUX.get(niveau, niveau)
    prix = PRIX.get(niveau, 0)
    message = (
        f"Bonjour {nom} !\n\n"
        f"Votre commande {nom_niveau} ({prix:,} FCFA) - ref {ref} - est en attente de paiement.\n\n"
        f"Envoyez le paiement sur +221 77 134 34 99 (Wave ou Orange Money)\n"
        f"puis repondez a ce message pour confirmer."
    )
    return envoyer_message(telephone, message)
