import os
import logging
import random
import string
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

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

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
    msg_wa = f"Bonjour+j%27ai+commande+le+cahier+{NOMS.get(niveau,niveau).replace(' ','+')}+ref+{ref}+montant+{prix}+FCFA"
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
.ref-box strong{{font-size:26px;color:var(--bleu);letter-spacing:3px;display:block;margin-top:4px;font-weight:800}}
.montant{{background:#FFFBEA;border:2px solid var(--jaune);border-radius:10px;padding:14px;text-align:center;margin-bottom:20px}}
.montant p{{font-size:13px;color:#666}}
.montant strong{{font-size:28px;color:#B8860B;display:block;margin-top:4px;font-weight:800}}
h3{{font-size:15px;font-weight:700;color:#1A1A18;margin-bottom:14px}}
.btn-wave{{display:flex;align-items:center;justify-content:center;gap:10px;background:#1565C0;color:white;padding:16px;border-radius:10px;text-decoration:none;font-size:15px;font-weight:700;margin-bottom:10px;transition:background .2s}}
.btn-wave:hover{{background:#0D47A1}}
.btn-om{{display:flex;align-items:center;justify-content:center;gap:10px;background:#FF6F00;color:white;padding:16px;border-radius:10px;border:none;cursor:pointer;font-size:15px;font-weight:700;width:100%;margin-bottom:10px;transition:background .2s}}
.btn-om:hover{{background:#E65100}}
.om-box{{background:#FFF3E0;border-radius:10px;padding:16px;font-size:13px;line-height:1.9;display:none;margin-bottom:10px}}
.om-box code{{background:#FFE0B2;padding:4px 10px;border-radius:6px;font-size:14px;font-weight:700;display:inline-block;margin:2px 0}}
.alert{{background:#FFF3CD;border-left:4px solid var(--jaune);border-radius:6px;padding:14px;font-size:13px;line-height:1.6;margin-bottom:14px}}
.btn-wa{{display:flex;align-items:center;justify-content:center;gap:10px;background:#25D366;color:white;padding:14px;border-radius:10px;text-decoration:none;font-size:14px;font-weight:700;transition:background .2s}}
.btn-wa:hover{{background:#20BA5A}}
.retour{{display:block;text-align:center;margin-top:14px;color:#666;font-size:13px;text-decoration:none}}
.retour:hover{{color:var(--bleu)}}
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
    <h3>💳 Choisissez votre mode de paiement</h3>
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
    <div class="alert">
      ⚠️ <strong>Apres le paiement</strong> — Envoyez votre reference
      <strong>{ref}</strong> sur WhatsApp pour confirmer et recevoir votre cahier.
    </div>
    <a href="https://wa.me/{WHATSAPP_NUM}?text={msg_wa}" class="btn-wa" target="_blank">
      💬 Confirmer mon paiement sur WhatsApp
    </a>
    <a href="/" class="retour">← Retour au site</a>
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
:root{{--bleu:#1B3A6B;--jaune:#F5C518}}
body{{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}}
.card{{background:#fff;border-radius:12px;padding:30px;width:320px}}
h2{{text-align:center;color:var(--bleu);margin-bottom:20px}}
input{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;margin-bottom:14px;font-size:14px;box-sizing:border-box}}
button{{width:100%;background:var(--bleu);color:#fff;border:none;padding:12px;border-radius:6px;font-size:15px;cursor:pointer}}
.err{{color:red;font-size:13px;margin-bottom:10px}}
</style></head><body>
<div class="card">
  <h2>🔒 Admin</h2>
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
        st = "Livré" if c["statut"] == "livre" else "En attente"
        rows += f"""<tr>
<td><strong>{c['ref']}</strong></td><td>{c['nom']}</td><td>{c['telephone']}</td>
<td>{c['nom_niveau']}</td><td>{c['prix']:,} F</td>
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
<meta http-equiv="refresh" content="30">
<title>Dashboard - MES EXERCICES</title>
<style>
:root{{--bleu:#1B3A6B;--jaune:#F5C518}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#f0f4f8}}
header{{background:var(--bleu);color:#fff;padding:15px 20px;display:flex;justify-content:space-between;align-items:center}}
header h1{{font-size:17px}}
.logout{{color:#F5C518;text-decoration:none;font-size:13px}}
.stats{{display:flex;gap:12px;padding:20px;flex-wrap:wrap}}
.stat{{background:#fff;border-radius:8px;padding:15px;flex:1;min-width:110px;text-align:center;box-shadow:0 2px 5px rgba(0,0,0,.08)}}
.stat .n{{font-size:26px;font-weight:800;color:var(--bleu)}}
.stat .l{{font-size:12px;color:#666;margin-top:2px}}
.stat.ok .n{{color:#1A7A4A}}
.stat.warn .n{{color:#ff9800}}
.stat.money .n{{color:#B8860B}}
.cont{{padding:0 20px 20px}}
.new-btn{{display:inline-block;background:var(--jaune);color:var(--bleu);padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:700;margin-bottom:14px;font-size:14px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 5px rgba(0,0,0,.08);font-size:12px}}
th{{background:var(--bleu);color:#fff;padding:10px;text-align:left}}
td{{padding:10px;border-bottom:1px solid #f0f0f0}}
.empty{{text-align:center;padding:40px;color:#999;background:#fff;border-radius:8px}}
</style></head>
<body>
<header>
  <h1>📚 MES EXERCICES — Dashboard Admin</h1>
  <a href="/admin/logout" class="logout">Déconnexion</a>
</header>
<div class="stats">
  <div class="stat warn"><div class="n">{attente}</div><div class="l">En attente</div></div>
  <div class="stat ok"><div class="n">{livres}</div><div class="l">Livrées</div></div>
  <div class="stat"><div class="n">{total}</div><div class="l">Total</div></div>
  <div class="stat money"><div class="n">{ca:,} F</div><div class="l">CA livré</div></div>
</div>
<div class="cont">
  <a href="/admin/nouvelle" class="new-btn">+ Nouvelle commande</a>
  {'<table><thead><tr><th>Réf</th><th>Nom</th><th>Tél</th><th>Niveau</th><th>Prix</th><th>Statut</th><th>Actions</th></tr></thead><tbody>'+rows+'</tbody></table>' if commandes else '<div class="empty">Aucune commande pour le moment — le dashboard se rafraîchit toutes les 30s</div>'}
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
                log.info(f"Livraison OK: {ref}")
            except Exception as e:
                log.error(f"ERREUR LIVRAISON {ref}: {e}")
                import traceback; log.error(traceback.format_exc())
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
                log.info(f"Renvoi OK: {ref}")
            except Exception as e:
                log.error(f"ERREUR RENVOI {ref}: {e}")
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
            "nom": request.form.get("nom"), "telephone": request.form.get("telephone"),
            "prix": PRIX.get(niveau, 0), "statut": "en_attente"
        })
        return redirect(url_for("admin"))
    opts = "".join([f'<option value="{k}">{v} — {PRIX[k]:,} F</option>' for k,v in NOMS.items()])
    return Response(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Nouvelle commande</title>
<style>
body{{font-family:Arial,sans-serif;background:#f0f4f8;display:flex;justify-content:center;padding:30px 15px}}
.card{{background:#fff;border-radius:10px;padding:24px;max-width:400px;width:100%;box-shadow:0 2px 10px rgba(0,0,0,.1)}}
h2{{color:#1B3A6B;margin-bottom:18px}}
label{{display:block;margin-bottom:5px;font-weight:700;font-size:13px}}
select,input{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-bottom:14px}}
button{{width:100%;background:#1B3A6B;color:#fff;border:none;padding:12px;border-radius:6px;font-size:15px;cursor:pointer}}
a{{display:block;text-align:center;margin-top:10px;color:#666;font-size:13px;text-decoration:none}}
</style></head><body>
<div class="card">
  <h2>Nouvelle commande manuelle</h2>
  <form method="POST">
    <label>Niveau</label><select name="niveau">{opts}</select>
    <label>Nom client</label><input name="nom" placeholder="Fatou Diallo" required>
    <label>Téléphone WhatsApp</label><input name="telephone" placeholder="221771234567" required>
    <button>Enregistrer</button>
  </form>
  <a href="/admin">← Retour</a>
</div></body></html>""", mimetype="text/html")

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

# ============================================================
# SITE VITRINE COMPLET AVEC FORMULAIRE INTEGRE
# ============================================================
MAIN_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MES EXERCICES — Les meilleures méthodes du monde pour vos enfants</title>
<meta name="description" content="Cahiers d'exercices scolaires inspirés des systèmes Finlandais, Singapourien, Japonais, Montessori, IB PYP et France MEN. Maternelle au CEM2.">
<style>
:root{--bleu:#1B3A6B;--bleu-clair:#2A5298;--jaune:#F5C518;--jaune-pale:#FFFBEA;--fond:#FAFAF8;--encre:#1A1A18;--gris:#5A5A58;--gris-pale:#F0EFED;--vert:#1A7A4A;--vert-pale:#E8F5EE;--radius:12px}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--fond);color:var(--encre);line-height:1.6}
nav{position:sticky;top:0;z-index:100;background:var(--bleu);padding:0 24px;display:flex;align-items:center;justify-content:space-between;height:56px;box-shadow:0 2px 12px rgba(0,0,0,.3)}
.nav-logo{color:var(--jaune);font-size:15px;font-weight:800}
.nav-links{display:flex;gap:8px;align-items:center}
.nav-links a{color:rgba(255,255,255,.8);font-size:13px;text-decoration:none;padding:6px 10px;border-radius:6px}
.nav-links a:hover{color:#fff}
.nav-badge{background:var(--jaune);color:var(--bleu);font-size:10px;font-weight:700;padding:3px 8px;border-radius:10px}
.hero{background:var(--bleu);padding:72px 24px 80px;text-align:center;position:relative;overflow:hidden}
.hero-eyebrow{display:inline-block;background:var(--jaune);color:var(--bleu);font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;padding:6px 16px;border-radius:20px;margin-bottom:24px}
.hero h1{color:#fff;font-size:clamp(28px,5vw,52px);font-weight:800;line-height:1.1;letter-spacing:-1px;margin-bottom:18px;max-width:700px;margin-left:auto;margin-right:auto}
.hero h1 em{color:var(--jaune);font-style:normal}
.hero-sub{color:rgba(255,255,255,.78);font-size:clamp(14px,2vw,17px);max-width:540px;margin:0 auto 36px;line-height:1.65}
.flags-row{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-bottom:36px}
.flag-chip{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);color:#fff;font-size:12px;font-weight:600;padding:6px 14px;border-radius:20px;display:inline-flex;align-items:center;gap:6px}
.flag-chip .dot{width:6px;height:6px;border-radius:50%;background:var(--jaune);flex-shrink:0}
.hero-ctas{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:48px}
.btn-primary{background:var(--jaune);color:var(--bleu);font-weight:800;font-size:15px;padding:15px 28px;border-radius:10px;border:none;cursor:pointer;text-decoration:none;display:inline-block;transition:transform .15s,box-shadow .15s}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(245,197,24,.4)}
.btn-secondary{background:transparent;color:#fff;font-weight:600;font-size:14px;padding:15px 24px;border-radius:10px;border:1.5px solid rgba(255,255,255,.35);text-decoration:none;display:inline-block}
.hero-stats{display:flex;gap:36px;justify-content:center;flex-wrap:wrap}
.hero-stat-num{color:var(--jaune);font-size:32px;font-weight:800;line-height:1}
.hero-stat-lbl{color:rgba(255,255,255,.6);font-size:12px;margin-top:4px}
.proof-strip{background:var(--jaune-pale);border-top:1px solid #F5C518;border-bottom:1px solid #F5C518;padding:14px 24px;text-align:center}
.proof-strip-inner{max-width:900px;margin:0 auto;display:flex;gap:28px;justify-content:center;flex-wrap:wrap}
.proof-item{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:600;color:var(--bleu)}
.section{padding:64px 24px;max-width:1100px;margin:0 auto}
.section-label{font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--bleu-clair);margin-bottom:8px}
.section-title{font-size:clamp(22px,3vw,36px);font-weight:800;letter-spacing:-.5px;color:var(--encre);margin-bottom:12px}
.section-sub{font-size:15px;color:var(--gris);max-width:560px;line-height:1.6}
.products-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px;margin-top:32px}
.product-card{background:#fff;border:1.5px solid #E8E8E6;border-radius:var(--radius);padding:20px;cursor:pointer;transition:transform .15s,box-shadow .15s,border-color .15s;position:relative}
.product-card:hover{transform:translateY(-3px);box-shadow:0 12px 32px rgba(27,58,107,.1);border-color:var(--bleu-clair)}
.product-card.featured{border-color:var(--bleu);border-width:2px}
.product-badge{position:absolute;top:-10px;left:16px;background:var(--bleu);color:#fff;font-size:10px;font-weight:700;padding:4px 10px;border-radius:20px}
.product-badge.gold{background:var(--jaune);color:var(--bleu)}
.product-niveau{display:inline-block;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;margin-bottom:10px}
.n-mat{background:#FFF3E0;color:#E65100}.n-ci{background:#FDEDEC;color:#C0392B}.n-cp{background:#E8F5E9;color:#1B5E20}
.n-ce1{background:#E3F2FD;color:#1565C0}.n-ce2{background:#F3E5F5;color:#6A1B9A}
.n-cm1{background:#E8F5E9;color:#2E7D32}.n-cm2{background:#FBE9E7;color:#BF360C}
.n-cem1{background:#E0F2F1;color:#004D40}.n-cem2{background:#E8EAF6;color:#1B3A6B}.n-pack{background:var(--bleu);color:#fff}
.product-name{font-size:15px;font-weight:700;color:var(--encre);margin-bottom:4px}
.product-desc{font-size:12px;color:var(--gris);margin-bottom:10px;line-height:1.5}
.product-price-main{font-size:22px;font-weight:800;color:var(--bleu);margin-bottom:10px}
.btn-acheter{width:100%;padding:11px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:700;background:var(--bleu);color:#fff;transition:background .15s}
.btn-acheter:hover{background:var(--bleu-clair)}
.btn-acheter.pack{background:var(--jaune);color:var(--bleu)}
.btn-acheter.pack:hover{background:#e6b800}
.methodes-section{background:var(--bleu);padding:64px 24px;color:#fff}
.methodes-detail-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px;margin-top:36px}
.methode-card{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.15);border-radius:var(--radius);padding:18px;transition:background .2s}
.methode-card:hover{background:rgba(255,255,255,.12)}
.methode-flag{font-size:26px;margin-bottom:8px}
.methode-nom{font-size:14px;font-weight:700;color:var(--jaune);margin-bottom:4px}
.methode-pays{font-size:11px;color:rgba(255,255,255,.6);margin-bottom:6px}
.methode-info{font-size:12px;color:rgba(255,255,255,.75);line-height:1.6}
.temoignages-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:18px;margin-top:32px}
.temoignage{background:#fff;border:1.5px solid #E8E8E6;border-radius:var(--radius);padding:20px}
.temo-stars{color:#F5C518;font-size:14px;margin-bottom:8px}
.temo-text{font-size:13px;color:var(--gris);line-height:1.7;margin-bottom:12px;font-style:italic}
.temo-name{font-size:13px;font-weight:700;color:var(--encre)}
.temo-role{font-size:11px;color:var(--gris)}
.faq-list{margin-top:28px}
.faq-item{border:1.5px solid #E8E8E6;border-radius:var(--radius);margin-bottom:10px;background:#fff;overflow:hidden}
.faq-q{padding:16px 20px;font-size:14px;font-weight:700;cursor:pointer;display:flex;justify-content:space-between;align-items:center}
.faq-a{display:none;padding:0 20px 16px;font-size:13px;color:var(--gris);line-height:1.7}
.faq-item.open .faq-a{display:block}
.faq-arrow{transition:transform .2s;font-size:12px;color:var(--gris)}
.faq-item.open .faq-arrow{transform:rotate(180deg)}
/* FORMULAIRE COMMANDE INTEGRE */
.commande-section{background:linear-gradient(135deg,#1B3A6B 0%,#2A5298 100%);padding:72px 24px}
.commande-inner{max-width:900px;margin:0 auto}
.commande-title{color:#fff;font-size:clamp(24px,3vw,38px);font-weight:800;text-align:center;margin-bottom:8px}
.commande-sub{color:rgba(255,255,255,.75);text-align:center;font-size:15px;margin-bottom:40px}
.commande-grid{display:grid;grid-template-columns:1fr 1fr;gap:32px}
@media(max-width:680px){.commande-grid{grid-template-columns:1fr}}
.form-card{background:#fff;border-radius:16px;padding:28px}
.form-card h3{font-size:17px;font-weight:700;color:var(--bleu);margin-bottom:20px}
.niveaux-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:18px}
.niv-btn{border:2px solid #E8E8E6;border-radius:8px;padding:10px 8px;cursor:pointer;text-align:center;background:#fff;transition:all .2s}
.niv-btn:hover{border-color:var(--bleu);background:#EFF6FF}
.niv-btn.sel{border-color:var(--bleu);background:#EFF6FF}
.niv-btn .nn{font-weight:700;font-size:12px;color:var(--encre)}
.niv-btn .np{color:var(--bleu);font-size:11px;margin-top:2px}
.pack-btn{grid-column:1/-1;border-color:var(--jaune);background:var(--jaune-pale)}
.pack-btn.sel{border-color:#B8860B;background:#FFF3CD}
.pack-btn .np{color:#B8860B}
.recap-box{background:#EFF6FF;border-radius:8px;padding:12px;margin-bottom:16px;display:none;font-size:13px}
.recap-box strong{color:var(--bleu);font-size:18px}
label{display:block;margin-bottom:4px;font-weight:600;font-size:13px;color:var(--encre)}
input,select{width:100%;padding:10px 12px;border:1.5px solid #E0E0E0;border-radius:8px;font-size:14px;margin-bottom:14px;transition:border-color .2s}
input:focus,select:focus{outline:none;border-color:var(--bleu)}
.btn-commander{width:100%;background:var(--jaune);color:var(--bleu);border:none;padding:15px;border-radius:10px;font-size:16px;font-weight:800;cursor:pointer;transition:transform .15s,box-shadow .15s}
.btn-commander:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(245,197,24,.5)}
.info-card{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.2);border-radius:16px;padding:28px;color:#fff}
.info-card h3{font-size:17px;font-weight:700;color:var(--jaune);margin-bottom:20px}
.step-item{display:flex;gap:14px;margin-bottom:18px;align-items:flex-start}
.step-num{width:32px;height:32px;border-radius:50%;background:var(--jaune);color:var(--bleu);font-size:14px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.step-text strong{display:block;font-size:14px;font-weight:700;margin-bottom:2px}
.step-text span{font-size:13px;color:rgba(255,255,255,.7)}
.payment-methods{display:flex;gap:10px;margin-top:20px;flex-wrap:wrap}
.pm{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:8px;padding:10px 16px;font-size:13px;font-weight:700;color:#fff;display:flex;align-items:center;gap:6px}
footer{background:var(--encre);color:rgba(255,255,255,.6);padding:36px 24px;text-align:center}
.footer-logo{color:var(--jaune);font-size:17px;font-weight:800;margin-bottom:8px}
.footer-links{display:flex;gap:20px;justify-content:center;flex-wrap:wrap;margin:14px 0}
.footer-links a{color:var(--jaune);text-decoration:none;font-size:13px;font-weight:600}
.footer-bottom{font-size:12px;color:rgba(255,255,255,.35);margin-top:12px}
.btn-wa-float{position:fixed;bottom:24px;right:24px;background:#25D366;color:#fff;width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:26px;text-decoration:none;box-shadow:0 4px 16px rgba(0,0,0,.3);z-index:999;transition:transform .2s}
.btn-wa-float:hover{transform:scale(1.1)}
</style>
</head>
<body>

<nav>
  <div class="nav-logo">📚 MES EXERCICES</div>
  <div class="nav-links">
    <a href="#methodes">Méthodes</a>
    <a href="#cahiers">Cahiers</a>
    <a href="#commander">Commander</a>
    <a href="#faq">FAQ</a>
    <span class="nav-badge">🌍 7 méthodes</span>
  </div>
</nav>

<!-- HERO -->
<section class="hero">
  <div class="hero-eyebrow">🏆 Sélection mondiale · Maternelle → BFEM</div>
  <h1>Les <em>meilleures méthodes du monde</em><br>dans les mains de vos enfants</h1>
  <p class="hero-sub">Chaque exercice sélectionné dans les systèmes scolaires les mieux classés du monde — Finlande, Singapour, Japon, Montessori — et adapté au programme sénégalais.</p>
  <div class="flags-row">
    <span class="flag-chip"><span class="dot"></span>🇫🇮 Finlande #1 mondial</span>
    <span class="flag-chip"><span class="dot"></span>🇸🇬 Singapour Maths</span>
    <span class="flag-chip"><span class="dot"></span>🇯🇵 Méthode Japon</span>
    <span class="flag-chip"><span class="dot"></span>🍀 Montessori</span>
    <span class="flag-chip"><span class="dot"></span>🌐 IB PYP</span>
    <span class="flag-chip"><span class="dot"></span>🇫🇷 France MEN</span>
    <span class="flag-chip"><span class="dot"></span>🇬🇧 Jolly Phonics</span>
  </div>
  <div class="hero-ctas">
    <a href="#commander" class="btn-primary">📚 Commander maintenant →</a>
    <a href="#methodes" class="btn-secondary">Comment ça marche ?</a>
  </div>
  <div class="hero-stats">
    <div class="hero-stat"><div class="hero-stat-num">7</div><div class="hero-stat-lbl">Méthodes mondiales</div></div>
    <div class="hero-stat"><div class="hero-stat-num">9</div><div class="hero-stat-lbl">Niveaux scolaires</div></div>
    <div class="hero-stat"><div class="hero-stat-num">500+</div><div class="hero-stat-lbl">Exercices par cahier</div></div>
    <div class="hero-stat"><div class="hero-stat-num">100</div><div class="hero-stat-lbl">Pages par cahier</div></div>
  </div>
</section>

<!-- SOCIAL PROOF -->
<div class="proof-strip">
  <div class="proof-strip-inner">
    <div class="proof-item"><span>⭐</span> 200+ familles satisfaites</div>
    <div class="proof-item"><span>📥</span> Livraison instantanée WhatsApp</div>
    <div class="proof-item"><span>🔄</span> Imprimable à l'infini</div>
    <div class="proof-item"><span>🇸🇳</span> Programme MEN Sénégal</div>
    <div class="proof-item"><span>💳</span> Wave · Orange Money</div>
  </div>
</div>

<!-- MÉTHODES -->
<section class="methodes-section" id="methodes">
  <div style="max-width:1100px;margin:0 auto">
    <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:rgba(255,255,255,.5);margin-bottom:8px">Nos sources</div>
    <div style="font-size:clamp(22px,3vw,38px);font-weight:800;color:#fff;margin-bottom:10px">7 systèmes scolaires,<br><em style="color:var(--jaune)">tous les #1 mondiaux</em></div>
    <div class="methodes-detail-grid">
      <div class="methode-card"><div class="methode-flag">🇫🇮</div><div class="methode-nom">Méthode Finlandaise</div><div class="methode-pays">PISA #1 mondial</div><div class="methode-info">Apprentissage par la curiosité, pas la mémorisation.</div></div>
      <div class="methode-card"><div class="methode-flag">🇸🇬</div><div class="methode-nom">Singapour Maths</div><div class="methode-pays">TIMSS #1 mondial</div><div class="methode-info">Modèle barre visuel — comprendre avant calculer.</div></div>
      <div class="methode-card"><div class="methode-flag">🇯🇵</div><div class="methode-nom">Méthode Japonaise</div><div class="methode-pays">PISA Top 3</div><div class="methode-info">Rigueur, calligraphie et maîtrise progressive.</div></div>
      <div class="methode-card"><div class="methode-flag">🍀</div><div class="methode-nom">Montessori</div><div class="methode-pays">100+ ans d'expérience</div><div class="methode-info">Matériel sensoriel et apprentissage autonome.</div></div>
      <div class="methode-card"><div class="methode-flag">🌐</div><div class="methode-nom">IB PYP</div><div class="methode-pays">159 pays</div><div class="methode-info">Esprit critique et connexion entre matières.</div></div>
      <div class="methode-card"><div class="methode-flag">🇫🇷</div><div class="methode-nom">France MEN</div><div class="methode-pays">Programme officiel</div><div class="methode-info">Structure académique et excellence en français.</div></div>
      <div class="methode-card"><div class="methode-flag">🇬🇧</div><div class="methode-nom">Jolly Phonics</div><div class="methode-pays">Lecture rapide</div><div class="methode-info">Méthode phonique #1 pour apprendre à lire.</div></div>
    </div>
  </div>
</section>

<!-- CAHIERS -->
<section class="section" id="cahiers">
  <div class="section-label">Nos produits</div>
  <div class="section-title">9 cahiers — Un pour chaque niveau</div>
  <div class="section-sub">De la Maternelle au BFEM, chaque cahier couvre les 3 trimestres avec 100 pages et 500+ exercices.</div>
  <div class="products-grid">
    <div class="product-card" onclick="scrollCommander('maternelle')">
      <div class="product-niveau n-mat">Maternelle · 4-6 ans</div>
      <div class="product-name">📚 Cahier Maternelle</div>
      <div class="product-desc">Lettres, chiffres, formes, couleurs. Méthodes Montessori + Jolly Phonics.</div>
      <div class="product-price-main">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="scrollCommander('ci')">
      <div class="product-niveau n-ci">CI · 6-7 ans</div>
      <div class="product-name">📚 Cahier CI</div>
      <div class="product-desc">Lecture syllabique, additions, écriture. Jolly Phonics + Finlande.</div>
      <div class="product-price-main">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="scrollCommander('cp')">
      <div class="product-niveau n-cp">CP · 6-7 ans</div>
      <div class="product-name">📚 Cahier CP</div>
      <div class="product-desc">Lecture complète, soustraction, grammaire de base. France MEN.</div>
      <div class="product-price-main">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="scrollCommander('ce1')">
      <div class="product-niveau n-ce1">CE1 · 7-8 ans</div>
      <div class="product-name">📚 Cahier CE1</div>
      <div class="product-desc">Tables de multiplication, conjugaison, carte du Sénégal. Singapour Math.</div>
      <div class="product-price-main">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="scrollCommander('ce2')">
      <div class="product-niveau n-ce2">CE2 · 8-9 ans</div>
      <div class="product-name">📚 Cahier CE2</div>
      <div class="product-desc">Division, compréhension de texte, sciences. Méthode Japon.</div>
      <div class="product-price-main">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="scrollCommander('cm1')">
      <div class="product-niveau n-cm1">CM1 · 9-10 ans</div>
      <div class="product-name">📚 Cahier CM1</div>
      <div class="product-desc">Géométrie, fractions, histoire du Sénégal. Common Core USA.</div>
      <div class="product-price-main">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="scrollCommander('cm2')">
      <div class="product-niveau n-cm2">CM2 · CFEE</div>
      <div class="product-name">📚 Cahier CM2</div>
      <div class="product-desc">Préparation CFEE complète. Exercices types examens officiels.</div>
      <div class="product-price-main">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="scrollCommander('cem1')">
      <div class="product-niveau n-cem1">CEM1 · 6ème</div>
      <div class="product-name">📚 Cahier CEM1</div>
      <div class="product-desc">Algèbre, analyse littéraire, biologie. Niveau collège complet.</div>
      <div class="product-price-main">1 200 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card featured" onclick="scrollCommander('cem2')">
      <div class="product-badge">⭐ BFEM</div>
      <div class="product-niveau n-cem2">CEM2 · BFEM</div>
      <div class="product-name">📚 Cahier CEM2</div>
      <div class="product-desc">Préparation BFEM. Épreuves types, corrigés, méthodes avancées.</div>
      <div class="product-price-main">1 500 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card featured" onclick="scrollCommander('pack')" style="grid-column:1/-1;border-color:var(--jaune)">
      <div class="product-badge gold">🔥 MEILLEUR CHOIX -44%</div>
      <div class="product-niveau n-pack">Pack Complet · 9 niveaux</div>
      <div class="product-name">📚 Pack Complet MES EXERCICES</div>
      <div class="product-desc">Les 9 cahiers (Maternelle → BFEM) en un seul achat. Économisez 4 700 FCFA !</div>
      <div class="product-price-main" style="color:var(--jaune)">6 000 FCFA <span style="font-size:14px;color:#999;text-decoration:line-through;font-weight:400">10 700 FCFA</span></div>
      <button class="btn-acheter pack">Commander le Pack →</button>
    </div>
  </div>
</section>

<!-- TÉMOIGNAGES -->
<div style="background:#fff;padding:64px 24px;border-top:1px solid #E8E8E6">
  <div style="max-width:1100px;margin:0 auto">
    <div class="section-label" style="text-align:center">Témoignages</div>
    <div class="section-title" style="text-align:center;margin-bottom:32px">Ce que disent les parents</div>
    <div class="temoignages-grid">
      <div class="temoignage"><div class="temo-stars">★★★★★</div><div class="temo-text">"Mon fils de CE1 a progressé en maths en 2 semaines. Les exercices avec les baobabs et les mangues, il adore !"</div><div class="temo-name">Aïssatou Diallo</div><div class="temo-role">Maman · Dakar</div></div>
      <div class="temoignage"><div class="temo-stars">★★★★★</div><div class="temo-text">"J'utilise le cahier CM2 pour préparer le CFEE de ma fille. La structure en 3 trimestres est parfaite."</div><div class="temo-name">Ibrahima Sow</div><div class="temo-role">Papa · Thiès</div></div>
      <div class="temoignage"><div class="temo-stars">★★★★★</div><div class="temo-text">"Livraison reçue en 4 minutes sur WhatsApp ! Imprimé le soir même, mon fils a commencé le lendemain."</div><div class="temo-name">Fatou Ndiaye</div><div class="temo-role">Maman · Ziguinchor</div></div>
    </div>
  </div>
</div>

<!-- FORMULAIRE COMMANDE INTEGRE -->
<section class="commande-section" id="commander">
  <div class="commande-inner">
    <div class="commande-title">📚 Commander votre cahier</div>
    <div class="commande-sub">Choisissez votre niveau, payez avec Wave ou Orange Money, recevez sur WhatsApp en 5 minutes</div>
    <div class="commande-grid">
      <!-- FORMULAIRE -->
      <div class="form-card">
        <h3>1. Remplissez votre commande</h3>
        <form method="POST" action="/commander">
          <div class="niveaux-grid">
            <div class="niv-btn" id="btn-maternelle" onclick="choisir('maternelle',this)"><div class="nn">Maternelle</div><div class="np">1 000 FCFA</div></div>
            <div class="niv-btn" id="btn-ci" onclick="choisir('ci',this)"><div class="nn">CI</div><div class="np">1 000 FCFA</div></div>
            <div class="niv-btn" id="btn-cp" onclick="choisir('cp',this)"><div class="nn">CP</div><div class="np">1 000 FCFA</div></div>
            <div class="niv-btn" id="btn-ce1" onclick="choisir('ce1',this)"><div class="nn">CE1</div><div class="np">1 000 FCFA</div></div>
            <div class="niv-btn" id="btn-ce2" onclick="choisir('ce2',this)"><div class="nn">CE2</div><div class="np">1 000 FCFA</div></div>
            <div class="niv-btn" id="btn-cm1" onclick="choisir('cm1',this)"><div class="nn">CM1</div><div class="np">1 000 FCFA</div></div>
            <div class="niv-btn" id="btn-cm2" onclick="choisir('cm2',this)"><div class="nn">CM2</div><div class="np">1 000 FCFA</div></div>
            <div class="niv-btn" id="btn-cem1" onclick="choisir('cem1',this)"><div class="nn">CEM1</div><div class="np">1 200 FCFA</div></div>
            <div class="niv-btn" id="btn-cem2" onclick="choisir('cem2',this)"><div class="nn">CEM2 BFEM</div><div class="np">1 500 FCFA</div></div>
            <div class="niv-btn pack-btn" id="btn-pack" onclick="choisir('pack',this)"><div class="nn">🔥 Pack Complet 9 niveaux</div><div class="np">6 000 FCFA (-44%)</div></div>
          </div>
          <input type="hidden" name="niveau" id="niveau_input" required>
          <div class="recap-box" id="recap">
            <div>Niveau : <span id="recap_nom"></span></div>
            <div>Montant : <strong id="recap_prix"></strong></div>
          </div>
          <label>Votre prénom et nom</label>
          <input type="text" name="nom" placeholder="Fatou Diallo" required>
          <label>Votre numéro WhatsApp</label>
          <input type="tel" name="telephone" placeholder="221771234567" required>
          <button type="submit" class="btn-commander">✅ Commander et payer →</button>
        </form>
      </div>
      <!-- INFO PAIEMENT -->
      <div class="info-card">
        <h3>2. Comment payer et recevoir ?</h3>
        <div class="step-item">
          <div class="step-num">1</div>
          <div class="step-text"><strong>Remplissez le formulaire</strong><span>Choisissez votre niveau et entrez votre numéro WhatsApp</span></div>
        </div>
        <div class="step-item">
          <div class="step-num">2</div>
          <div class="step-text"><strong>Choisissez votre paiement</strong><span>Wave (lien direct) ou Orange Money (code *144#)</span></div>
        </div>
        <div class="step-item">
          <div class="step-num">3</div>
          <div class="step-text"><strong>Confirmez sur WhatsApp</strong><span>Envoyez votre référence de commande sur WhatsApp</span></div>
        </div>
        <div class="step-item">
          <div class="step-num">4</div>
          <div class="step-text"><strong>Recevez votre cahier</strong><span>PDF envoyé sur WhatsApp en moins de 5 minutes !</span></div>
        </div>
        <div style="margin-top:20px;padding-top:18px;border-top:1px solid rgba(255,255,255,.15)">
          <div style="font-size:13px;font-weight:700;color:var(--jaune);margin-bottom:10px">Modes de paiement acceptés</div>
          <div class="payment-methods">
            <div class="pm">💙 Wave</div>
            <div class="pm">🟠 Orange Money</div>
          </div>
          <div style="margin-top:16px;font-size:13px;color:rgba(255,255,255,.7)">📞 WhatsApp : <strong style="color:#fff">+221 77 134 34 99</strong></div>
          <div style="font-size:12px;color:rgba(255,255,255,.5);margin-top:4px">Disponible 7j/7 · 8h-22h</div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- FAQ -->
<section class="section" id="faq">
  <div class="section-label">Questions fréquentes</div>
  <div class="section-title">Tout ce que vous devez savoir</div>
  <div class="faq-list">
    <div class="faq-item"><div class="faq-q">C'est quoi exactement MES EXERCICES ? <span class="faq-arrow">▼</span></div><div class="faq-a">MES EXERCICES est une collection de cahiers scolaires numériques (PDF) couvrant tous les niveaux du système sénégalais, de la Maternelle au BFEM. Chaque cahier contient 100 pages d'exercices inspirés des 7 meilleures méthodes éducatives mondiales, adaptées au programme officiel du Ministère de l'Éducation Nationale du Sénégal.</div></div>
    <div class="faq-item"><div class="faq-q">Comment vais-je recevoir le cahier après paiement ? <span class="faq-arrow">▼</span></div><div class="faq-a">Après réception de votre paiement Wave ou Orange Money, nous vous envoyons le lien de téléchargement par WhatsApp au numéro que vous nous avez communiqué. Délai maximum : 5 minutes. Le fichier est au format PDF, compatible avec tous les appareils.</div></div>
    <div class="faq-item"><div class="faq-q">Puis-je imprimer le cahier plusieurs fois ? <span class="faq-arrow">▼</span></div><div class="faq-a">Oui, absolument ! Un achat = une licence illimitée pour votre usage personnel. Vous pouvez imprimer autant d'exemplaires que vous voulez, pour tous vos enfants, pour toutes les années à venir.</div></div>
    <div class="faq-item"><div class="faq-q">Le programme est-il adapté au Sénégal ? <span class="faq-arrow">▼</span></div><div class="faq-a">Oui ! Les cahiers suivent le programme officiel du MEN Sénégal. Les exemples et contextes sont africains (le baobab, le mil, la Tabaski, Dakar, les noms sénégalais...). Les méthodes mondiales sont intégrées EN PLUS du programme officiel.</div></div>
    <div class="faq-item"><div class="faq-q">Y a-t-il des tarifs pour les enseignants et les écoles ? <span class="faq-arrow">▼</span></div><div class="faq-a">Oui ! Les établissements scolaires et enseignants peuvent bénéficier de tarifs préférentiels. Contactez-nous sur WhatsApp (+221 77 134 34 99) pour un devis personnalisé.</div></div>
  </div>
</section>

<!-- CTA FINAL -->
<div style="background:var(--jaune);padding:56px 24px;text-align:center">
  <div style="max-width:600px;margin:0 auto">
    <div style="font-size:32px;margin-bottom:10px">🎓</div>
    <div style="font-size:clamp(20px,4vw,34px);font-weight:800;color:var(--bleu);margin-bottom:10px;line-height:1.15">Offrez à votre enfant<br>le meilleur du monde</div>
    <div style="font-size:14px;color:rgba(27,58,107,.75);margin-bottom:24px">7 méthodes mondiales · 100 pages · 500+ exercices · Diplôme inclus</div>
    <a href="#commander" class="btn-primary" style="background:var(--bleu);color:#fff">📚 Commander maintenant →</a>
  </div>
</div>

<!-- FOOTER -->
<footer>
  <div class="footer-logo">📚 MES EXERCICES</div>
  <div style="font-size:13px;color:rgba(255,255,255,.45);margin-bottom:14px">Les meilleures méthodes du monde · Pour chaque enfant d'Afrique</div>
  <div class="footer-links">
    <a href="https://wa.me/221771343499">WhatsApp</a>
    <a href="tel:+221771343499">+221 77 134 34 99</a>
    <a href="#commander">Commander</a>
    <a href="#faq">FAQ</a>
  </div>
  <div class="footer-bottom">© 2025-2026 MES EXERCICES · Tous droits réservés<br>
  🇫🇮 Finlande · 🇸🇬 Singapour · 🇯🇵 Japon · 🍀 Montessori · 🌐 IB PYP · 🇫🇷 France MEN · 🇬🇧 Jolly Phonics</div>
</footer>

<!-- BOUTON WHATSAPP FLOTTANT -->
<a href="https://wa.me/221771343499" class="btn-wa-float" target="_blank" title="WhatsApp">💬</a>

<script>
var prix={"maternelle":1000,"ci":1000,"cp":1000,"ce1":1000,"ce2":1000,"cm1":1000,"cm2":1000,"cem1":1200,"cem2":1500,"pack":6000};
var noms={"maternelle":"Maternelle","ci":"CI","cp":"CP","ce1":"CE1","ce2":"CE2","cm1":"CM1","cm2":"CM2","cem1":"CEM1 (6ème)","cem2":"CEM2 BFEM","pack":"Pack Complet 9 niveaux"};
function choisir(n,el){
  document.querySelectorAll('.niv-btn').forEach(b=>b.classList.remove('sel'));
  el.classList.add('sel');
  document.getElementById('niveau_input').value=n;
  document.getElementById('recap_nom').textContent=noms[n];
  document.getElementById('recap_prix').textContent=prix[n].toLocaleString()+' FCFA';
  document.getElementById('recap').style.display='block';
}
function scrollCommander(niveau){
  document.getElementById('commander').scrollIntoView({behavior:'smooth'});
  setTimeout(function(){
    var el=document.getElementById('btn-'+niveau);
    if(el) choisir(niveau,el);
  },600);
}
document.querySelectorAll('.faq-item').forEach(item=>{
  item.querySelector('.faq-q').addEventListener('click',()=>item.classList.toggle('open'));
});
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
