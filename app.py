import os
import logging
import random
import string
from flask import Flask, request, jsonify, session, redirect, url_for
from functools import wraps

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "mesexercices2025secret"

ADMIN_PASSWORD = "mesexercices2025"
WAVE_LINK = "https://pay.wave.com/m/M_sn_KPX6hNLZUljQ/c/sn/"
ORANGE_NUMERO = "+221 77 134 34 99"
SITE_URL = "https://mes-exercices-bot.onrender.com"

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
    html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MES EXERCICES - Commander</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#f0f4f8;color:#333}
header{background:#2e7d32;color:white;padding:20px;text-align:center}
header h1{font-size:26px}
header p{font-size:13px;margin-top:4px;opacity:.9}
.container{max-width:680px;margin:24px auto;padding:0 15px}
.card{background:white;border-radius:12px;padding:24px;box-shadow:0 2px 10px rgba(0,0,0,.1);margin-bottom:16px}
h2{color:#2e7d32;margin-bottom:18px;font-size:18px}
.niveaux{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:18px}
.nb{border:2px solid #e0e0e0;border-radius:8px;padding:12px;cursor:pointer;text-align:center;transition:all .2s;background:white}
.nb:hover{border-color:#2e7d32;background:#f1f8f1}
.nb.sel{border-color:#2e7d32;background:#e8f5e9}
.nb .nom{font-weight:bold;font-size:13px}
.nb .px{color:#2e7d32;font-size:12px;margin-top:3px}
.pack{grid-column:1/-1;border-color:#ff6f00;background:#fff8e1}
.pack.sel{border-color:#ff6f00;background:#ffe0b2}
.pack .px{color:#ff6f00}
label{display:block;margin-bottom:5px;font-weight:bold;font-size:14px}
input,select{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-bottom:14px}
.recap{background:#e8f5e9;border-radius:8px;padding:14px;margin-bottom:16px;display:none}
.recap p{font-size:13px;margin:3px 0}
.recap strong{color:#2e7d32;font-size:17px}
.info{background:#e3f2fd;border-radius:8px;padding:14px;font-size:13px;line-height:1.6;margin-bottom:16px}
.info strong{color:#1565c0}
button[type=submit]{width:100%;background:#2e7d32;color:white;border:none;padding:14px;border-radius:8px;font-size:16px;font-weight:bold;cursor:pointer}
button[type=submit]:hover{background:#1b5e20}
</style>
</head>
<body>
<header>
  <h1>&#128218; MES EXERCICES</h1>
  <p>Cahiers scolaires numeriques - Systeme senegalais</p>
</header>
<div class="container">
  <div class="card">
    <h2>&#128722; Passer une commande</h2>
    <form method="POST" action="/commander">
      <p style="margin-bottom:12px;font-weight:bold;font-size:14px;">Choisissez votre niveau :</p>
      <div class="niveaux">
        <div class="nb" onclick="choisir('maternelle',this)"><div class="nom">Maternelle</div><div class="px">1 000 FCFA</div></div>
        <div class="nb" onclick="choisir('ci',this)"><div class="nom">CI</div><div class="px">1 000 FCFA</div></div>
        <div class="nb" onclick="choisir('cp',this)"><div class="nom">CP</div><div class="px">1 000 FCFA</div></div>
        <div class="nb" onclick="choisir('ce1',this)"><div class="nom">CE1</div><div class="px">1 000 FCFA</div></div>
        <div class="nb" onclick="choisir('ce2',this)"><div class="nom">CE2</div><div class="px">1 000 FCFA</div></div>
        <div class="nb" onclick="choisir('cm1',this)"><div class="nom">CM1</div><div class="px">1 000 FCFA</div></div>
        <div class="nb" onclick="choisir('cm2',this)"><div class="nom">CM2</div><div class="px">1 000 FCFA</div></div>
        <div class="nb" onclick="choisir('cem1',this)"><div class="nom">CEM1 (6eme)</div><div class="px">1 200 FCFA</div></div>
        <div class="nb" onclick="choisir('cem2',this)"><div class="nom">CEM2 (BFEM)</div><div class="px">1 500 FCFA</div></div>
        <div class="nb pack" onclick="choisir('pack',this)"><div class="nom">&#127381; Pack Complet - 9 niveaux</div><div class="px">6 000 FCFA (economie -44%)</div></div>
      </div>
      <input type="hidden" name="niveau" id="niveau_input" required>
      <div class="recap" id="recap">
        <p>Niveau : <span id="recap_nom"></span></p>
        <p>Montant : <strong id="recap_prix"></strong></p>
      </div>
      <label>Votre prenom et nom</label>
      <input type="text" name="nom" placeholder="Ex: Fatou Diallo" required>
      <label>Votre numero WhatsApp</label>
      <input type="tel" name="telephone" placeholder="Ex: 221771234567" required>
      <div class="info">
        <strong>&#128722; Comment ca marche ?</strong><br>
        1. Choisissez votre niveau et cliquez Commander<br>
        2. Choisissez Wave ou Orange Money pour payer<br>
        3. Recevez votre cahier sur WhatsApp en 5 minutes !
      </div>
      <button type="submit">&#128722; Commander et payer</button>
    </form>
  </div>
</div>
<script>
var prix={"maternelle":1000,"ci":1000,"cp":1000,"ce1":1000,"ce2":1000,"cm1":1000,"cm2":1000,"cem1":1200,"cem2":1500,"pack":6000};
var noms={"maternelle":"Maternelle","ci":"CI","cp":"CP","ce1":"CE1","ce2":"CE2","cm1":"CM1","cm2":"CM2","cem1":"CEM1 (6eme)","cem2":"CEM2 (BFEM)","pack":"Pack Complet"};
function choisir(n,el){
  document.querySelectorAll('.nb').forEach(b=>b.classList.remove('sel'));
  el.classList.add('sel');
  document.getElementById('niveau_input').value=n;
  document.getElementById('recap_nom').textContent=noms[n];
  document.getElementById('recap_prix').textContent=prix[n].toLocaleString()+' FCFA';
  document.getElementById('recap').style.display='block';
}
</script>
</body>
</html>"""
    return html

@app.route("/commander", methods=["POST"])
def commander():
    niveau = request.form.get("niveau")
    nom = request.form.get("nom")
    telephone = request.form.get("telephone")
    if not niveau or not nom or not telephone:
        return redirect("/")
    ref = gen_ref()
    prix = PRIX.get(niveau, 1000)
    commande = {
        "ref": ref, "niveau": niveau, "nom_niveau": NOMS.get(niveau, niveau),
        "nom": nom, "telephone": telephone, "prix": prix, "statut": "en_attente"
    }
    commandes.append(commande)
    log.info(f"Nouvelle commande: {ref} - {nom} - {niveau} - {prix} FCFA")

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paiement - MES EXERCICES</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#f0f4f8;color:#333}}
header{{background:#2e7d32;color:white;padding:18px;text-align:center}}
header h1{{font-size:22px}}
.container{{max-width:500px;margin:24px auto;padding:0 15px}}
.card{{background:white;border-radius:12px;padding:24px;box-shadow:0 2px 10px rgba(0,0,0,.1);margin-bottom:16px}}
.ref-box{{background:#e8f5e9;border-radius:8px;padding:16px;text-align:center;margin-bottom:20px}}
.ref-box p{{font-size:13px;color:#555}}
.ref-box strong{{font-size:24px;color:#2e7d32;letter-spacing:2px;display:block;margin-top:4px}}
.montant{{background:#fff3e0;border-radius:8px;padding:14px;text-align:center;margin-bottom:20px}}
.montant p{{font-size:13px;color:#666}}
.montant strong{{font-size:26px;color:#ff6f00;display:block;margin-top:4px}}
h3{{color:#333;margin-bottom:14px;font-size:16px}}
.btn-wave{{display:block;background:#1565c0;color:white;padding:16px;border-radius:10px;text-decoration:none;text-align:center;font-size:16px;font-weight:bold;margin-bottom:12px}}
.btn-wave:hover{{background:#0d47a1}}
.btn-om{{display:block;background:#ff6f00;color:white;padding:16px;border-radius:10px;text-decoration:none;text-align:center;font-size:16px;font-weight:bold;margin-bottom:12px}}
.btn-om:hover{{background:#e65100}}
.om-instructions{{background:#fff3e0;border-radius:8px;padding:14px;font-size:13px;line-height:1.8;margin-bottom:12px;display:none}}
.om-instructions code{{background:#ffe0b2;padding:3px 8px;border-radius:4px;font-size:14px;font-weight:bold}}
.important{{background:#ffebee;border-radius:8px;padding:14px;font-size:13px;line-height:1.6;margin-top:16px;border-left:4px solid #e53935}}
.important strong{{color:#c62828}}
.wa-btn{{display:block;background:#25d366;color:white;padding:14px;border-radius:10px;text-decoration:none;text-align:center;font-size:15px;font-weight:bold;margin-top:14px}}
</style>
</head>
<body>
<header>
  <h1>&#128218; MES EXERCICES</h1>
</header>
<div class="container">
  <div class="card">
    <div class="ref-box">
      <p>Votre reference de commande :</p>
      <strong>{ref}</strong>
    </div>
    <div class="montant">
      <p>Montant a payer pour {NOMS.get(niveau, niveau)} :</p>
      <strong>{prix:,} FCFA</strong>
    </div>
    <h3>&#128179; Choisissez votre mode de paiement :</h3>
    <a href="{WAVE_LINK}" class="btn-wave" target="_blank">
      &#128179; PAYER AVEC WAVE
    </a>
    <a href="#" class="btn-om" onclick="showOM();return false;">
      &#128240; PAYER AVEC ORANGE MONEY
    </a>
    <div class="om-instructions" id="om-box">
      <strong>Paiement Orange Money :</strong><br><br>
      <strong>Option 1 — Par telephone :</strong><br>
      Composez : <code>*144*2*221771343499*{prix}#</code><br>
      Validez avec votre code PIN Orange Money<br><br>
      <strong>Option 2 — Depuis l'app Orange Money :</strong><br>
      Transfert → Entrez le numero : <code>77 134 34 99</code><br>
      Montant : <code>{prix} FCFA</code><br>
      Validez et confirmez
    </div>
    <div class="important">
      <strong>&#9888; Important apres le paiement :</strong><br>
      Envoyez votre reference <strong>{ref}</strong> sur WhatsApp
      pour confirmer votre paiement et recevoir votre cahier.
    </div>
    <a href="https://wa.me/221771343499?text=Bonjour%20j%27ai%20paye%20ma%20commande%20reference%20{ref}%20de%20{prix}%20FCFA%20pour%20{NOMS.get(niveau,niveau)}.%20Mon%20nom%3A%20{nom}" 
       class="wa-btn" target="_blank">
      &#128172; Confirmer mon paiement sur WhatsApp
    </a>
  </div>
</div>
<script>
function showOM(){{
  var box=document.getElementById('om-box');
  box.style.display=box.style.display==='block'?'none':'block';
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
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Admin - MES EXERCICES</title>
<style>
body{{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}}
.card{{background:white;border-radius:12px;padding:30px;width:320px}}
h2{{text-align:center;color:#2e7d32;margin-bottom:20px}}
input{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;margin-bottom:14px;font-size:14px;box-sizing:border-box}}
button{{width:100%;background:#2e7d32;color:white;border:none;padding:12px;border-radius:6px;font-size:16px;cursor:pointer}}
.error{{color:red;font-size:13px;margin-bottom:10px}}
</style>
</head>
<body>
<div class="card">
  <h2>&#128274; Admin</h2>
  {'<p class="error">'+error+'</p>' if error else ''}
  <form method="POST">
    <input type="password" name="password" placeholder="Mot de passe" required autofocus>
    <button type="submit">Se connecter</button>
  </form>
</div>
</body>
</html>"""
    return html

@app.route("/admin")
@login_required
def admin():
    rows = ""
    for c in reversed(commandes):
        sc = "#4caf50" if c["statut"] == "livre" else "#ff9800"
        st = "Livre" if c["statut"] == "livre" else "En attente"
        rows += f"""<tr>
<td><strong>{c['ref']}</strong></td>
<td>{c['nom']}</td>
<td>{c['telephone']}</td>
<td>{c['nom_niveau']}</td>
<td>{c['prix']:,} F</td>
<td><span style="background:{sc};color:white;padding:3px 8px;border-radius:4px;font-size:12px">{st}</span></td>
<td>"""
        if c["statut"] != "livre":
            rows += f'<a href="/admin/livrer/{c["ref"]}" style="background:#2e7d32;color:white;padding:4px 8px;border-radius:4px;font-size:12px;text-decoration:none;margin-right:4px">Livrer</a>'
        rows += f'<a href="/admin/renvoyer/{c["ref"]}" style="background:#1565c0;color:white;padding:4px 8px;border-radius:4px;font-size:12px;text-decoration:none">Renvoyer</a>'
        rows += "</td></tr>"
    total = len(commandes)
    livres = sum(1 for c in commandes if c["statut"] == "livre")
    attente = total - livres
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="30">
<title>Dashboard - MES EXERCICES</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#f0f4f8}}
header{{background:#1a1a2e;color:white;padding:15px 20px;display:flex;justify-content:space-between;align-items:center}}
header h1{{font-size:18px}}
.logout{{color:#ff6b6b;text-decoration:none;font-size:13px}}
.stats{{display:flex;gap:14px;padding:20px;flex-wrap:wrap}}
.stat{{background:white;border-radius:8px;padding:15px 20px;flex:1;min-width:110px;text-align:center;box-shadow:0 2px 5px rgba(0,0,0,.1)}}
.stat .num{{font-size:28px;font-weight:bold;color:#2e7d32}}
.stat .lbl{{font-size:12px;color:#666}}
.stat.warn .num{{color:#ff9800}}
.container{{padding:0 20px 20px}}
.btn-new{{display:inline-block;background:#ff6f00;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:bold;margin-bottom:14px}}
table{{width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 5px rgba(0,0,0,.1);font-size:13px}}
th{{background:#2e7d32;color:white;padding:10px;text-align:left}}
td{{padding:10px;border-bottom:1px solid #f0f0f0}}
tr:last-child td{{border-bottom:none}}
.empty{{text-align:center;padding:40px;color:#999;background:white;border-radius:8px}}
</style>
</head>
<body>
<header>
  <h1>&#128218; MES EXERCICES - Dashboard</h1>
  <a href="/admin/logout" class="logout">Deconnexion</a>
</header>
<div class="stats">
  <div class="stat"><div class="num">{total}</div><div class="lbl">Total</div></div>
  <div class="stat warn"><div class="num">{attente}</div><div class="lbl">En attente</div></div>
  <div class="stat"><div class="num">{livres}</div><div class="lbl">Livrees</div></div>
  <div class="stat"><div class="num">{attente * 1000 if attente > 0 else 0:,}</div><div class="lbl">A recevoir (F)</div></div>
</div>
<div class="container">
  <a href="/admin/nouvelle" class="btn-new">+ Nouvelle commande</a>
  {'<table><thead><tr><th>Ref</th><th>Nom</th><th>Tel</th><th>Niveau</th><th>Prix</th><th>Statut</th><th>Actions</th></tr></thead><tbody>'+rows+'</tbody></table>' if commandes else '<div class="empty">Aucune commande pour le moment</div>'}
</div>
</body>
</html>"""
    return html

@app.route("/admin/livrer/<ref>")
@login_required
def livrer(ref):
    for c in commandes:
        if c["ref"] == ref:
            try:
                from whatsapp import envoyer_livraison
                envoyer_livraison(c["telephone"], c["nom"], c["niveau"], c["ref"])
                c["statut"] = "livre"
                log.info(f"Livraison OK: {ref} -> {c['telephone']}")
            except Exception as e:
                log.error(f"ERREUR LIVRAISON {ref}: {e}")
                import traceback
                log.error(traceback.format_exc())
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
        nom = request.form.get("nom")
        telephone = request.form.get("telephone")
        ref = gen_ref()
        commandes.append({
            "ref": ref, "niveau": niveau, "nom_niveau": NOMS.get(niveau, niveau),
            "nom": nom, "telephone": telephone,
            "prix": PRIX.get(niveau, 0), "statut": "en_attente"
        })
        return redirect(url_for("admin"))
    options = "".join([f'<option value="{k}">{v} - {PRIX[k]:,} F</option>' for k, v in NOMS.items()])
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Nouvelle commande</title>
<style>
body{{font-family:Arial,sans-serif;background:#f0f4f8;display:flex;justify-content:center;padding:30px 15px}}
.card{{background:white;border-radius:10px;padding:24px;max-width:400px;width:100%;box-shadow:0 2px 10px rgba(0,0,0,.1)}}
h2{{color:#2e7d32;margin-bottom:18px}}
label{{display:block;margin-bottom:5px;font-weight:bold;font-size:14px}}
select,input{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-bottom:14px}}
button{{width:100%;background:#2e7d32;color:white;border:none;padding:12px;border-radius:6px;font-size:15px;cursor:pointer}}
a{{display:block;text-align:center;margin-top:10px;color:#666;font-size:13px;text-decoration:none}}
</style>
</head>
<body>
<div class="card">
  <h2>Nouvelle commande manuelle</h2>
  <form method="POST">
    <label>Niveau</label>
    <select name="niveau">{options}</select>
    <label>Nom du client</label>
    <input type="text" name="nom" placeholder="Fatou Diallo" required>
    <label>Telephone WhatsApp</label>
    <input type="tel" name="telephone" placeholder="221771234567" required>
    <button type="submit">Enregistrer</button>
  </form>
  <a href="/admin">Retour au dashboard</a>
</div>
</body>
</html>"""
    return html

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
