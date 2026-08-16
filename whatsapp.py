import requests
import logging

log = logging.getLogger(__name__)

# ============================================================
# ULTRAMSG — WhatsApp API
# ============================================================
ULTRA_INSTANCE = "instance188601"
ULTRA_TOKEN    = "bya0778bd0fr1j4g"
ULTRA_BASE     = f"https://api.ultramsg.com/{ULTRA_INSTANCE}"

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

# Liens de TELECHARGEMENT DIRECT PDF (format uc?export=download)
def drive_link(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"

DRIVE_LINKS = {
    "maternelle": drive_link("1K0W1OhjWi9przzz4Q7sGkUbRtnQMLJOk"),
    "ci":         drive_link("1URr_sYraPxX_EDX8MVYond4X4qA_NUd-"),
    "cp":         drive_link("1_BgaDuurE3zRW4E9bgMfyu7KpPnGZsRB"),
    "ce1":        drive_link("1_LIt16yOn9oRPy32CGxynbg71w2hWFgi"),
    "ce2":        drive_link("1v0mYvk-iVU0lFBBAXhlW1S0TjYwiVo6f"),
    "cm1":        drive_link("100MbZfQ23dkX-JRWYyWbz1_76g0UBkmw"),
    "cm2":        drive_link("1zG8XeuaT2KX87SKxIw9B8TY31iBFfJSb"),
    "cem1":       drive_link("1ERJBgxta-UMAZXYX9YLQ0mHiDRbd0m3W"),
    "cem2":       drive_link("1QndP0yRfbpfQgvYkj9eP3qs9cZrgu5IM"),
}

PRIX = {
    "maternelle": 1000, "ci": 1000, "cp": 1000,
    "ce1": 1000, "ce2": 1000, "cm1": 1000, "cm2": 1000,
    "cem1": 1200, "cem2": 1500, "pack": 6000,
}

def envoyer_message(telephone, texte):
    """Envoie un message texte via UltraMsg"""
    numero = telephone.strip().replace("+", "").replace(" ", "")
    if not numero.startswith("+"):
        numero = "+" + numero
    try:
        r = requests.post(
            f"{ULTRA_BASE}/messages/chat",
            data={
                "token": ULTRA_TOKEN,
                "to": numero,
                "body": texte,
                "priority": 1
            },
            timeout=15
        )
        log.info(f"UltraMsg {telephone}: {r.status_code} - {r.text[:100]}")
        return r.status_code == 200
    except Exception as e:
        log.error(f"Erreur UltraMsg: {e}")
        return False

def envoyer_livraison(telephone, nom, niveau, ref):
    """Envoie le lien de telechargement PDF direct"""
    nom_niveau = NOMS_NIVEAUX.get(niveau, niveau)

    if niveau == "pack":
        # Pack = envoyer tous les liens
        liens = ""
        for niv in ["maternelle","ci","cp","ce1","ce2","cm1","cm2","cem1","cem2"]:
            liens += f"\n{NOMS_NIVEAUX[niv]}: {DRIVE_LINKS[niv]}"
        message = (
            f"Bonjour {nom} ! 🎓\n\n"
            f"Merci pour votre commande MES EXERCICES !\n\n"
            f"Votre Pack Complet (9 niveaux) est pret !\n"
            f"Telechargez vos cahiers PDF :{liens}\n\n"
            f"Reference : {ref}\n\n"
            f"Bon apprentissage ! 📚\n"
            f"Support : +221 77 134 34 99"
        )
    else:
        lien = DRIVE_LINKS.get(niveau, "")
        message = (
            f"Bonjour {nom} ! 🎓\n\n"
            f"Merci pour votre commande MES EXERCICES !\n\n"
            f"Votre cahier *{nom_niveau}* est pret !\n\n"
            f"Telechargez votre PDF ici :\n"
            f"{lien}\n\n"
            f"Reference : {ref}\n\n"
            f"Bon apprentissage ! 📚\n"
            f"Support : +221 77 134 34 99"
        )

    return envoyer_message(telephone, message)

def envoyer_confirmation_attente(telephone, nom, niveau, ref):
    nom_niveau = NOMS_NIVEAUX.get(niveau, niveau)
    prix = PRIX.get(niveau, 0)
    message = (
        f"Bonjour {nom} !\n\n"
        f"Votre commande MES EXERCICES a ete recue.\n"
        f"Niveau : {nom_niveau}\n"
        f"Montant : {prix:,} FCFA\n"
        f"Reference : {ref}\n\n"
        f"Votre cahier PDF sera envoye apres confirmation du paiement.\n"
        f"Contact : +221 77 134 34 99"
    )
    return envoyer_message(telephone, message)
