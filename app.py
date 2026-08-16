import os
import logging
import random
import string
import re
import threading
import time
import requests
from flask import Flask, request, jsonify, session, redirect, url_for, Response
from functools import wraps

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "mesexercices2025secret"

ADMIN_PASSWORD = "mesexercices2025"
WAVE_LINK = "https://pay.wave.com/m/M_sn_KPX6hNLZUljQ/c/sn/"
WHATSAPP_NUM = "221771343499"

# Green API
GREEN_INSTANCE = "710722708786"
GREEN_TOKEN    = "219438e83e1a4e929a867f34e27565a560c00bb08f6a4a6089"
GREEN_BASE     = f"https://7107.api.greenapi.com/waInstance{GREEN_INSTANCE}"

PRIX = {
    "maternelle":1000,"ci":1000,"cp":1000,"ce1":1000,"ce2":1000,
    "cm1":1000,"cm2":1000,"cem1":1200,"cem2":1500,"pack":6000,
}
NOMS = {
    "maternelle":"Maternelle","ci":"CI - Cours d'Initiation",
    "cp":"CP - Cours Preparatoire","ce1":"CE1","ce2":"CE2",
    "cm1":"CM1","cm2":"CM2","cem1":"CEM1 (6eme)",
    "cem2":"CEM2 (BFEM)","pack":"Pack Complet (9 niveaux)",
}

commandes = []
messages_traites = set()  # eviter de traiter le meme message 2x

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
# LIVRAISON WHATSAPP
# ============================================================
def envoyer_message(telephone, texte):
    numero = telephone.strip().replace("+","").replace(" ","")
    if not numero.endswith("@c.us"):
        numero += "@c.us"
    try:
        r = requests.post(
            f"{GREEN_BASE}/sendMessage/{GREEN_TOKEN}",
            json={"chatId": numero, "message": texte},
            timeout=15
        )
        log.info(f"Message envoye {telephone}: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        log.error(f"Erreur envoi message: {e}")
        return False

def livrer_commande(commande):
    """Envoie le PDF par WhatsApp et marque comme livre"""
    from whatsapp import envoyer_livraison
    envoyer_livraison(
        commande["telephone"],
        commande["nom"],
        commande["niveau"],
        commande["ref"]
    )
    commande["statut"] = "livre"
    log.info(f"✅ LIVRE AUTO: {commande['ref']} -> {commande['telephone']}")

def traiter_message(texte, expediteur):
    """Cherche une reference MExxxxxx et livre automatiquement"""
    refs = re.findall(r'ME\d{6}', texte.upper())
    if not refs:
        return False

    livre = False
    for ref in refs:
        for c in commandes:
            if c["ref"] == ref:
                if c["statut"] != "livre":
                    try:
                        livrer_commande(c)
                        livre = True
                    except Exception as e:
                        log.error(f"Erreur livraison auto {ref}: {e}")
                else:
                    # Deja livre — renvoyer quand meme
                    try:
                        from whatsapp import envoyer_livraison
                        envoyer_livraison(c["telephone"],c["nom"],c["niveau"],c["ref"])
                        livre = True
                    except:
                        pass
    return livre

# ============================================================
# POLLING — LECTURE DES MESSAGES TOUTES LES 10 SECONDES
# ============================================================
def polling_whatsapp():
    """
    Lit les messages entrants via Green API receiveNotification.
    Tourne en arriere-plan toutes les 10 secondes.
    """
    log.info("🔄 Polling WhatsApp demarre...")
    while True:
        try:
            # receiveNotification retourne 1 message a la fois
            r = requests.get(
                f"{GREEN_BASE}/receiveNotification/{GREEN_TOKEN}",
                timeout=10
            )
            if r.status_code != 200:
                time.sleep(10)
                continue

            data = r.json()
            if not data:
                time.sleep(5)
                continue

            receipt_id = data.get("receiptId")
            body = data.get("body", {})
            type_webhook = body.get("typeWebhook", "")

            # Marquer comme lu pour ne pas le retraiter
            if receipt_id:
                requests.delete(
                    f"{GREEN_BASE}/deleteNotification/{GREEN_TOKEN}/{receipt_id}",
                    timeout=5
                )

            # On traite seulement les messages entrants
            if type_webhook != "incomingMessageReceived":
                continue

            msg_id = body.get("idMessage", "")
            if msg_id in messages_traites:
                continue
            messages_traites.add(msg_id)

            # Extraire le texte
            message_data = body.get("messageData", {})
            texte = message_data.get("textMessageData", {}).get("textMessage", "")
            sender_data = body.get("senderData", {})
            expediteur = sender_data.get("sender", "").replace("@c.us","")

            if not texte:
                continue

            log.info(f"📩 Message recu de {expediteur}: {texte[:80]}")

            # Chercher et livrer
            traiter_message(texte, expediteur)

        except Exception as e:
            log.error(f"Erreur polling: {e}")
            time.sleep(15)

        time.sleep(3)  # attendre 3s avant le prochain message

def demarrer_polling():
    """Demarre le polling en thread background"""
    t = threading.Thread(target=polling_whatsapp, daemon=True)
    t.start()
    log.info("✅ Thread polling WhatsApp demarre")

# ============================================================
# ROUTES FLASK
# ============================================================
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "commandes": len(commandes),
        "livrees": sum(1 for c in commandes if c["statut"]=="livre"),
        "polling": "actif"
    })

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
        "ref":ref,"niveau":niveau,"nom_niveau":NOMS.get(niveau,niveau),
        "nom":nom,"telephone":telephone,"prix":prix,"statut":"en_attente"
    })
    log.info(f"Commande: {ref} - {nom} - {niveau} - {prix} FCFA")

    msg_wa = (
        f"Bonjour+j%27ai+paye+ma+commande+"
        f"ref+{ref}+montant+{prix}+FCFA"
    )
    html = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paiement - MES EXERCICES</title>
<style>
:root{{--bleu:#1B3A6B;--jaune:#F5C518;--vert:#1A7A4A}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#FAFAF8}}
nav{{background:var(--bleu);padding:0 24px;display:flex;align-items:center;height:56px}}
.logo{{color:var(--jaune);font-size:15px;font-weight:800}}
.container{{max-width:500px;margin:28px auto;padding:0 16px}}
.card{{background:#fff;border-radius:14px;padding:26px;box-shadow:0 2px 16px rgba(0,0,0,.08);margin-bottom:14px}}
.ref-box{{background:#EFF6FF;border:2px solid var(--bleu);border-radius:10px;padding:16px;text-align:center;margin-bottom:18px}}
.ref-box p{{font-size:13px;color:#666;margin-bottom:4px}}
.ref-box strong{{font-size:30px;color:var(--bleu);letter-spacing:3px;font-weight:800;display:block}}
.montant{{background:#FFFBEA;border:2px solid var(--jaune);border-radius:10px;padding:14px;text-align:center;margin-bottom:18px}}
.montant p{{font-size:13px;color:#666}}
.montant strong{{font-size:28px;color:#B8860B;font-weight:800;display:block;margin-top:4px}}
.auto-info{{background:#E8F5E9;border:1px solid #4CAF50;border-radius:10px;padding:14px;margin-bottom:18px;font-size:13px;color:#1B5E20;text-align:center;line-height:1.7}}
h3{{font-size:15px;font-weight:700;color:#1A1A18;margin-bottom:14px}}
.btn-wave{{display:flex;align-items:center;justify-content:center;gap:8px;background:#1565C0;color:#fff;padding:16px;border-radius:10px;text-decoration:none;font-size:15px;font-weight:700;margin-bottom:10px}}
.btn-om{{display:flex;align-items:center;justify-content:center;gap:8px;background:#FF6F00;color:#fff;padding:16px;border-radius:10px;border:none;cursor:pointer;font-size:15px;font-weight:700;width:100%;margin-bottom:10px}}
.om-box{{background:#FFF3E0;border-radius:10px;padding:16px;font-size:13px;line-height:1.9;display:none;margin-bottom:10px}}
.om-box code{{background:#FFE0B2;padding:4px 10px;border-radius:6px;font-size:14px;font-weight:700;display:inline-block}}
.btn-wa{{display:flex;align-items:center;justify-content:center;gap:8px;background:#25D366;color:#fff;padding:16px;border-radius:10px;text-decoration:none;font-size:15px;font-weight:800}}
.note{{font-size:11px;color:#999;text-align:center;margin-top:8px;line-height:1.6}}
</style>
</head>
<body>
<nav><div class="logo">📚 MES EXERCICES</div></nav>
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
  <div class="auto-info">
    ⚡ <strong>Livraison 100% automatique !</strong><br>
    Payez → Cliquez le bouton WhatsApp ci-dessous<br>
    → Votre cahier arrive en moins de 2 minutes !
  </div>
  <h3>Etape 1 — Payez maintenant</h3>
  <a href="{WAVE_LINK}" class="btn-wave" target="_blank">💙 Payer avec Wave</a>
  <button class="btn-om" onclick="document.getElementById('om').style.display=document.getElementById('om').style.display=='block'?'none':'block'">🟠 Payer avec Orange Money</button>
  <div class="om-box" id="om">
    <strong>Composez :</strong><br>
    <code>*144*2*{WHATSAPP_NUM}*{prix}#</code><br>
    Ou dans l'app : Transfert → <code>77 134 34 99</code> → <code>{prix} FCFA</code>
  </div>
  <h3>Etape 2 — Confirmez et recevez</h3>
  <a href="https://wa.me/{WHATSAPP_NUM}?text=Bonjour+j%27ai+paye+ma+commande+ref+{ref}+montant+{prix}+FCFA" 
     class="btn-wa" target="_blank">
    💬 Envoyer confirmation WhatsApp
  </a>
  <p class="note">
    → Le message est pre-rempli avec votre reference <strong>{ref}</strong><br>
    → Envoyez-le apres avoir paye<br>
    → Votre cahier PDF arrive automatiquement !
  </p>
</div>
</div>
</body></html>"""
    return html

@app.route("/admin/login", methods=["GET","POST"])
def login():
    error=""
    if request.method=="POST":
        if request.form.get("password")==ADMIN_PASSWORD:
            session["admin"]=True
            return redirect(url_for("admin"))
        error="Mot de passe incorrect"
    return Response(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Admin</title>
<style>body{{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}}
.c{{background:#fff;border-radius:12px;padding:30px;width:320px}}
h2{{text-align:center;color:#1B3A6B;margin-bottom:20px}}
input{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;margin-bottom:14px;font-size:14px;box-sizing:border-box}}
button{{width:100%;background:#1B3A6B;color:#fff;border:none;padding:12px;border-radius:6px;font-size:15px;cursor:pointer}}
.e{{color:red;font-size:13px;margin-bottom:10px}}</style>
</head><body><div class="c">
<h2>🔒 Admin MES EXERCICES</h2>
{'<p class="e">'+error+'</p>' if error else ''}
<form method="POST">
<input type="password" name="password" placeholder="Mot de passe" required autofocus>
<button>Se connecter</button>
</form></div></body></html>""",mimetype="text/html")

@app.route("/admin")
@login_required
def admin():
    rows=""
    for c in reversed(commandes):
        sc="#4caf50" if c["statut"]=="livre" else "#ff9800"
        st="✅ Livre auto" if c["statut"]=="livre" else "⏳ En attente"
        rows+=f"""<tr>
<td><strong>{c['ref']}</strong></td><td>{c['nom']}</td>
<td>{c['telephone']}</td><td>{c['nom_niveau']}</td>
<td>{c['prix']:,} F</td>
<td><span style="background:{sc};color:#fff;padding:3px 8px;border-radius:4px;font-size:11px">{st}</span></td>
<td><a href="/admin/renvoyer/{c['ref']}" style="background:#1A7A4A;color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;text-decoration:none">Renvoyer</a></td>
</tr>"""
    total=len(commandes)
    livres=sum(1 for c in commandes if c["statut"]=="livre")
    ca=sum(c["prix"] for c in commandes if c["statut"]=="livre")
    return Response(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="15">
<title>Dashboard - MES EXERCICES</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#f0f4f8}}
header{{background:#1B3A6B;color:#fff;padding:15px 20px;display:flex;justify-content:space-between;align-items:center}}
header h1{{font-size:16px}}
.logout{{color:#F5C518;text-decoration:none;font-size:13px}}
.banner{{background:#E8F5E9;border-bottom:1px solid #4CAF50;padding:10px 20px;font-size:13px;color:#1B5E20;text-align:center;font-weight:600}}
.stats{{display:flex;gap:12px;padding:18px;flex-wrap:wrap}}
.stat{{background:#fff;border-radius:8px;padding:14px;flex:1;min-width:100px;text-align:center;box-shadow:0 2px 5px rgba(0,0,0,.08)}}
.stat .n{{font-size:24px;font-weight:800;color:#1B3A6B}}
.stat .l{{font-size:11px;color:#666;margin-top:2px}}
.cont{{padding:0 18px 18px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 5px rgba(0,0,0,.08);font-size:12px}}
th{{background:#1B3A6B;color:#fff;padding:10px;text-align:left}}
td{{padding:10px;border-bottom:1px solid #f0f0f0}}
.empty{{text-align:center;padding:40px;color:#999;background:#fff;border-radius:8px}}
.new-btn{{display:inline-block;background:#F5C518;color:#1B3A6B;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:700;margin-bottom:14px;font-size:13px}}
</style></head>
<body>
<header><h1>📚 MES EXERCICES — Dashboard</h1><a href="/admin/logout" class="logout">Déconnexion</a></header>
<div class="banner">⚡ Livraison automatique ACTIVE — Polling WhatsApp toutes les 3 secondes</div>
<div class="stats">
  <div class="stat"><div class="n">{total-livres}</div><div class="l">En attente</div></div>
  <div class="stat"><div class="n">{livres}</div><div class="l">Livrees auto</div></div>
  <div class="stat"><div class="n">{total}</div><div class="l">Total</div></div>
  <div class="stat"><div class="n">{ca:,}</div><div class="l">CA (FCFA)</div></div>
</div>
<div class="cont">
  <a href="/admin/nouvelle" class="new-btn">+ Commande manuelle</a>
  {'<table><thead><tr><th>Ref</th><th>Nom</th><th>Tel</th><th>Niveau</th><th>Prix</th><th>Statut</th><th>Action</th></tr></thead><tbody>'+rows+'</tbody></table>' if commandes else '<div class="empty">⚡ En attente de commandes — Livraison auto activee</div>'}
</div></body></html>""",mimetype="text/html")

@app.route("/admin/renvoyer/<ref>")
@login_required
def renvoyer(ref):
    for c in commandes:
        if c["ref"]==ref:
            try:
                from whatsapp import envoyer_livraison
                envoyer_livraison(c["telephone"],c["nom"],c["niveau"],c["ref"])
                log.info(f"Renvoi manuel OK: {ref}")
            except Exception as e:
                log.error(f"Erreur renvoi: {e}")
            break
    return redirect(url_for("admin"))

@app.route("/admin/nouvelle",methods=["GET","POST"])
@login_required
def nouvelle():
    if request.method=="POST":
        niveau=request.form.get("niveau")
        ref=gen_ref()
        commandes.append({
            "ref":ref,"niveau":niveau,"nom_niveau":NOMS.get(niveau,niveau),
            "nom":request.form.get("nom"),"telephone":request.form.get("telephone"),
            "prix":PRIX.get(niveau,0),"statut":"en_attente"
        })
        return redirect(url_for("admin"))
    opts="".join([f'<option value="{k}">{v} — {PRIX[k]:,} F</option>' for k,v in NOMS.items()])
    return Response(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Nouvelle commande</title>
<style>body{{font-family:Arial,sans-serif;background:#f0f4f8;display:flex;justify-content:center;padding:30px 15px}}
.c{{background:#fff;border-radius:10px;padding:24px;max-width:400px;width:100%;box-shadow:0 2px 10px rgba(0,0,0,.1)}}
h2{{color:#1B3A6B;margin-bottom:18px}}
label{{display:block;margin-bottom:4px;font-weight:700;font-size:13px}}
select,input{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-bottom:13px}}
button{{width:100%;background:#1B3A6B;color:#fff;border:none;padding:12px;border-radius:6px;font-size:15px;cursor:pointer}}
a{{display:block;text-align:center;margin-top:10px;color:#666;font-size:13px;text-decoration:none}}</style>
</head><body><div class="c">
<h2>Nouvelle commande manuelle</h2>
<form method="POST">
<label>Niveau</label><select name="niveau">{opts}</select>
<label>Nom client</label><input name="nom" placeholder="Fatou Diallo" required>
<label>Telephone WhatsApp</label><input name="telephone" placeholder="221771234567" required>
<button>Enregistrer</button>
</form><a href="/admin">← Retour</a>
</div></body></html>""",mimetype="text/html")

@app.route("/admin/logout")
def logout():
    session.pop("admin",None)
    return redirect(url_for("login"))

# Page principale
MAIN_HTML = """<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MES EXERCICES — Cahiers scolaires numeriques</title>
<style>
:root{--bleu:#1B3A6B;--jaune:#F5C518;--vert:#1A7A4A}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#FAFAF8;color:#1A1A18}
nav{background:var(--bleu);padding:0 20px;display:flex;align-items:center;justify-content:space-between;height:56px;position:sticky;top:0;z-index:100}
.nav-logo{color:var(--jaune);font-size:15px;font-weight:800}
.nav-cta{background:var(--jaune);color:var(--bleu);padding:8px 16px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:700}
.hero{background:var(--bleu);padding:56px 20px 64px;text-align:center}
.hero h1{color:#fff;font-size:clamp(26px,5vw,46px);font-weight:800;line-height:1.15;margin-bottom:14px}
.hero h1 em{color:var(--jaune);font-style:normal}
.hero p{color:rgba(255,255,255,.8);font-size:15px;max-width:480px;margin:0 auto 28px;line-height:1.6}
.flags{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-bottom:28px}
.flag{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);color:#fff;font-size:12px;font-weight:600;padding:5px 12px;border-radius:16px}
.btn-hero{background:var(--jaune);color:var(--bleu);font-weight:800;font-size:15px;padding:14px 26px;border-radius:10px;text-decoration:none;display:inline-block}
.proof{background:#FFFBEA;border-top:1px solid #F5C518;border-bottom:1px solid #F5C518;padding:12px 20px}
.proof-inner{max-width:900px;margin:0 auto;display:flex;gap:20px;justify-content:center;flex-wrap:wrap}
.proof-item{font-size:13px;font-weight:600;color:var(--bleu)}
.section{max-width:1000px;margin:0 auto;padding:48px 20px}
.section h2{font-size:clamp(20px,3vw,32px);font-weight:800;color:var(--bleu);margin-bottom:24px;text-align:center}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px}
.card{background:#fff;border:1.5px solid #E8E8E6;border-radius:12px;padding:18px;cursor:pointer;transition:all .15s}
.card:hover{border-color:var(--bleu);transform:translateY(-2px);box-shadow:0 8px 20px rgba(27,58,107,.1)}
.card.pack{border-color:var(--jaune);grid-column:1/-1;background:#FFFBEA}
.niv{font-size:10px;font-weight:700;background:#EFF6FF;color:var(--bleu);padding:3px 8px;border-radius:12px;display:inline-block;margin-bottom:8px}
.card h3{font-size:14px;font-weight:700;margin-bottom:4px}
.card p{font-size:12px;color:#666;margin-bottom:10px;line-height:1.4}
.price{font-size:20px;font-weight:800;color:var(--bleu);margin-bottom:10px}
.pack .price{color:#B8860B}
.btn-card{width:100%;padding:10px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:700;background:var(--bleu);color:#fff}
.pack .btn-card{background:var(--jaune);color:var(--bleu)}
.commande-section{background:var(--bleu);padding:56px 20px}
.commande-inner{max-width:860px;margin:0 auto}
.ct{color:#fff;font-size:clamp(22px,3vw,34px);font-weight:800;text-align:center;margin-bottom:6px}
.cs{color:rgba(255,255,255,.7);text-align:center;font-size:14px;margin-bottom:32px}
.fgrid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
@media(max-width:600px){.fgrid{grid-template-columns:1fr}}
.fc{background:#fff;border-radius:14px;padding:22px}
.fc h3{font-size:15px;font-weight:700;color:var(--bleu);margin-bottom:16px}
.ng{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:14px}
.nb{border:2px solid #E0E0E0;border-radius:8px;padding:10px 6px;cursor:pointer;text-align:center;background:#fff;transition:all .15s}
.nb:hover,.nb.sel{border-color:var(--bleu);background:#EFF6FF}
.nb .nn{font-weight:700;font-size:12px}
.nb .np{color:var(--bleu);font-size:10px;margin-top:2px}
.pb{grid-column:1/-1;border-color:var(--jaune);background:#FFFBEA}
.pb.sel{border-color:#B8860B}
.rc{background:#EFF6FF;border-radius:8px;padding:10px;margin-bottom:12px;display:none;font-size:13px}
.rc strong{color:var(--bleu);font-size:17px}
label{display:block;margin-bottom:3px;font-weight:600;font-size:13px}
input{width:100%;padding:10px;border:1.5px solid #E0E0E0;border-radius:8px;font-size:14px;margin-bottom:12px;transition:border-color .15s}
input:focus{outline:none;border-color:var(--bleu)}
.btn-cmd{width:100%;background:var(--jaune);color:var(--bleu);border:none;padding:14px;border-radius:10px;font-size:15px;font-weight:800;cursor:pointer}
.ic{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.2);border-radius:14px;padding:22px;color:#fff}
.ic h3{font-size:15px;font-weight:700;color:var(--jaune);margin-bottom:16px}
.step{display:flex;gap:10px;align-items:flex-start;margin-bottom:14px}
.sn{width:28px;height:28px;border-radius:50%;background:var(--jaune);color:var(--bleu);font-size:12px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.st strong{display:block;font-size:13px;font-weight:700;margin-bottom:2px}
.st span{font-size:12px;color:rgba(255,255,255,.7)}
.auto-badge{background:#E8F5E9;border:1px solid #4CAF50;border-radius:8px;padding:10px 14px;font-size:12px;color:#1B5E20;text-align:center;margin:14px 0;font-weight:600}
footer{background:#1A1A18;color:rgba(255,255,255,.5);padding:28px 20px;text-align:center;font-size:13px}
.fl{color:var(--jaune);font-size:15px;font-weight:800;margin-bottom:8px}
.wa-float{position:fixed;bottom:22px;right:22px;background:#25D366;color:#fff;width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:24px;text-decoration:none;box-shadow:0 4px 14px rgba(0,0,0,.3);z-index:999}
</style></head>
<body>
<nav>
  <div class="nav-logo">📚 MES EXERCICES</div>
  <a href="#commander" class="nav-cta">Commander →</a>
</nav>
<div class="hero">
  <h1>Les <em>meilleures méthodes du monde</em><br>pour vos enfants</h1>
  <p>Cahiers scolaires numériques · Maternelle → BFEM · Programme sénégalais</p>
  <div class="flags">
    <span class="flag">🇫🇮 Finlande #1 PISA</span>
    <span class="flag">🇸🇬 Singapour Maths</span>
    <span class="flag">🇯🇵 Japon</span>
    <span class="flag">🍀 Montessori</span>
    <span class="flag">🇫🇷 France MEN</span>
    <span class="flag">🌐 IB PYP</span>
    <span class="flag">🇬🇧 Jolly Phonics</span>
  </div>
  <a href="#commander" class="btn-hero">📚 Commander maintenant →</a>
</div>
<div class="proof">
  <div class="proof-inner">
    <span class="proof-item">⚡ Livraison auto WhatsApp</span>
    <span class="proof-item">📄 100 pages par cahier</span>
    <span class="proof-item">✅ 500+ exercices</span>
    <span class="proof-item">💰 Dès 1 000 FCFA</span>
    <span class="proof-item">🇸🇳 Programme sénégalais</span>
  </div>
</div>
<div class="section" id="cahiers">
  <h2>9 cahiers · Un pour chaque niveau</h2>
  <div class="grid">
    <div class="card" onclick="sc('maternelle')"><div class="niv">Maternelle · 4-6 ans</div><h3>📚 Maternelle</h3><p>Lettres, chiffres, formes. Montessori + Jolly Phonics.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('ci')"><div class="niv">CI · 6-7 ans</div><h3>📚 CI</h3><p>Lecture syllabique, additions. Jolly Phonics.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('cp')"><div class="niv">CP · 6-7 ans</div><h3>📚 CP</h3><p>Lecture complète, soustraction. France MEN.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('ce1')"><div class="niv">CE1 · 7-8 ans</div><h3>📚 CE1</h3><p>Tables multiplication. Singapour Math.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('ce2')"><div class="niv">CE2 · 8-9 ans</div><h3>📚 CE2</h3><p>Division, compréhension. Méthode Japon.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('cm1')"><div class="niv">CM1 · 9-10 ans</div><h3>📚 CM1</h3><p>Géométrie, fractions. Common Core USA.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('cm2')"><div class="niv">CM2 · CFEE</div><h3>📚 CM2</h3><p>Préparation CFEE complète.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('cem1')"><div class="niv">CEM1 · 6ème</div><h3>📚 CEM1</h3><p>Algèbre, littérature, biologie.</p><div class="price">1 200 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('cem2')"><div class="niv">CEM2 · BFEM ⭐</div><h3>📚 CEM2</h3><p>Préparation BFEM. Épreuves types.</p><div class="price">1 500 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card pack" onclick="sc('pack')"><div class="niv" style="background:#FFF3CD;color:#B8860B">🔥 MEILLEUR CHOIX -44%</div><h3>📚 Pack Complet — 9 niveaux</h3><p>Tous les cahiers. Économisez 4 700 FCFA !</p><div class="price">6 000 FCFA <span style="font-size:13px;color:#999;text-decoration:line-through">10 700 FCFA</span></div><button class="btn-card">Commander le Pack →</button></div>
  </div>
</div>
<section class="commande-section" id="commander">
  <div class="commande-inner">
    <div class="ct">📚 Commander votre cahier</div>
    <div class="cs">Payez Wave ou Orange Money · Reçu sur WhatsApp en 2 minutes !</div>
    <div class="fgrid">
      <div class="fc">
        <h3>Choisissez votre niveau</h3>
        <form method="POST" action="/commander">
          <div class="ng">
            <div class="nb" id="btn-maternelle" onclick="ch('maternelle',this)"><div class="nn">Maternelle</div><div class="np">1 000 F</div></div>
            <div class="nb" id="btn-ci" onclick="ch('ci',this)"><div class="nn">CI</div><div class="np">1 000 F</div></div>
            <div class="nb" id="btn-cp" onclick="ch('cp',this)"><div class="nn">CP</div><div class="np">1 000 F</div></div>
            <div class="nb" id="btn-ce1" onclick="ch('ce1',this)"><div class="nn">CE1</div><div class="np">1 000 F</div></div>
            <div class="nb" id="btn-ce2" onclick="ch('ce2',this)"><div class="nn">CE2</div><div class="np">1 000 F</div></div>
            <div class="nb" id="btn-cm1" onclick="ch('cm1',this)"><div class="nn">CM1</div><div class="np">1 000 F</div></div>
            <div class="nb" id="btn-cm2" onclick="ch('cm2',this)"><div class="nn">CM2</div><div class="np">1 000 F</div></div>
            <div class="nb" id="btn-cem1" onclick="ch('cem1',this)"><div class="nn">CEM1</div><div class="np">1 200 F</div></div>
            <div class="nb" id="btn-cem2" onclick="ch('cem2',this)"><div class="nn">CEM2 BFEM</div><div class="np">1 500 F</div></div>
            <div class="nb pb" id="btn-pack" onclick="ch('pack',this)"><div class="nn">🔥 Pack 9 niveaux</div><div class="np">6 000 F (-44%)</div></div>
          </div>
          <input type="hidden" name="niveau" id="ni" required>
          <div class="rc" id="rc">
            Niveau : <span id="rn"></span><br>
            Montant : <strong id="rp"></strong>
          </div>
          <label>Prénom et nom</label>
          <input type="text" name="nom" placeholder="Fatou Diallo" required>
          <label>Numéro WhatsApp</label>
          <input type="tel" name="telephone" placeholder="221771234567" required>
          <button type="submit" class="btn-cmd">✅ Commander →</button>
        </form>
      </div>
      <div class="ic">
        <h3>⚡ Comment ça marche ?</h3>
        <div class="step"><div class="sn">1</div><div class="st"><strong>Choisissez et commandez</strong><span>Sélectionnez votre niveau, remplissez le formulaire</span></div></div>
        <div class="step"><div class="sn">2</div><div class="st"><strong>Payez Wave ou Orange Money</strong><span>Lien direct Wave ou code *144# Orange Money</span></div></div>
        <div class="step"><div class="sn">3</div><div class="st"><strong>Envoyez la confirmation</strong><span>Cliquez le bouton WhatsApp pré-rempli avec votre référence</span></div></div>
        <div class="step"><div class="sn">4</div><div class="st"><strong>Recevez en 2 minutes !</strong><span>Votre cahier PDF arrive automatiquement</span></div></div>
        <div class="auto-badge">⚡ 100% automatique — aucune intervention humaine</div>
        <div style="font-size:13px;color:rgba(255,255,255,.8);margin-top:10px">
          💙 Wave · 🟠 Orange Money<br>
          📞 <strong style="color:#fff">+221 77 134 34 99</strong>
        </div>
      </div>
    </div>
  </div>
</section>
<footer>
  <div class="fl">📚 MES EXERCICES</div>
  <div>Les meilleures méthodes du monde · Pour chaque enfant du Sénégal 🇸🇳</div>
  <div style="margin-top:10px">
    <a href="https://wa.me/221771343499" style="color:var(--jaune)">WhatsApp</a> ·
    <a href="tel:+221771343499" style="color:var(--jaune)">+221 77 134 34 99</a>
  </div>
</footer>
<a href="https://wa.me/221771343499" class="wa-float">💬</a>
<script>
var px={"maternelle":1000,"ci":1000,"cp":1000,"ce1":1000,"ce2":1000,"cm1":1000,"cm2":1000,"cem1":1200,"cem2":1500,"pack":6000};
var nm={"maternelle":"Maternelle","ci":"CI","cp":"CP","ce1":"CE1","ce2":"CE2","cm1":"CM1","cm2":"CM2","cem1":"CEM1","cem2":"CEM2 BFEM","pack":"Pack Complet"};
function ch(n,el){
  document.querySelectorAll('.nb').forEach(b=>b.classList.remove('sel'));
  el.classList.add('sel');
  document.getElementById('ni').value=n;
  document.getElementById('rn').textContent=nm[n];
  document.getElementById('rp').textContent=px[n].toLocaleString()+' FCFA';
  document.getElementById('rc').style.display='block';
}
function sc(n){
  document.getElementById('commander').scrollIntoView({behavior:'smooth'});
  setTimeout(function(){var el=document.getElementById('btn-'+n);if(el)ch(n,el);},600);
}
</script>
</body></html>"""

if __name__ == "__main__":
    demarrer_polling()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

# Pour Gunicorn (production)
demarrer_polling()
