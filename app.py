import os
from flask import Flask, request, jsonify, session, redirect, url_for, flash
from functools import wraps

app = Flask(__name__)
app.secret_key = "mesexercices2025secret"

ADMIN_PASSWORD = "mesexercices2025"

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
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Arial, sans-serif; background: #f0f4f8; color: #333; }
header { background: #2e7d32; color: white; padding: 20px; text-align: center; }
header h1 { font-size: 28px; }
header p { font-size: 14px; margin-top: 5px; opacity: 0.9; }
.container { max-width: 700px; margin: 30px auto; padding: 0 15px; }
.card { background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
h2 { color: #2e7d32; margin-bottom: 20px; font-size: 20px; }
.niveaux { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
.niveau-btn { border: 2px solid #e0e0e0; border-radius: 8px; padding: 12px; cursor: pointer; text-align: center; transition: all 0.2s; background: white; }
.niveau-btn:hover { border-color: #2e7d32; background: #f1f8f1; }
.niveau-btn.selected { border-color: #2e7d32; background: #e8f5e9; }
.niveau-btn .nom { font-weight: bold; font-size: 13px; }
.niveau-btn .prix { color: #2e7d32; font-size: 12px; margin-top: 4px; }
.pack-btn { grid-column: 1 / -1; border-color: #ff6f00; background: #fff8e1; }
.pack-btn.selected { border-color: #ff6f00; background: #ffe0b2; }
.pack-btn .prix { color: #ff6f00; }
label { display: block; margin-bottom: 5px; font-weight: bold; font-size: 14px; }
input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; margin-bottom: 15px; }
.recap { background: #e8f5e9; border-radius: 8px; padding: 15px; margin-bottom: 20px; display: none; }
.recap p { font-size: 14px; margin: 4px 0; }
.recap strong { color: #2e7d32; font-size: 18px; }
button[type=submit] { width: 100%; background: #2e7d32; color: white; border: none; padding: 15px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
button[type=submit]:hover { background: #1b5e20; }
.info-paiement { background: #e3f2fd; border-radius: 8px; padding: 15px; font-size: 13px; line-height: 1.6; }
.info-paiement strong { color: #1565c0; }
input[name=niveau] { display: none; }
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
    <form method="POST" action="/commander" id="form">
      <p style="margin-bottom:12px;font-weight:bold;font-size:14px;">Choisissez votre niveau :</p>
      <div class="niveaux">
        <div class="niveau-btn" onclick="choisir('maternelle',this)"><div class="nom">Maternelle</div><div class="prix">1 000 FCFA</div></div>
        <div class="niveau-btn" onclick="choisir('ci',this)"><div class="nom">CI</div><div class="prix">1 000 FCFA</div></div>
        <div class="niveau-btn" onclick="choisir('cp',this)"><div class="nom">CP</div><div class="prix">1 000 FCFA</div></div>
        <div class="niveau-btn" onclick="choisir('ce1',this)"><div class="nom">CE1</div><div class="prix">1 000 FCFA</div></div>
        <div class="niveau-btn" onclick="choisir('ce2',this)"><div class="nom">CE2</div><div class="prix">1 000 FCFA</div></div>
        <div class="niveau-btn" onclick="choisir('cm1',this)"><div class="nom">CM1</div><div class="prix">1 000 FCFA</div></div>
        <div class="niveau-btn" onclick="choisir('cm2',this)"><div class="nom">CM2</div><div class="prix">1 000 FCFA</div></div>
        <div class="niveau-btn" onclick="choisir('cem1',this)"><div class="nom">CEM1 (6eme)</div><div class="prix">1 200 FCFA</div></div>
        <div class="niveau-btn" onclick="choisir('cem2',this)"><div class="nom">CEM2 (BFEM)</div><div class="prix">1 500 FCFA</div></div>
        <div class="niveau-btn pack-btn" onclick="choisir('pack',this)"><div class="nom">&#127381; Pack Complet - 9 niveaux</div><div class="prix">6 000 FCFA (economie -44%)</div></div>
      </div>
      <input type="hidden" name="niveau" id="niveau_input" required>
      <div class="recap" id="recap">
        <p>Niveau choisi : <span id="recap_nom"></span></p>
        <p>Montant a payer : <strong id="recap_prix"></strong></p>
      </div>
      <label>Votre prenom et nom</label>
      <input type="text" name="nom" placeholder="Ex: Fatou Diallo" required>
      <label>Votre numero WhatsApp</label>
      <input type="tel" name="telephone" placeholder="Ex: 221771234567" required>
      <label>Methode de paiement</label>
      <select name="paiement" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-bottom:15px;">
        <option value="wave">Wave</option>
        <option value="orange_money">Orange Money</option>
      </select>
      <div class="info-paiement">
        <strong>&#128722; Comment payer ?</strong><br>
        1. Envoyez le montant sur : <strong>+221 77 134 34 99</strong><br>
        2. Remplissez ce formulaire et cliquez Commander<br>
        3. Vous recevrez votre cahier par WhatsApp sous 5 minutes
      </div>
      <br>
      <button type="submit">&#128722; Commander maintenant</button>
    </form>
  </div>
</div>
<script>
var prix = {"maternelle":1000,"ci":1000,"cp":1000,"ce1":1000,"ce2":1000,"cm1":1000,"cm2":1000,"cem1":1200,"cem2":1500,"pack":6000};
var noms = {"maternelle":"Maternelle","ci":"CI","cp":"CP","ce1":"CE1","ce2":"CE2","cm1":"CM1","cm2":"CM2","cem1":"CEM1 (6eme)","cem2":"CEM2 (BFEM)","pack":"Pack Complet (9 niveaux)"};
function choisir(niveau, el) {
  document.querySelectorAll('.niveau-btn').forEach(b => b.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('niveau_input').value = niveau;
  document.getElementById('recap_nom').textContent = noms[niveau];
  document.getElementById('recap_prix').textContent = prix[niveau].toLocaleString() + ' FCFA';
  document.getElementById('recap').style.display = 'block';
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
    paiement = request.form.get("paiement", "wave")
    if not niveau or not nom or not telephone:
        return redirect("/")
    import random, string
    ref = "ME" + "".join(random.choices(string.digits, k=6))
    commande = {
        "ref": ref, "niveau": niveau, "nom_niveau": NOMS.get(niveau, niveau),
        "nom": nom, "telephone": telephone, "paiement": paiement,
        "prix": PRIX.get(niveau, 0), "statut": "en_attente"
    }
    commandes.append(commande)
    html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Commande confirmee</title>
<style>
body { font-family: Arial, sans-serif; background: #f0f4f8; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
.card { background: white; border-radius: 12px; padding: 30px; max-width: 400px; width: 90%; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
.check { font-size: 60px; margin-bottom: 15px; }
h2 { color: #2e7d32; margin-bottom: 10px; }
.ref { background: #e8f5e9; border-radius: 8px; padding: 15px; margin: 15px 0; }
.ref p { font-size: 13px; color: #555; }
.ref strong { font-size: 22px; color: #2e7d32; letter-spacing: 2px; }
p { color: #555; font-size: 14px; line-height: 1.6; margin-bottom: 10px; }
a { display: block; background: #25d366; color: white; padding: 12px; border-radius: 8px; text-decoration: none; margin-top: 15px; font-weight: bold; }
</style>
</head>
<body>
<div class="card">
  <div class="check">&#10003;</div>
  <h2>Commande enregistree !</h2>
  <div class="ref">
    <p>Votre reference :</p>
    <strong>""" + ref + """</strong>
  </div>
  <p>Bonjour <strong>""" + nom + """</strong> !<br>
  Votre commande pour <strong>""" + NOMS.get(niveau, niveau) + """</strong> est bien enregistree.<br>
  Vous recevrez votre cahier sur WhatsApp sous <strong>5 minutes</strong>.</p>
  <p style="color:#ff6f00;"><strong>Gardez cette reference : """ + ref + """</strong></p>
  <a href="https://wa.me/221771343499?text=Bonjour%2C+ma+reference+est+""" + ref + """">&#128172; Contacter sur WhatsApp</a>
</div>
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
    html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Admin - MES EXERCICES</title>
<style>
body { font-family: Arial, sans-serif; background: #1a1a2e; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
.card { background: white; border-radius: 12px; padding: 30px; width: 320px; }
h2 { text-align: center; color: #2e7d32; margin-bottom: 20px; }
input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 15px; font-size: 14px; box-sizing: border-box; }
button { width: 100%; background: #2e7d32; color: white; border: none; padding: 12px; border-radius: 6px; font-size: 16px; cursor: pointer; }
.error { color: red; font-size: 13px; margin-bottom: 10px; }
</style>
</head>
<body>
<div class="card">
  <h2>&#128274; Admin</h2>
  """ + (f'<p class="error">{error}</p>' if error else "") + """
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
        statut_color = "#4caf50" if c["statut"] == "livre" else "#ff9800"
        statut_txt = "Livre" if c["statut"] == "livre" else "En attente"
        rows += f"""<tr>
<td><strong>{c['ref']}</strong></td>
<td>{c['nom']}</td>
<td>{c['telephone']}</td>
<td>{c['nom_niveau']}</td>
<td>{c['prix']:,} F</td>
<td>{c['paiement'].replace('_',' ').title()}</td>
<td><span style="background:{statut_color};color:white;padding:3px 8px;border-radius:4px;font-size:12px;">{statut_txt}</span></td>
<td>"""
        if c["statut"] != "livre":
            rows += f'<a href="/admin/livrer/{c["ref"]}" style="background:#2e7d32;color:white;padding:4px 8px;border-radius:4px;font-size:12px;text-decoration:none;">Livrer</a> '
        rows += f'<a href="/admin/renvoyer/{c["ref"]}" style="background:#1565c0;color:white;padding:4px 8px;border-radius:4px;font-size:12px;text-decoration:none;">Renvoyer</a>'
        rows += "</td></tr>"
    total = len(commandes)
    livres = sum(1 for c in commandes if c["statut"] == "livre")
    html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="30">
<title>Dashboard Admin - MES EXERCICES</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Arial, sans-serif; background: #f0f4f8; }
header { background: #1a1a2e; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
header h1 { font-size: 20px; }
.logout { color: #ff6b6b; text-decoration: none; font-size: 13px; }
.stats { display: flex; gap: 15px; padding: 20px; flex-wrap: wrap; }
.stat { background: white; border-radius: 8px; padding: 15px 20px; flex: 1; min-width: 120px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
.stat .num { font-size: 28px; font-weight: bold; color: #2e7d32; }
.stat .lbl { font-size: 12px; color: #666; }
.container { padding: 0 20px 20px; }
.btn-new { display: inline-block; background: #ff6f00; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; margin-bottom: 15px; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); font-size: 13px; }
th { background: #2e7d32; color: white; padding: 10px; text-align: left; }
td { padding: 10px; border-bottom: 1px solid #f0f0f0; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f9f9f9; }
.empty { text-align: center; padding: 40px; color: #999; }
</style>
</head>
<body>
<header>
  <h1>&#128218; MES EXERCICES - Dashboard</h1>
  <a href="/admin/logout" class="logout">Deconnexion</a>
</header>
<div class="stats">
  <div class="stat"><div class="num">""" + str(total) + """</div><div class="lbl">Total commandes</div></div>
  <div class="stat"><div class="num">""" + str(livres) + """</div><div class="lbl">Livrees</div></div>
  <div class="stat"><div class="num">""" + str(total - livres) + """</div><div class="lbl">En attente</div></div>
</div>
<div class="container">
  <a href="/admin/nouvelle" class="btn-new">+ Nouvelle commande manuelle</a>
  """ + (f"""<table>
<thead><tr><th>Ref</th><th>Nom</th><th>Telephone</th><th>Niveau</th><th>Prix</th><th>Paiement</th><th>Statut</th><th>Actions</th></tr></thead>
<tbody>{rows}</tbody>
</table>""" if commandes else '<div class="empty">Aucune commande pour le moment</div>') + """
</div>
</body>
</html>"""
    return html

@app.route("/admin/livrer/<ref>")
@login_required
def livrer(ref):
    from whatsapp import envoyer_livraison
    for c in commandes:
        if c["ref"] == ref:
            try:
               try:
    envoyer_livraison(c["telephone"], c["nom"], c["niveau"], c["ref"])
    c["statut"] = "livre"
except Exception as e:
    log.error(f"ERREUR LIVRAISON: {e}")
    import traceback
    log.error(traceback.format_exc())
            break
    return redirect(url_for("admin"))

@app.route("/admin/renvoyer/<ref>")
@login_required
try:
    envoyer_livraison(c["telephone"], c["nom"], c["niveau"], c["ref"])
    c["statut"] = "livre"
except Exception as e:
    log.error(f"ERREUR LIVRAISON: {e}")
    import traceback
    log.error(traceback.format_exc())
                pass
            break
    return redirect(url_for("admin"))

@app.route("/admin/nouvelle", methods=["GET", "POST"])
@login_required
def nouvelle():
    if request.method == "POST":
        niveau = request.form.get("niveau")
        nom = request.form.get("nom")
        telephone = request.form.get("telephone")
        paiement = request.form.get("paiement", "wave")
        import random, string
        ref = "ME" + "".join(random.choices(string.digits, k=6))
        commande = {
            "ref": ref, "niveau": niveau, "nom_niveau": NOMS.get(niveau, niveau),
            "nom": nom, "telephone": telephone, "paiement": paiement,
            "prix": PRIX.get(niveau, 0), "statut": "en_attente"
        }
        commandes.append(commande)
        return redirect(url_for("admin"))
    options = "".join([f'<option value="{k}">{v} - {p:,} F</option>' for k, (v, p) in zip(NOMS.keys(), [(v, PRIX[k]) for k, v in NOMS.items()])])
    html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Nouvelle commande</title>
<style>
body { font-family: Arial, sans-serif; background: #f0f4f8; display: flex; justify-content: center; padding: 30px 15px; }
.card { background: white; border-radius: 10px; padding: 25px; max-width: 400px; width: 100%; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
h2 { color: #2e7d32; margin-bottom: 20px; }
label { display: block; margin-bottom: 5px; font-weight: bold; font-size: 14px; }
select, input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; margin-bottom: 15px; }
button { width: 100%; background: #2e7d32; color: white; border: none; padding: 12px; border-radius: 6px; font-size: 15px; cursor: pointer; }
a { display: block; text-align: center; margin-top: 10px; color: #666; font-size: 13px; }
</style>
</head>
<body>
<div class="card">
  <h2>Nouvelle commande manuelle</h2>
  <form method="POST">
    <label>Niveau</label>
    <select name="niveau">""" + options + """</select>
    <label>Nom du client</label>
    <input type="text" name="nom" placeholder="Fatou Diallo" required>
    <label>Telephone WhatsApp</label>
    <input type="tel" name="telephone" placeholder="221771234567" required>
    <label>Paiement</label>
    <select name="paiement">
      <option value="wave">Wave</option>
      <option value="orange_money">Orange Money</option>
    </select>
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
