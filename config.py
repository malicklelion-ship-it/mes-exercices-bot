"""
⚙️ CONFIGURATION MES EXERCICES — Bot WhatsApp automatique
Remplissez vos clés API ici avant de déployer.
"""

# ─── VOTRE NUMÉRO WHATSAPP BUSINESS ──────────────────────────────
VOTRE_NUMERO = "+221771343499"

# ─── ULTRAMSG (WhatsApp API) ────────────────────────────────────
# Créez un compte gratuit sur https://ultramsg.com
# Dashboard → Instances → Créer → Scanner le QR avec votre WhatsApp Business
# Green API (gratuit) — voir whatsapp.py
# https://green-api.com — 200 messages/jour gratuits

# ─── LIENS GOOGLE DRIVE (un lien par niveau) ────────────────────
# Drive → clic droit sur fichier → Partager → "Toute personne avec le lien"
DRIVE_LINKS = {
    "maternelle": "https://drive.google.com/LIEN_MATERNELLE",
    "ci":         "https://drive.google.com/LIEN_CI",
    "ce1":        "https://drive.google.com/LIEN_CE1",
    "ce2":        "https://drive.google.com/LIEN_CE2",
    "cm1":        "https://drive.google.com/LIEN_CM1",
    "cm2":        "https://drive.google.com/LIEN_CM2",
    "cem1":       "https://drive.google.com/LIEN_CEM1",
    "cem2":       "https://drive.google.com/LIEN_CEM2",
    "pack":       "https://drive.google.com/LIEN_PACK_COMPLET",
}

# ─── TARIFS (FCFA) ──────────────────────────────────────────────
PRIX = {
    "maternelle": 1000,
    "ci":         1000,
    "ce1":        1000,
    "ce2":        1000,
    "cm1":        1000,
    "cm2":        1000,
    "cem1":       1200,
    "cem2":       1500,
    "pack":       5000,
}

NOMS_NIVEAUX = {
    "maternelle": "🎨 Maternelle",
    "ci":         "📖 CI — Cours d'Initiation",
    "ce1":        "📗 CE1 — Cours Élémentaire 1",
    "ce2":        "📘 CE2 — Cours Élémentaire 2",
    "cm1":        "📙 CM1 — Cours Moyen 1",
    "cm2":        "📕 CM2 — Cours Moyen 2",
    "cem1":       "🔬 CEM1 — Collège 1re Année",
    "cem2":       "🎓 CEM2 — BFEM",
    "pack":       "⭐ Pack Complet 8 niveaux",
}

# ─── CLÉS SECRÈTES ──────────────────────────────────────────────
ADMIN_PASSWORD = "mesexercices2025"   # ← changez ce mot de passe !
SECRET_KEY     = "changez_cette_cle_secrete_longue_et_aleatoire"

# ─── WAVE WEBHOOK (optionnel) ───────────────────────────────────
# Si vous avez un compte Wave Business avec webhook activé
WAVE_SECRET_KEY = ""   # laissez vide si non utilisé
