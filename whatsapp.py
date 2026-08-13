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
    "maternelle": "https://drive.google.com/file/d/1K0W1OhjWi9przzz4Q7sGkUbRtnQMLJOk/view?usp=sharing",
    "ci":         "https://drive.google.com/file/d/1URr_sYraPxX_EDX8MVYond4X4qA_NUd-/view?usp=drive_link",
    "cp":         "https://drive.google.com/file/d/1_BgaDuurE3zRW4E9bgMfyu7KpPnGZsRB/view?usp=sharing",
    "ce1":        "https://drive.google.com/file/d/1_LIt16yOn9oRPy32CGxynbg71w2hWFgi/view?usp=sharing",
    "ce2":        "https://drive.google.com/file/d/1v0mYvk-iVU0lFBBAXhlW1S0TjYwiVo6f/view?usp=drive_link",
    "cm1":        "https://drive.google.com/file/d/100MbZfQ23dkX-JRWYyWbz1_76g0UBkmw/view?usp=drive_link",
    "cm2":        "https://drive.google.com/file/d/1zG8XeuaT2KX87SKxIw9B8TY31iBFfJSb/view?usp=drive_link",
    "cem1":       "https://drive.google.com/file/d/1ERJBgxta-UMAZXYX9YLQ0mHiDRbd0m3W/view?usp=drive_link",
    "cem2":       "https://drive.google.com/file/d/1QndP0yRfbpfQgvYkj9eP3qs9cZrgu5IM/view?usp=sharing",
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
