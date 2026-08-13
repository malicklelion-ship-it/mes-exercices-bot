"""
🚀 MES EXERCICES — Bot de livraison automatique WhatsApp
Server Flask : commandes + paiements + livraison automatique
"""
import os, sqlite3, logging, hashlib, hmac, json
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, request, jsonify, render_template,
                   redirect, url_for, session, flash)
from whatsapp import envoyer_livraison, envoyer_confirmation_attente, envoyer_relance
from config import (PRIX, NOMS_NIVEAUX, ADMIN_PASSWORD, SECRET_KEY,
                    WAVE_SECRET_KEY, VOTRE_NUMERO)

# ─── APP ─────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

DB = "commandes.db"

# ─── BASE DE DONNÉES ─────────────────────────────────────────────
def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS commandes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ref         TEXT UNIQUE NOT NULL,
                prenom      TEXT,
                telephone   TEXT NOT NULL,
                niveau      TEXT NOT NULL,
                montant     INTEGER NOT NULL,
                statut      TEXT DEFAULT 'en_attente',
                mode_paiement TEXT,
                wave_ref    TEXT,
                livree      INTEGER DEFAULT 0,
                cree_le     TEXT DEFAULT (datetime('now')),
                payee_le    TEXT,
                livree_le   TEXT
            )
        """)
        db.commit()

def generer_ref():
    import random, string
    return "ME-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ─── AUTH ADMIN ──────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ════════════════════════════════════════════════════════════════
# ROUTES CLIENT
# ════════════════════════════════════════════════════════════════

@app.route("/")
def accueil():
    return render_template("commande.html", prix=PRIX, noms=NOMS_NIVEAUX)


@app.route("/commander", methods=["POST"])
def commander():
    """Le client soumet sa commande → reçoit les instructions de paiement."""
    prenom    = request.form.get("prenom", "").strip()
    telephone = request.form.get("telephone", "").strip()
    niveau    = request.form.get("niveau", "").strip().lower()

    # Validation
    if not telephone or not niveau or niveau not in PRIX:
        flash("❌ Numéro de téléphone ou niveau invalide.", "error")
        return redirect(url_for("accueil"))

    montant = PRIX[niveau]
    ref     = generer_ref()

    with get_db() as db:
        db.execute("""
            INSERT INTO commandes (ref, prenom, telephone, niveau, montant)
            VALUES (?, ?, ?, ?, ?)
        """, (ref, prenom, telephone, niveau, montant))
        db.commit()

    # Envoyer instructions de paiement par WhatsApp
    envoyer_confirmation_attente(telephone, niveau, montant)
    log.info(f"📝 Nouvelle commande {ref} — {niveau} — {telephone}")

    return render_template("confirmation.html",
        ref=ref, prenom=prenom, niveau=NOMS_NIVEAUX[niveau],
        montant=montant, telephone=telephone)


# ════════════════════════════════════════════════════════════════
# WEBHOOK WAVE (paiement automatique)
# ════════════════════════════════════════════════════════════════

@app.route("/webhook/wave", methods=["POST"])
def webhook_wave():
    """
    Reçoit les notifications de paiement Wave Business.
    Wave envoie un POST JSON quand un paiement est reçu.
    """
    # Vérification signature Wave (si configurée)
    if WAVE_SECRET_KEY:
        sig = request.headers.get("X-Wave-Signature", "")
        payload = request.get_data()
        expected = hmac.new(WAVE_SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            log.warning("⚠️ Signature Wave invalide !")
            return jsonify({"error": "Invalid signature"}), 401

    data = request.get_json(silent=True) or {}
    log.info(f"📩 Webhook Wave reçu : {json.dumps(data, ensure_ascii=False)}")

    # Extraire les infos du paiement Wave
    # (adapter selon la structure réelle de l'API Wave Sénégal)
    statut    = data.get("status") or data.get("payment_status", "")
    montant   = int(data.get("amount", 0))
    wave_ref  = data.get("id") or data.get("reference", "")
    telephone = data.get("customer_phone") or data.get("sender_phone", "")
    message   = data.get("message") or data.get("description", "")

    if statut.lower() not in ("completed", "success", "paid"):
        return jsonify({"status": "ignored", "reason": "not paid"}), 200

    # Trouver la commande correspondante
    with get_db() as db:
        # Cherche d'abord par référence dans le message
        cmd = None
        for ref_tentative in _extraire_refs(message):
            row = db.execute(
                "SELECT * FROM commandes WHERE ref=? AND statut='en_attente'",
                (ref_tentative,)
            ).fetchone()
            if row:
                cmd = row
                break

        # Sinon par téléphone + montant
        if not cmd and telephone:
            cmd = db.execute("""
                SELECT * FROM commandes
                WHERE telephone LIKE ? AND montant=? AND statut='en_attente'
                ORDER BY cree_le DESC LIMIT 1
            """, (f"%{telephone[-8:]}%", montant)).fetchone()

        if not cmd:
            log.warning(f"⚠️ Commande introuvable pour Wave ref={wave_ref}")
            return jsonify({"status": "not_found"}), 200

        # Marquer comme payée
        db.execute("""
            UPDATE commandes SET statut='payee', wave_ref=?, payee_le=datetime('now')
            WHERE id=?
        """, (wave_ref, cmd["id"]))
        db.commit()

    # Livraison automatique
    succes = envoyer_livraison(cmd["telephone"], cmd["niveau"], cmd["prenom"])
    if succes:
        with get_db() as db:
            db.execute("""
                UPDATE commandes SET livree=1, livree_le=datetime('now') WHERE id=?
            """, (cmd["id"],))
            db.commit()
        log.info(f"🎉 Livraison auto OK — {cmd['ref']} → {cmd['telephone']}")
    else:
        log.error(f"❌ Échec livraison — {cmd['ref']} → {cmd['telephone']}")

    return jsonify({"status": "ok", "delivered": succes})


def _extraire_refs(texte: str) -> list:
    """Extrait les références ME-XXXXXX d'un texte."""
    import re
    return re.findall(r'ME-[A-Z0-9]{8}', texte.upper())


# ════════════════════════════════════════════════════════════════
# WEBHOOK ORANGE MONEY (si disponible)
# ════════════════════════════════════════════════════════════════

@app.route("/webhook/orange", methods=["POST"])
def webhook_orange():
    """Reçoit les notifications Orange Money."""
    data = request.get_json(silent=True) or {}
    log.info(f"📩 Webhook Orange Money : {data}")
    # Structure OM varie selon l'opérateur — adaptez selon votre contrat
    statut = data.get("status", "")
    if statut.lower() not in ("success", "successful"):
        return jsonify({"status": "ignored"}), 200
    # Même logique que Wave
    return jsonify({"status": "ok"}), 200


# ════════════════════════════════════════════════════════════════
# DASHBOARD ADMIN
# ════════════════════════════════════════════════════════════════

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("dashboard"))
        flash("❌ Mot de passe incorrect", "error")
    return render_template("login.html")

@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@login_required
def dashboard():
    with get_db() as db:
        commandes = db.execute("""
            SELECT * FROM commandes ORDER BY cree_le DESC LIMIT 100
        """).fetchall()
        stats = db.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN statut='payee' THEN 1 ELSE 0 END) as payees,
                SUM(CASE WHEN livree=1 THEN 1 ELSE 0 END) as livrees,
                SUM(CASE WHEN statut='payee' THEN montant ELSE 0 END) as revenu
            FROM commandes
        """).fetchone()
    return render_template("dashboard.html", commandes=commandes, stats=stats,
                           noms=NOMS_NIVEAUX)


@app.route("/admin/confirmer/<int:cmd_id>", methods=["POST"])
@login_required
def confirmer_paiement(cmd_id):
    """Confirmation manuelle d'un paiement (Wave/OM sans webhook)."""
    mode = request.form.get("mode", "manual")
    with get_db() as db:
        cmd = db.execute("SELECT * FROM commandes WHERE id=?", (cmd_id,)).fetchone()
        if not cmd:
            flash("Commande introuvable", "error")
            return redirect(url_for("dashboard"))
        db.execute("""
            UPDATE commandes SET statut='payee', mode_paiement=?, payee_le=datetime('now')
            WHERE id=?
        """, (mode, cmd_id))
        db.commit()

    # Livraison automatique
    succes = envoyer_livraison(cmd["telephone"], cmd["niveau"], cmd["prenom"])
    if succes:
        with get_db() as db:
            db.execute("UPDATE commandes SET livree=1, livree_le=datetime('now') WHERE id=?",
                       (cmd_id,))
            db.commit()
        flash(f"✅ Cahier livré automatiquement à {cmd['telephone']} !", "success")
    else:
        flash(f"⚠️ Paiement confirmé mais erreur WhatsApp — vérifiez manuellement.", "warning")
    return redirect(url_for("dashboard"))


@app.route("/admin/relancer/<int:cmd_id>", methods=["POST"])
@login_required
def relancer(cmd_id):
    """Renvoie le cahier au client (en cas de problème)."""
    with get_db() as db:
        cmd = db.execute("SELECT * FROM commandes WHERE id=?", (cmd_id,)).fetchone()
    if not cmd:
        flash("Commande introuvable", "error")
        return redirect(url_for("dashboard"))
    succes = envoyer_livraison(cmd["telephone"], cmd["niveau"], cmd["prenom"])
    if succes:
        flash(f"📬 Cahier renvoyé à {cmd['telephone']}", "success")
    else:
        flash("❌ Erreur d'envoi WhatsApp", "error")
    return redirect(url_for("dashboard"))


@app.route("/admin/nouvelle", methods=["GET", "POST"])
@login_required
def nouvelle_commande():
    """Saisie manuelle d'une commande depuis le dashboard admin."""
    if request.method == "POST":
        prenom    = request.form.get("prenom", "").strip()
        telephone = request.form.get("telephone", "").strip()
        niveau    = request.form.get("niveau", "").strip().lower()
        livre_now = request.form.get("livrer_maintenant") == "on"

        if not telephone or niveau not in PRIX:
            flash("Données invalides", "error")
            return redirect(url_for("nouvelle_commande"))

        ref     = generer_ref()
        montant = PRIX[niveau]
        statut  = "payee" if livre_now else "en_attente"

        with get_db() as db:
            db.execute("""
                INSERT INTO commandes (ref, prenom, telephone, niveau, montant, statut, mode_paiement)
                VALUES (?, ?, ?, ?, ?, ?, 'manual')
            """, (ref, prenom, telephone, niveau, montant, statut))
            db.commit()

        if livre_now:
            envoyer_livraison(telephone, niveau, prenom)
            flash(f"✅ Commande {ref} créée et cahier livré à {telephone} !", "success")
        else:
            envoyer_confirmation_attente(telephone, niveau, montant)
            flash(f"📝 Commande {ref} créée — instructions envoyées à {telephone}", "success")
        return redirect(url_for("dashboard"))

    return render_template("nouvelle_commande.html", prix=PRIX, noms=NOMS_NIVEAUX)


@app.route("/admin/stats")
@login_required
def stats():
    """Statistiques détaillées par niveau et par période."""
    with get_db() as db:
        par_niveau = db.execute("""
            SELECT niveau, COUNT(*) as nb, SUM(montant) as total
            FROM commandes WHERE statut='payee'
            GROUP BY niveau ORDER BY total DESC
        """).fetchall()
        par_jour = db.execute("""
            SELECT DATE(cree_le) as jour, COUNT(*) as nb, SUM(montant) as total
            FROM commandes WHERE statut='payee'
            GROUP BY jour ORDER BY jour DESC LIMIT 30
        """).fetchall()
    return render_template("stats.html", par_niveau=par_niveau,
                           par_jour=par_jour, noms=NOMS_NIVEAUX)


# ─── LANCEMENT ───────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
