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

# Liens VIEW — ouvrent le PDF directement dans Google Drive
def view(file_id):
    return f"https://drive.google.com/file/d/{file_id}/view"

DRIVE_LINKS = {
    "maternelle": view("1kqocCbOlYSFfSJotNPSK3dp36EcCavuW"),
    "ci":         view("1b_GLMYrqK5GN60szlarfKOf5Lh9Erx3d"),
    "cp":         view("1Ie39rU54ahU9QVtPBChhBUmRgBVRrIL3"),
    "ce1":        view("1H0SHtPG2IDS96omT9iPNj3fOnhexPAFf"),
    "ce2":        view("1YkCeMJSLKQgP24Rk2bCtq-YNhNZHd4YT"),
    "cm1":        view("1Mt0dgDr_zq0KNg7eeRKujBWsC01mWCq6"),
    "cm2":        view("1rBHg-39IYHSyaPE8DrmZuAWeoI4eRnzg"),
    "cem1":       view("1QDU8lRaNR7qXTv8LhzRak4Oy-Vxs41KK"),
    "cem2":       view("1jdyGLh6NiqSH9HgBEcEiSoWuP-nimCme"),
}

PRIX = {
    "maternelle": 1000, "ci": 1000, "cp": 1000,
    "ce1": 1000, "ce2": 1000, "cm1": 1000, "cm2": 1000,
    "cem1": 1200, "cem2": 1500, "pack": 6000,
}

def envoyer_message(telephone, texte):
    numero = telephone.strip().replace("+","").replace(" ","")
    if not numero.startswith("+"):
        numero = "+" + numero
    try:
        r = requests.post(
            f"{ULTRA_BASE}/messages/chat",
            data={"token":ULTRA_TOKEN,"to":numero,"body":texte,"priority":1},
            timeout=15
        )
        log.info(f"UltraMsg {telephone}: {r.status_code} - {r.text[:80]}")
        return r.status_code == 200
    except Exception as e:
        log.error(f"Erreur UltraMsg: {e}")
        return False

def envoyer_livraison(telephone, nom, niveau, ref):
    nom_niveau = NOMS_NIVEAUX.get(niveau, niveau)

    if niveau == "pack":
        liens = ""
        for niv in ["maternelle","ci","cp","ce1","ce2","cm1","cm2","cem1","cem2"]:
            liens += f"\n• {NOMS_NIVEAUX[niv]}:\n{DRIVE_LINKS[niv]}"
        message = (
            f"Bonjour {nom} ! 🎓\n\n"
            f"Merci pour votre commande MES EXERCICES !\n\n"
            f"✅ Votre Pack Complet (9 niveaux) est prêt !\n\n"
            f"📖 Ouvrez vos 9 cahiers PDF :{liens}\n\n"
            f"💡 Appuyez sur le lien pour ouvrir le PDF\n"
            f"    puis appuyez ⬇️ pour le sauvegarder\n\n"
            f"📌 Référence : {ref}\n"
            f"📚 Bon apprentissage !\n"
            f"📞 Support : +221 77 134 34 99"
        )
    else:
        lien = DRIVE_LINKS.get(niveau, "")
        message = (
            f"Bonjour {nom} ! 🎓\n\n"
            f"Merci pour votre commande MES EXERCICES !\n\n"
            f"✅ Votre cahier *{nom_niveau}* est prêt !\n\n"
            f"📖 Ouvrez votre PDF ici :\n"
            f"{lien}\n\n"
            f"💡 Appuyez sur le lien pour ouvrir le PDF\n"
            f"    puis appuyez ⬇️ pour le sauvegarder\n\n"
            f"📌 Référence : {ref}\n"
            f"📚 Bon apprentissage !\n"
            f"📞 Support : +221 77 134 34 99"
        )
    return envoyer_message(telephone, message)

def envoyer_confirmation_attente(telephone, nom, niveau, ref):
    nom_niveau = NOMS_NIVEAUX.get(niveau, niveau)
    prix = PRIX.get(niveau, 0)
    message = (
        f"Bonjour {nom} !\n\n"
        f"✅ Votre commande MES EXERCICES a été reçue.\n\n"
        f"📚 Niveau : {nom_niveau}\n"
        f"💰 Montant : {prix:,} FCFA\n"
        f"📌 Référence : {ref}\n\n"
        f"Votre cahier PDF sera envoyé après confirmation du paiement.\n"
        f"📞 Contact : +221 77 134 34 99"
    )
    return envoyer_message(telephone, message)
