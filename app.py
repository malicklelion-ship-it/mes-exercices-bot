import os
import logging
import random
import string
import re
from flask import Flask, request, jsonify, session, redirect, url_for, Response
from functools import wraps

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "mesexercices2025secret"

ADMIN_PASSWORD = "mesexercices2025"
WAVE_LINK = "https://pay.wave.com/m/M_sn_KPX6hNLZUljQ/c/sn/"
WHATSAPP_NUM = "221771343499"

PRIX = {
    "maternelle": 1000, "ci": 1000, "cp": 1000,
    "ce1": 1000, "ce2": 1000, "cm1": 1000, "cm2": 1000,
    "cem1": 1200, "cem2": 1500, "pack": 6000,
}
NOMS = {
    "maternelle": "Maternelle", "ci": "CI - Cours d'Initiation",
    "cp": "CP - Cours Preparatoire", "ce1": "CE1", "ce2": "CE2",
    "cm1": "CM1", "cm2": "CM2", "cem1": "CEM1 (6eme)",
    "cem2": "CEM2 (BFEM)", "pack": "Pack Complet (9 niveaux)",
}

commandes = []

def gen_ref():
    return "ME" + "".join(random.choices(string.digits, k=6))

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ============================================================
# WEBHOOK GREEN API — LIVRAISON AUTOMATIQUE
# ============================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Green API envoie ici tous les messages WhatsApp entrants.
    On cherche une reference MExxxxxx dans le message.
    Si trouvée → livraison automatique immédiate.
    """
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"status": "no data"}), 200

        log.info(f"Webhook recu: {str(data)[:200]}")

        # Extraire le texte du message et le numero expediteur
        body = data.get("body", {})
        type_webhook = data.get("typeWebhook", "")

        # Green API envoie les messages dans "incomingMessageReceived"
        if type_webhook != "incomingMessageReceived":
            return jsonify({"status": "ignored"}), 200

        message_data = body.get("messageData", {})
        text_message = message_data.get("textMessageData", {}).get("textMessage", "")
        sender_data = body.get("senderData", {})
        sender = sender_data.get("sender", "")  # ex: "221771234567@c.us"

        log.info(f"Message de {sender}: {text_message}")

        if not text_message:
            return jsonify({"status": "no text"}), 200

        # Chercher une reference MExxxxxx dans le message
        refs_trouvees = re.findall(r'ME\d{6}', text_message.upper())

        if not refs_trouvees:
            # Pas de reference — envoyer message d'aide
            numero = sender.replace("@c.us", "")
            from whatsapp import envoyer_message
            envoyer_message(numero,
                "Bonjour ! Pour confirmer votre paiement, envoyez votre "
                "reference de commande (ex: ME123456).\n"
                "Vous la trouvez sur la page de confirmation apres commande.\n"
                "Site : mes-exercices-bot.onrender.com"
            )
            return jsonify({"status": "no ref found"}), 200

        # Livrer pour chaque reference trouvee
        for ref in refs_trouvees:
            commande_trouvee = None
            for c in commandes:
                if c["ref"] == ref:
                    commande_trouvee = c
                    break

            if not commande_trouvee:
                log.warning(f"Reference {ref} non trouvee dans les commandes")
                numero = sender.replace("@c.us", "")
                from whatsapp import envoyer_message
                envoyer_message(numero,
                    f"Reference {ref} non trouvee.\n"
                    f"Verifiez la reference sur votre page de confirmation.\n"
                    f"Besoin d'aide ? Contactez +221 77 134 34 99"
                )
                continue

            if commande_trouvee["statut"] == "livre":
                log.info(f"Commande {ref} deja livree")
                numero = sender.replace("@c.us", "")
                from whatsapp import envoyer_livraison
                # Renvoyer quand meme
                envoyer_livraison(
                    commande_trouvee["telephone"],
                    commande_trouvee["nom"],
                    commande_trouvee["niveau"],
                    ref
                )
                continue

            # LIVRAISON AUTOMATIQUE !
            try:
                from whatsapp import envoyer_livraison
                envoyer_livraison(
                    commande_trouvee["telephone"],
                    commande_trouvee["nom"],
                    commande_trouvee["niveau"],
                    ref
                )
                commande_trouvee["statut"] = "livre"
                log.info(f"LIVRAISON AUTO OK: {ref} -> {commande_trouvee['telephone']}")
            except Exception as e:
                log.error(f"ERREUR LIVRAISON AUTO {ref}: {e}")
                import traceback
                log.error(traceback.format_exc())

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        log.error(f"ERREUR WEBHOOK: {e}")
        import traceback
        log.error(traceback.format_exc())
        return jsonify({"status": "error"}), 200

@app.route("/health")
def health():
    return jsonify({"status": "ok", "commandes": len(commandes)})

@app.route("/")
def index():
    return Response(MAIN_HTML, mimetype="text/html")

@app.route("/commander", methods=["POST"])
def commander():
    niveau = request.form.get("niveau")
    nom = request.form.get("nom")
    telephone = request.form.get("telephone")
    if not niveau or not nom or not telephone:
        return redirect("/")
    ref = gen_ref()
    prix = PRIX.get(niveau, 1000)
    commandes.append({
        "ref": ref, "niveau": niveau, "nom_niveau": NOMS.get(niveau, niveau),
        "nom": nom, "telephone": telephone, "prix": prix, "statut": "en_attente"
    })
    log.info(f"Commande: {ref} - {nom} - {niveau} - {prix} FCFA")
    msg_wa = (
        f"Bonjour+j%27ai+commande+le+cahier+"
        f"{NOMS.get(niveau,niveau).replace(' ','+')}+"
        f"ref+{ref}+montant+{prix}+FCFA"
    )
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paiement - MES EXERCICES</title>
<style>
:root{{--bleu:#1B3A6B;--jaune:#F5C518;--vert:#1A7A4A}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#FAFAF8;color:#1A1A18}}
nav{{background:var(--bleu);padding:0 24px;display:flex;align-items:center;height:56px}}
.nav-logo{{color:var(--jaune);font-size:15px;font-weight:800}}
.container{{max-width:520px;margin:32px auto;padding:0 16px}}
.card{{background:#fff;border-radius:14px;padding:28px;box-shadow:0 2px 16px rgba(0,0,0,0.08);margin-bottom:16px}}
.ref-box{{background:#EFF6FF;border:2px solid var(--bleu);border-radius:10px;padding:16px;text-align:center;margin-bottom:20px}}
.ref-box p{{font-size:13px;color:#666}}
.ref-box strong{{font-size:28px;color:var(--bleu);letter-spacing:3px;display:block;margin-top:4px;font-weight:800}}
.montant{{background:#FFFBEA;border:2px solid var(--jaune);border-radius:10px;padding:14px;text-align:center;margin-bottom:20px}}
.montant p{{font-size:13px;color:#666}}
.montant strong{{font-size:28px;color:#B8860B;display:block;margin-top:4px;font-weight:800}}
h3{{font-size:15px;font-weight:700;color:#1A1A18;margin-bottom:14px}}
.steps{{background:#F0F9F4;border-radius:10px;padding:16px;margin-bottom:20px}}
.step{{display:flex;gap:12px;align-items:flex-start;margin-bottom:12px}}
.step:last-child{{margin-bottom:0}}
.step-num{{width:28px;height:28px;border-radius:50%;background:var(--vert);color:#fff;font-size:13px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.step-text{{font-size:13px;line-height:1.5}}
.step-text strong{{display:block;font-weight:700;color:#1A1A18}}
.step-text span{{color:#666}}
.btn-wave{{display:flex;align-items:center;justify-content:center;gap:10px;background:#1565C0;color:white;padding:16px;border-radius:10px;text-decoration:none;font-size:15px;font-weight:700;margin-bottom:10px}}
.btn-om{{display:flex;align-items:center;justify-content:center;gap:10px;background:#FF6F00;color:white;padding:16px;border-radius:10px;border:none;cursor:pointer;font-size:15px;font-weight:700;width:100%;margin-bottom:10px}}
.om-box{{background:#FFF3E0;border-radius:10px;padding:16px;font-size:13px;line-height:1.9;display:none;margin-bottom:10px}}
.om-box code{{background:#FFE0B2;padding:4px 10px;border-radius:6px;font-size:14px;font-weight:700;display:inline-block}}
.btn-wa{{display:flex;align-items:center;justify-content:center;gap:10px;background:#25D366;color:white;padding:16px;border-radius:10px;text-decoration:none;font-size:15px;font-weight:800}}
.auto-badge{{background:#E8F5E9;border:1px solid #4CAF50;border-radius:8px;padding:12px;font-size:12px;color:#2E7D32;text-align:center;margin-bottom:14px;line-height:1.6}}
</style>
</head>
<body>
<nav><div class="nav-logo">📚 MES EXERCICES</div></nav>
<div class="container">
  <div class="card">
    <div class="ref-box">
      <p>Votre reference de commande</p>
      <strong>{ref}</strong>
    </div>
    <div class="montant">
      <p>{NOMS.get(niveau,niveau)}</p>
      <strong>{prix:,} FCFA</strong>
    </div>

    <div class="auto-badge">
      ⚡ <strong>Livraison 100% automatique !</strong><br>
      Apres paiement, cliquez le bouton WhatsApp ci-dessous.<br>
      Votre cahier sera envoye <strong>instantanement</strong> !
    </div>

    <h3>1. Payez maintenant</h3>
    <a href="{WAVE_LINK}" class="btn-wave" target="_blank">
      💙 Payer avec Wave
    </a>
    <button class="btn-om" onclick="toggleOM()">
      🟠 Payer avec Orange Money
    </button>
    <div class="om-box" id="om-box">
      <strong>Option 1 — Par telephone :</strong><br>
      Composez : <code>*144*2*{WHATSAPP_NUM}*{prix}#</code><br>
      Validez avec votre code PIN<br><br>
      <strong>Option 2 — App Orange Money :</strong><br>
      Transfert → Numero : <code>77 134 34 99</code><br>
      Montant : <code>{prix} FCFA</code>
    </div>

    <h3 style="margin-top:20px">2. Confirmez et recevez votre cahier</h3>
    <a href="https://wa.me/{WHATSAPP_NUM}?text=Bonjour+j%27ai+paye+ma+commande+ref+{ref}+montant+{prix}+FCFA" 
       class="btn-wa" target="_blank">
      💬 Envoyer la confirmation WhatsApp
    </a>
    <p style="font-size:12px;color:#999;text-align:center;margin-top:8px">
      → Cliquez ce bouton apres avoir paye<br>
      → Le message est pre-rempli avec votre reference<br>
      → Votre cahier arrive automatiquement en moins de 2 minutes !
    </p>
  </div>
</div>
<script>
function toggleOM(){{
  var b=document.getElementById('om-box');
  b.style.display=b.style.display==='block'?'none':'block';
}}
</script>
</body>
</html>"""
    return html

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        error = "Mot de passe incorrect"
    return Response(f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Admin</title>
<style>
body{{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;
justify-content:center;align-items:center;min-height:100vh;margin:0}}
.card{{background:#fff;border-radius:12px;padding:30px;width:320px}}
h2{{text-align:center;color:#1B3A6B;margin-bottom:20px}}
input{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;
margin-bottom:14px;font-size:14px;box-sizing:border-box}}
button{{width:100%;background:#1B3A6B;color:#fff;border:none;padding:12px;
border-radius:6px;font-size:15px;cursor:pointer}}
.err{{color:red;font-size:13px;margin-bottom:10px}}
</style></head><body>
<div class="card">
  <h2>🔒 Admin MES EXERCICES</h2>
  {'<p class="err">'+error+'</p>' if error else ''}
  <form method="POST">
    <input type="password" name="password" placeholder="Mot de passe" required autofocus>
    <button>Se connecter</button>
  </form>
</div></body></html>""", mimetype="text/html")

@app.route("/admin")
@login_required
def admin():
    rows = ""
    for c in reversed(commandes):
        sc = "#4caf50" if c["statut"] == "livre" else "#ff9800"
        st = "Livre ✅" if c["statut"] == "livre" else "En attente ⏳"
        rows += f"""<tr>
<td><strong>{c['ref']}</strong></td><td>{c['nom']}</td>
<td>{c['telephone']}</td><td>{c['nom_niveau']}</td>
<td>{c['prix']:,} F</td>
<td><span style="background:{sc};color:#fff;padding:3px 8px;border-radius:4px;font-size:11px">{st}</span></td>
<td>"""
        if c["statut"] != "livre":
            rows += f'<a href="/admin/livrer/{c["ref"]}" style="background:#1B3A6B;color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;text-decoration:none;margin-right:4px">Livrer</a>'
        rows += f'<a href="/admin/renvoyer/{c["ref"]}" style="background:#1A7A4A;color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;text-decoration:none">Renvoyer</a>'
        rows += "</td></tr>"
    total = len(commandes)
    livres = sum(1 for c in commandes if c["statut"] == "livre")
    attente = total - livres
    ca = sum(c["prix"] for c in commandes if c["statut"] == "livre")
    return Response(f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="20">
<title>Dashboard - MES EXERCICES</title>
<style>
:root{{--bleu:#1B3A6B;--jaune:#F5C518}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#f0f4f8}}
header{{background:var(--bleu);color:#fff;padding:15px 20px;
display:flex;justify-content:space-between;align-items:center}}
header h1{{font-size:17px}}
.logout{{color:#F5C518;text-decoration:none;font-size:13px}}
.webhook-status{{background:#E8F5E9;border:1px solid #4CAF50;
padding:10px 20px;font-size:13px;color:#2E7D32;text-align:center}}
.stats{{display:flex;gap:12px;padding:20px;flex-wrap:wrap}}
.stat{{background:#fff;border-radius:8px;padding:15px;flex:1;
min-width:100px;text-align:center;box-shadow:0 2px 5px rgba(0,0,0,.08)}}
.stat .n{{font-size:26px;font-weight:800;color:var(--bleu)}}
.stat .l{{font-size:11px;color:#666;margin-top:2px}}
.stat.ok .n{{color:#1A7A4A}}
.stat.warn .n{{color:#ff9800}}
.stat.money .n{{color:#B8860B}}
.cont{{padding:0 20px 20px}}
.new-btn{{display:inline-block;background:var(--jaune);color:var(--bleu);
padding:10px 20px;border-radius:6px;text-decoration:none;
font-weight:700;margin-bottom:14px;font-size:14px}}
table{{width:100%;border-collapse:collapse;background:#fff;
border-radius:8px;overflow:hidden;box-shadow:0 2px 5px rgba(0,0,0,.08);
font-size:12px}}
th{{background:var(--bleu);color:#fff;padding:10px;text-align:left}}
td{{padding:10px;border-bottom:1px solid #f0f0f0}}
.empty{{text-align:center;padding:40px;color:#999;background:#fff;border-radius:8px}}
</style></head>
<body>
<header>
  <h1>📚 MES EXERCICES — Dashboard</h1>
  <a href="/admin/logout" class="logout">Déconnexion</a>
</header>
<div class="webhook-status">
  ⚡ Livraison automatique ACTIVE — Les cahiers sont livrés dès que le client confirme sur WhatsApp
</div>
<div class="stats">
  <div class="stat warn"><div class="n">{attente}</div><div class="l">En attente</div></div>
  <div class="stat ok"><div class="n">{livres}</div><div class="l">Livrees auto</div></div>
  <div class="stat"><div class="n">{total}</div><div class="l">Total</div></div>
  <div class="stat money"><div class="n">{ca:,} F</div><div class="l">CA total</div></div>
</div>
<div class="cont">
  <a href="/admin/nouvelle" class="new-btn">+ Commande manuelle</a>
  {'<table><thead><tr><th>Réf</th><th>Nom</th><th>Tél</th><th>Niveau</th><th>Prix</th><th>Statut</th><th>Actions</th></tr></thead><tbody>'+rows+'</tbody></table>' if commandes else '<div class="empty">Aucune commande — Les livraisons se font automatiquement via WhatsApp ⚡</div>'}
</div>
</body></html>""", mimetype="text/html")

@app.route("/admin/livrer/<ref>")
@login_required
def livrer(ref):
    for c in commandes:
        if c["ref"] == ref:
            try:
                from whatsapp import envoyer_livraison
                envoyer_livraison(c["telephone"], c["nom"], c["niveau"], c["ref"])
                c["statut"] = "livre"
                log.info(f"Livraison manuelle OK: {ref}")
            except Exception as e:
                log.error(f"ERREUR: {e}")
            break
    return redirect(url_for("admin"))

@app.route("/admin/renvoyer/<ref>")
@login_required
def renvoyer(ref):
    for c in commandes:
        if c["ref"] == ref:
            try:
                from whatsapp import envoyer_livraison
                envoyer_livraison(c["telephone"], c["nom"], c["niveau"], c["ref"])
            except Exception as e:
                log.error(f"ERREUR: {e}")
            break
    return redirect(url_for("admin"))

@app.route("/admin/nouvelle", methods=["GET", "POST"])
@login_required
def nouvelle():
    if request.method == "POST":
        niveau = request.form.get("niveau")
        ref = gen_ref()
        commandes.append({
            "ref": ref, "niveau": niveau, "nom_niveau": NOMS.get(niveau, niveau),
            "nom": request.form.get("nom"),
            "telephone": request.form.get("telephone"),
            "prix": PRIX.get(niveau, 0), "statut": "en_attente"
        })
        return redirect(url_for("admin"))
    opts = "".join([f'<option value="{k}">{v} — {PRIX[k]:,} F</option>' for k,v in NOMS.items()])
    return Response(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Nouvelle commande</title>
<style>
body{{font-family:Arial,sans-serif;background:#f0f4f8;
display:flex;justify-content:center;padding:30px 15px}}
.card{{background:#fff;border-radius:10px;padding:24px;
max-width:400px;width:100%;box-shadow:0 2px 10px rgba(0,0,0,.1)}}
h2{{color:#1B3A6B;margin-bottom:18px}}
label{{display:block;margin-bottom:5px;font-weight:700;font-size:13px}}
select,input{{width:100%;padding:10px;border:1px solid #ddd;
border-radius:6px;font-size:14px;margin-bottom:14px}}
button{{width:100%;background:#1B3A6B;color:#fff;border:none;
padding:12px;border-radius:6px;font-size:15px;cursor:pointer}}
a{{display:block;text-align:center;margin-top:10px;color:#666;font-size:13px;text-decoration:none}}
</style></head><body>
<div class="card">
  <h2>Nouvelle commande manuelle</h2>
  <form method="POST">
    <label>Niveau</label><select name="niveau">{opts}</select>
    <label>Nom client</label><input name="nom" placeholder="Fatou Diallo" required>
    <label>Telephone WhatsApp</label>
    <input name="telephone" placeholder="221771234567" required>
    <button>Enregistrer</button>
  </form>
  <a href="/admin">← Retour</a>
</div></body></html>""", mimetype="text/html")

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

MAIN_HTML = open("index_template.html").read() if os.path.exists("index_template.html") else """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MES EXERCICES</title>
<style>
:root{--bleu:#1B3A6B;--jaune:#F5C518;--vert:#1A7A4A}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#FAFAF8}
nav{background:var(--bleu);padding:0 24px;display:flex;align-items:center;justify-content:space-between;height:56px;position:sticky;top:0;z-index:100}
.nav-logo{color:var(--jaune);font-size:15px;font-weight:800}
.hero{background:var(--bleu);padding:60px 24px 70px;text-align:center}
.hero h1{color:#fff;font-size:clamp(28px,5vw,48px);font-weight:800;margin-bottom:16px}
.hero h1 em{color:var(--jaune);font-style:normal}
.hero p{color:rgba(255,255,255,.8);font-size:16px;max-width:500px;margin:0 auto 32px}
.btn-cta{background:var(--jaune);color:var(--bleu);font-weight:800;font-size:15px;padding:15px 28px;border-radius:10px;border:none;cursor:pointer;text-decoration:none;display:inline-block}
.section{max-width:900px;margin:0 auto;padding:48px 20px}
.section h2{font-size:26px;font-weight:800;color:var(--bleu);margin-bottom:24px;text-align:center}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin-bottom:32px}
.card{background:#fff;border:1.5px solid #E8E8E6;border-radius:12px;padding:18px;cursor:pointer;transition:all .15s}
.card:hover{border-color:var(--bleu);transform:translateY(-2px);box-shadow:0 8px 24px rgba(27,58,107,.1)}
.card.pack{border-color:var(--jaune);grid-column:1/-1;background:#FFFBEA}
.niveau{font-size:11px;font-weight:700;background:#EFF6FF;color:var(--bleu);padding:3px 10px;border-radius:20px;display:inline-block;margin-bottom:8px}
.card h3{font-size:14px;font-weight:700;margin-bottom:4px}
.card p{font-size:12px;color:#666;margin-bottom:10px}
.price{font-size:20px;font-weight:800;color:var(--bleu);margin-bottom:10px}
.pack .price{color:#B8860B}
.btn-card{width:100%;padding:10px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:700;background:var(--bleu);color:#fff}
.pack .btn-card{background:var(--jaune);color:var(--bleu)}
/* Formulaire integre */
.commande-section{background:var(--bleu);padding:60px 24px}
.commande-inner{max-width:860px;margin:0 auto}
.commande-title{color:#fff;font-size:clamp(22px,3vw,34px);font-weight:800;text-align:center;margin-bottom:6px}
.commande-sub{color:rgba(255,255,255,.7);text-align:center;font-size:14px;margin-bottom:36px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px}
@media(max-width:640px){.form-grid{grid-template-columns:1fr}}
.form-card{background:#fff;border-radius:14px;padding:24px}
.form-card h3{font-size:16px;font-weight:700;color:var(--bleu);margin-bottom:18px}
.niveaux-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
.niv-btn{border:2px solid #E0E0E0;border-radius:8px;padding:10px 8px;cursor:pointer;text-align:center;background:#fff;transition:all .15s}
.niv-btn:hover,.niv-btn.sel{border-color:var(--bleu);background:#EFF6FF}
.niv-btn .nn{font-weight:700;font-size:12px}
.niv-btn .np{color:var(--bleu);font-size:11px;margin-top:2px}
.pack-btn{grid-column:1/-1;border-color:var(--jaune);background:#FFFBEA}
.pack-btn.sel{border-color:#B8860B}
.recap{background:#EFF6FF;border-radius:8px;padding:12px;margin-bottom:14px;display:none;font-size:13px}
.recap strong{color:var(--bleu);font-size:18px}
label{display:block;margin-bottom:4px;font-weight:600;font-size:13px}
input,select{width:100%;padding:10px;border:1.5px solid #E0E0E0;border-radius:8px;font-size:14px;margin-bottom:12px}
.btn-commander{width:100%;background:var(--jaune);color:var(--bleu);border:none;padding:14px;border-radius:10px;font-size:15px;font-weight:800;cursor:pointer}
.info-card{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.2);border-radius:14px;padding:24px;color:#fff}
.info-card h3{font-size:16px;font-weight:700;color:var(--jaune);margin-bottom:18px}
.step{display:flex;gap:12px;align-items:flex-start;margin-bottom:16px}
.step-n{width:30px;height:30px;border-radius:50%;background:var(--jaune);color:var(--bleu);font-size:13px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.step-t strong{display:block;font-size:13px;font-weight:700;margin-bottom:2px}
.step-t span{font-size:12px;color:rgba(255,255,255,.7)}
.auto-badge-hero{background:#E8F5E9;border:1px solid #4CAF50;border-radius:8px;padding:10px 16px;font-size:13px;color:#1B5E20;text-align:center;margin:16px 0;font-weight:600}
footer{background:#1A1A18;color:rgba(255,255,255,.6);padding:32px 24px;text-align:center;font-size:13px}
.footer-logo{color:var(--jaune);font-size:16px;font-weight:800;margin-bottom:8px}
.wa-float{position:fixed;bottom:24px;right:24px;background:#25D366;color:#fff;width:54px;height:54px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:24px;text-decoration:none;box-shadow:0 4px 16px rgba(0,0,0,.3);z-index:999}
</style>
</head>
<body>
<nav>
  <div class="nav-logo">📚 MES EXERCICES</div>
  <a href="#commander" style="background:var(--jaune);color:var(--bleu);padding:8px 16px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:700">Commander →</a>
</nav>

<div class="hero">
  <h1>Les <em>meilleures méthodes du monde</em><br>pour vos enfants</h1>
  <p>🇫🇮 Finlande · 🇸🇬 Singapour · 🇯🇵 Japon · Montessori · France MEN<br>Adaptées au programme sénégalais · Maternelle → BFEM</p>
  <a href="#commander" class="btn-cta">📚 Commander maintenant →</a>
</div>

<div class="section" id="cahiers">
  <h2>9 cahiers — Un pour chaque niveau</h2>
  <div class="grid">
    <div class="card" onclick="scrollCommander('maternelle')"><div class="niveau">Maternelle · 4-6 ans</div><h3>📚 Cahier Maternelle</h3><p>Lettres, chiffres, formes. Méthode Montessori.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="scrollCommander('ci')"><div class="niveau">CI · 6-7 ans</div><h3>📚 Cahier CI</h3><p>Lecture syllabique, additions. Jolly Phonics.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="scrollCommander('cp')"><div class="niveau">CP · 6-7 ans</div><h3>📚 Cahier CP</h3><p>Lecture complète, soustraction. France MEN.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="scrollCommander('ce1')"><div class="niveau">CE1 · 7-8 ans</div><h3>📚 Cahier CE1</h3><p>Tables de multiplication. Singapour Math.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="scrollCommander('ce2')"><div class="niveau">CE2 · 8-9 ans</div><h3>📚 Cahier CE2</h3><p>Division, compréhension. Méthode Japon.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="scrollCommander('cm1')"><div class="niveau">CM1 · 9-10 ans</div><h3>📚 Cahier CM1</h3><p>Géométrie, fractions. Common Core USA.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="scrollCommander('cm2')"><div class="niveau">CM2 · CFEE</div><h3>📚 Cahier CM2</h3><p>Préparation CFEE complète.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="scrollCommander('cem1')"><div class="niveau">CEM1 · 6ème</div><h3>📚 Cahier CEM1</h3><p>Algèbre, littérature, biologie.</p><div class="price">1 200 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="scrollCommander('cem2')"><div class="niveau">CEM2 · BFEM ⭐</div><h3>📚 Cahier CEM2</h3><p>Préparation BFEM. Épreuves types.</p><div class="price">1 500 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card pack" onclick="scrollCommander('pack')"><div class="niveau" style="background:#FFF3CD;color:#B8860B">🔥 MEILLEUR CHOIX -44%</div><h3>📚 Pack Complet — 9 niveaux</h3><p>Tous les cahiers en un seul achat. Économisez 4 700 FCFA !</p><div class="price">6 000 FCFA <span style="font-size:13px;color:#999;text-decoration:line-through">10 700 FCFA</span></div><button class="btn-card">Commander le Pack →</button></div>
  </div>
</div>

<section class="commande-section" id="commander">
  <div class="commande-inner">
    <div class="commande-title">📚 Commander votre cahier</div>
    <div class="commande-sub">Payez avec Wave ou Orange Money — Reçu sur WhatsApp en 2 minutes !</div>
    <div class="form-grid">
      <div class="form-card">
        <h3>Choisissez votre niveau</h3>
        <form method="POST" action="/commander">
          <div class="niveaux-grid">
            <div class="niv-btn" id="btn-maternelle" onclick="choisir('maternelle',this)"><div class="nn">Maternelle</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-ci" onclick="choisir('ci',this)"><div class="nn">CI</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-cp" onclick="choisir('cp',this)"><div class="nn">CP</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-ce1" onclick="choisir('ce1',this)"><div class="nn">CE1</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-ce2" onclick="choisir('ce2',this)"><div class="nn">CE2</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-cm1" onclick="choisir('cm1',this)"><div class="nn">CM1</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-cm2" onclick="choisir('cm2',this)"><div class="nn">CM2</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-cem1" onclick="choisir('cem1',this)"><div class="nn">CEM1</div><div class="np">1 200 F</div></div>
            <div class="niv-btn" id="btn-cem2" onclick="choisir('cem2',this)"><div class="nn">CEM2 BFEM</div><div class="np">1 500 F</div></div>
            <div class="niv-btn pack-btn" id="btn-pack" onclick="choisir('pack',this)"><div class="nn">🔥 Pack 9 niveaux</div><div class="np">6 000 F (-44%)</div></div>
          </div>
          <input type="hidden" name="niveau" id="niveau_input" required>
          <div class="recap" id="recap">
            Niveau : <span id="recap_nom"></span><br>
            Montant : <strong id="recap_prix"></strong>
          </div>
          <label>Votre prénom et nom</label>
          <input type="text" name="nom" placeholder="Fatou Diallo" required>
          <label>Votre numéro WhatsApp</label>
          <input type="tel" name="telephone" placeholder="221771234567" required>
          <button type="submit" class="btn-commander">✅ Commander →</button>
        </form>
      </div>
      <div class="info-card">
        <h3>⚡ Comment ça marche ?</h3>
        <div class="step"><div class="step-n">1</div><div class="step-t"><strong>Choisissez et commandez</strong><span>Sélectionnez votre niveau et remplissez le formulaire</span></div></div>
        <div class="step"><div class="step-n">2</div><div class="step-t"><strong>Payez Wave ou Orange Money</strong><span>Lien direct Wave ou code *144# Orange Money</span></div></div>
        <div class="step"><div class="step-n">3</div><div class="step-t"><strong>Envoyez la confirmation</strong><span>Cliquez le bouton WhatsApp pré-rempli avec votre référence</span></div></div>
        <div class="step"><div class="step-n">4</div><div class="step-t"><strong>Recevez en 2 minutes !</strong><span>Votre cahier PDF arrive automatiquement sur WhatsApp</span></div></div>
        <div class="auto-badge-hero">⚡ Livraison 100% automatique dès confirmation WhatsApp</div>
        <div style="font-size:13px;color:rgba(255,255,255,.8);margin-top:12px">
          💙 Wave · 🟠 Orange Money<br>
          📞 <strong style="color:#fff">+221 77 134 34 99</strong><br>
          <span style="font-size:11px;opacity:.6">Disponible 7j/7</span>
        </div>
      </div>
    </div>
  </div>
</section>

<footer>
  <div class="footer-logo">📚 MES EXERCICES</div>
  <div>Les meilleures méthodes du monde · Pour chaque enfant du Sénégal 🇸🇳</div>
  <div style="margin-top:10px">
    <a href="https://wa.me/221771343499" style="color:var(--jaune)">WhatsApp</a> ·
    <a href="tel:+221771343499" style="color:var(--jaune)">+221 77 134 34 99</a>
  </div>
</footer>

<a href="https://wa.me/221771343499" class="wa-float">💬</a>

<script>
var prix={"maternelle":1000,"ci":1000,"cp":1000,"ce1":1000,"ce2":1000,"cm1":1000,"cm2":1000,"cem1":1200,"cem2":1500,"pack":6000};
var noms={"maternelle":"Maternelle","ci":"CI","cp":"CP","ce1":"CE1","ce2":"CE2","cm1":"CM1","cm2":"CM2","cem1":"CEM1","cem2":"CEM2 BFEM","pack":"Pack Complet"};
function choisir(n,el){
  document.querySelectorAll('.niv-btn').forEach(b=>b.classList.remove('sel'));
  el.classList.add('sel');
  document.getElementById('niveau_input').value=n;
  document.getElementById('recap_nom').textContent=noms[n];
  document.getElementById('recap_prix').textContent=prix[n].toLocaleString()+' FCFA';
  document.getElementById('recap').style.display='block';
}
function scrollCommander(n){
  document.getElementById('commander').scrollIntoView({behavior:'smooth'});
  setTimeout(function(){var el=document.getElementById('btn-'+n);if(el)choisir(n,el);},600);
}
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
