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
    "maternelle": "Maternelle",
    "ci": "CI - Cours d'Initiation",
    "cp": "CP - Cours Preparatoire",
    "ce1": "CE1", "ce2": "CE2",
    "cm1": "CM1", "cm2": "CM2 (CFEE)",
    "cem1": "CEM1", "cem2": "CEM2 (BFEM)",
    "pack": "Pack Complet 9 niveaux",
}

# Stockage en memoire (remplace SQLite)
commandes = []

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ============================================================
# PAGE D'ACCUEIL - COMMANDE CLIENT
# ============================================================
@app.route("/")
def accueil():
    options = ""
    for code, nom in NOMS.items():
        prix = PRIX.get(code, 0)
        options += f'<option value="{code}">{nom} — {prix:,} FCFA</option>'

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Commander — MES EXERCICES</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,sans-serif;background:#F8F8F6;min-height:100vh}}
.hero{{background:#1B3A6B;padding:28px 20px 36px;text-align:center;color:#fff}}
.hero h1{{font-size:22px;font-weight:800;line-height:1.3;margin-bottom:6px}}
.hero h1 em{{color:#F5C518;font-style:normal}}
.hero p{{font-size:13px;color:rgba(255,255,255,.7);margin-top:6px}}
.wrap{{padding:20px 16px;max-width:480px;margin:0 auto}}
.card{{background:#fff;border-radius:12px;border:1px solid #E8E8E6;padding:20px;margin-bottom:14px}}
.card-title{{font-size:13px;font-weight:700;color:#1B3A6B;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #F5C518}}
label{{font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:4px}}
input,select{{width:100%;padding:11px 14px;border:1.5px solid #E0E0E0;border-radius:8px;font-size:14px;margin-bottom:12px}}
input:focus,select:focus{{outline:none;border-color:#1B3A6B}}
.btn{{width:100%;padding:14px;border-radius:10px;border:none;cursor:pointer;font-size:15px;font-weight:800;background:#1B3A6B;color:#fff}}
.step{{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid #F0EFED;font-size:12px;color:#555}}
.step:last-child{{border:none}}
.sn{{width:24px;height:24px;border-radius:50%;background:#1B3A6B;color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.flags{{display:flex;flex-wrap:wrap;gap:5px;justify-content:center;margin-top:12px}}
.flag{{background:rgba(255,255,255,.12);color:#fff;font-size:10px;font-weight:600;padding:3px 9px;border-radius:12px}}
</style>
</head>
<body>
<div class="hero">
  <div style="font-size:13px;font-weight:800;color:#F5C518;margin-bottom:8px">📚 MES EXERCICES</div>
  <h1>Les <em>meilleures methodes du monde</em><br>pour vos enfants</h1>
  <p>100 pages · 500+ exercices · Livraison automatique par WhatsApp</p>
  <div class="flags">
    <span class="flag">🇫🇮 Finlande #1</span>
    <span class="flag">🇸🇬 Singapour #1</span>
    <span class="flag">🇯🇵 Japon Top3</span>
    <span class="flag">🍀 Montessori</span>
    <span class="flag">🌐 IB PYP</span>
  </div>
</div>
<div class="wrap">
  <form method="POST" action="/commander">
    <div class="card">
      <div class="card-title">1. Vos informations</div>
      <label>Prenom (optionnel)</label>
      <input type="text" name="prenom" placeholder="Ex : Amadou">
      <label>Votre numero WhatsApp *</label>
      <input type="tel" name="telephone" placeholder="+221 77 134 34 99" required>
    </div>
    <div class="card">
      <div class="card-title">2. Choisissez votre cahier</div>
      <select name="niveau" required>
        <option value="">-- Selectionnez un niveau --</option>
        {options}
      </select>
    </div>
    <div class="card">
      <div class="card-title">3. Comment ca marche ?</div>
      <div class="step"><span class="sn">1</span><span>Entrez votre numero WhatsApp et choisissez le niveau</span></div>
      <div class="step"><span class="sn">2</span><span>Nous vous envoyons les instructions de paiement par WhatsApp</span></div>
      <div class="step"><span class="sn">3</span><span>Payez sur <strong>Wave ou Orange Money</strong> au +221 77 134 34 99</span></div>
      <div class="step"><span class="sn">4</span><span>Votre cahier vous est envoye <strong>automatiquement en 5 minutes</strong> !</span></div>
    </div>
    <button type="submit" class="btn">📚 Commander maintenant</button>
    <div style="text-align:center;margin-top:12px;font-size:12px;color:#888">
      Wave · Orange Money · +221 77 134 34 99 · mesexercices.com
    </div>
  </form>
</div>
</body>
</html>"""

# ============================================================
# TRAITEMENT COMMANDE
# ============================================================
@app.route("/commander", methods=["POST"])
def commander():
    prenom = request.form.get("prenom", "").strip()
    telephone = request.form.get("telephone", "").strip()
    niveau = request.form.get("niveau", "").strip().lower()

    if not telephone or niveau not in PRIX:
        return redirect(url_for("accueil"))

    montant = PRIX[niveau]
    nom_niveau = NOMS.get(niveau, niveau)
    import random, string
    ref = "ME-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    commandes.append({
        "ref": ref, "prenom": prenom, "telephone": telephone,
        "niveau": niveau, "montant": montant, "statut": "en_attente"
    })

    try:
        from whatsapp import envoyer_confirmation_attente
        envoyer_confirmation_attente(telephone, niveau, montant)
    except Exception as e:
        print("WhatsApp error:", e)

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Commande confirmee</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,sans-serif;background:#F8F8F6;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
.card{{background:#fff;border-radius:16px;border:1px solid #E8E8E6;padding:28px 24px;max-width:420px;width:100%;text-align:center}}
.icon{{font-size:52px;margin-bottom:12px}}
h1{{font-size:20px;font-weight:800;color:#1B3A6B;margin-bottom:8px}}
.ref{{background:#EBF2FF;border-radius:8px;padding:10px;font-family:monospace;font-size:14px;font-weight:700;color:#1B3A6B;margin-bottom:16px}}
.step{{display:flex;gap:10px;text-align:left;padding:8px 0;border-bottom:1px solid #F0EFED;font-size:12px;color:#555}}
.step:last-child{{border:none}}
.sn{{width:22px;height:22px;border-radius:50%;background:#1B3A6B;color:#fff;font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px}}
.wa{{display:flex;align-items:center;justify-content:center;gap:8px;background:#25D366;color:#fff;font-size:14px;font-weight:800;padding:14px;border-radius:10px;text-decoration:none;margin-top:14px}}
</style>
</head>
<body>
<div class="card">
  <div class="icon">📱</div>
  <h1>Commande enregistree !</h1>
  <p style="font-size:13px;color:#666;margin-bottom:12px">Les instructions de paiement ont ete envoyees par WhatsApp au <strong>{telephone}</strong>.</p>
  <div class="ref">Ref : {ref}</div>
  <div class="step"><span class="sn">1</span><span>Verifiez vos messages WhatsApp</span></div>
  <div class="step"><span class="sn">2</span><span>Payez <strong>{montant:,} FCFA</strong> sur Wave ou OM au <strong>+221 77 134 34 99</strong></span></div>
  <div class="step"><span class="sn">3</span><span>Votre cahier <strong>{nom_niveau}</strong> arrive automatiquement en moins de 5 min ✅</span></div>
  <a href="https://wa.me/221771343499?text=Bonjour+j+ai+commande+{ref}+et+j+ai+paye" class="wa">
    💬 Confirmer le paiement sur WhatsApp
  </a>
</div>
</body></html>"""

# ============================================================
# ADMIN
# ============================================================
@app.route("/admin/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("dashboard"))
        error = "Mot de passe incorrect"
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Admin</title>
<style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:system-ui,sans-serif;background:#1B3A6B;min-height:100vh;display:flex;align-items:center;justify-content:center}}.box{{background:#fff;border-radius:16px;padding:32px 28px;width:100%;max-width:340px;text-align:center}}.logo{{font-size:14px;font-weight:800;color:#1B3A6B;margin-bottom:14px}}h1{{font-size:20px;font-weight:800;margin-bottom:18px}}input{{width:100%;padding:12px;border:1.5px solid #E0E0E0;border-radius:8px;font-size:14px;margin-bottom:12px}}button{{width:100%;padding:13px;background:#1B3A6B;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer}}.err{{background:#F8D7DA;color:#721C24;border-radius:7px;padding:9px;font-size:12px;margin-bottom:12px}}</style>
</head><body><div class="box"><div class="logo">📚 MES EXERCICES</div><h1>Admin</h1>
{"<div class='err'>"+error+"</div>" if error else ""}
<form method="POST"><input type="password" name="password" placeholder="Mot de passe" autofocus><button>Connexion</button></form></div></body></html>"""

@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin")
@login_required
def dashboard():
    rows = ""
    total_rev = 0
    for c in commandes:
        statut_badge = '<span style="background:#D4EDDA;color:#155724;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">Paye</span>' if c["statut"] == "payee" else '<span style="background:#FFF3CD;color:#856404;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">Attente</span>'
        if c["statut"] == "payee":
            total_rev += c["montant"]
        action = f'<form method="POST" action="/admin/livrer/{c["ref"]}" style="display:inline"><button style="background:#1A7A4A;color:#fff;border:none;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px;font-weight:700">✅ Confirmer</button></form>' if c["statut"] == "en_attente" else f'<form method="POST" action="/admin/renvoyer/{c["ref"]}" style="display:inline"><button style="background:#1565C0;color:#fff;border:none;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px;font-weight:700">🔄 Renvoyer</button></form>'
        rows += f'<tr><td style="padding:9px 12px;border-bottom:1px solid #F0EFED;font-family:monospace;font-size:11px;color:#888">{c["ref"]}</td><td style="padding:9px 12px;border-bottom:1px solid #F0EFED"><div style="font-weight:700;color:#1B3A6B">{c["telephone"]}</div>{"<div style='font-size:11px;color:#888'>"+c["prenom"]+"</div>" if c.get("prenom") else ""}</td><td style="padding:9px 12px;border-bottom:1px solid #F0EFED;font-size:12px">{NOMS.get(c["niveau"],c["niveau"])}</td><td style="padding:9px 12px;border-bottom:1px solid #F0EFED;font-weight:700;color:#1A7A4A">{c["montant"]:,} F</td><td style="padding:9px 12px;border-bottom:1px solid #F0EFED">{statut_badge}</td><td style="padding:9px 12px;border-bottom:1px solid #F0EFED">{action}</td></tr>'

    nb_att = sum(1 for c in commandes if c["statut"]=="en_attente")
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Dashboard Admin</title>
<meta http-equiv="refresh" content="30">
<style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:system-ui,sans-serif;background:#F0F2F5;color:#1A1A18}}.top{{background:#1B3A6B;padding:0 20px;height:52px;display:flex;align-items:center;justify-content:space-between}}.logo{{color:#F5C518;font-size:14px;font-weight:800}}.tl{{color:rgba(255,255,255,.7);font-size:12px;text-decoration:none;padding:5px 10px;border-radius:6px}}.tl:hover{{background:rgba(255,255,255,.1);color:#fff}}.wrap{{padding:20px;max-width:1100px;margin:0 auto}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}.stat{{background:#fff;border-radius:10px;border:1px solid #E8E8E6;padding:14px;text-align:center}}.stat-n{{font-size:28px;font-weight:800;color:#1B3A6B}}.stat-l{{font-size:11px;color:#888;margin-top:2px}}table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;border:1px solid #E8E8E6}}th{{background:#1B3A6B;color:#fff;padding:10px 12px;text-align:left;font-size:12px}}.add-btn{{background:#F5C518;color:#1B3A6B;font-size:12px;font-weight:700;padding:6px 14px;border-radius:8px;text-decoration:none;border:none;cursor:pointer}}.sec-title{{font-size:14px;font-weight:700;color:#1B3A6B;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center}}</style>
</head><body>
<div class="top">
  <div class="logo">📚 MES EXERCICES — Admin</div>
  <div>
    <a class="tl" href="/admin/nouvelle">+ Nouvelle</a>
    <a class="tl" href="/admin/logout">Deconnexion</a>
  </div>
</div>
<div class="wrap">
  <div class="stats">
    <div class="stat"><div class="stat-n">{len(commandes)}</div><div class="stat-l">Commandes</div></div>
    <div class="stat"><div class="stat-n" style="color:#856404">{nb_att}</div><div class="stat-l">En attente</div></div>
    <div class="stat"><div class="stat-n" style="color:#1A7A4A">{sum(1 for c in commandes if c["statut"]=="payee")}</div><div class="stat-l">Payees</div></div>
    <div class="stat"><div class="stat-n" style="color:#E07B39">{total_rev:,}</div><div class="stat-l">FCFA generes</div></div>
  </div>
  <div class="sec-title">📋 Commandes <a href="/admin/nouvelle" class="add-btn">+ Nouvelle</a></div>
  <table>
    <thead><tr><th>Reference</th><th>Client</th><th>Niveau</th><th>Montant</th><th>Statut</th><th>Action</th></tr></thead>
    <tbody>{"<tr><td colspan='6' style='text-align:center;padding:20px;color:#888;font-size:13px'>Aucune commande pour l instant. Les nouvelles commandes apparaitront ici automatiquement.</td></tr>" if not rows else rows}</tbody>
  </table>
  <div style="font-size:11px;color:#888;margin-top:8px;text-align:right">Actualisation automatique toutes les 30 secondes</div>
</div>
</body></html>"""

@app.route("/admin/livrer/<ref>", methods=["POST"])
@login_required
def livrer(ref):
    for c in commandes:
        if c["ref"] == ref:
            c["statut"] = "payee"
            try:
                from whatsapp import envoyer_livraison
                ok = envoyer_livraison(c["telephone"], c["niveau"], c.get("prenom",""))
                msg = "Cahier livre a " + c["telephone"] if ok else "Erreur envoi WhatsApp"
            except Exception as e:
                msg = "Erreur: " + str(e)
            break
    return redirect(url_for("dashboard"))

@app.route("/admin/renvoyer/<ref>", methods=["POST"])
@login_required
def renvoyer(ref):
    for c in commandes:
        if c["ref"] == ref:
            try:
                from whatsapp import envoyer_livraison
                envoyer_livraison(c["telephone"], c["niveau"], c.get("prenom",""))
            except Exception as e:
                print("Erreur:", e)
            break
    return redirect(url_for("dashboard"))

@app.route("/admin/nouvelle", methods=["GET","POST"])
@login_required
def nouvelle_commande():
    if request.method == "POST":
        telephone = request.form.get("telephone","").strip()
        niveau = request.form.get("niveau","").strip().lower()
        prenom = request.form.get("prenom","").strip()
        livrer_now = request.form.get("livrer") == "on"
        if telephone and niveau in PRIX:
            import random, string
            ref = "ME-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            c = {"ref":ref,"prenom":prenom,"telephone":telephone,"niveau":niveau,"montant":PRIX[niveau],"statut":"payee" if livrer_now else "en_attente"}
            commandes.append(c)
            if livrer_now:
                try:
                    from whatsapp import envoyer_livraison
                    envoyer_livraison(telephone, niveau, prenom)
                except Exception as e:
                    print("Erreur:", e)
        return redirect(url_for("dashboard"))

    options = ""
    for code, nom in NOMS.items():
        options += f'<option value="{code}">{nom} — {PRIX.get(code,0):,} FCFA</option>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Nouvelle commande</title>
<style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:system-ui,sans-serif;background:#F0F2F5;padding:20px}}.top{{background:#1B3A6B;padding:12px 20px;display:flex;align-items:center;gap:16px;margin:-20px -20px 20px;border-radius:0}}.logo{{color:#F5C518;font-size:14px;font-weight:800}}.back{{color:rgba(255,255,255,.7);font-size:12px;text-decoration:none}}.card{{background:#fff;border-radius:12px;border:1px solid #E8E8E6;padding:24px;max-width:480px}}h1{{font-size:18px;font-weight:800;color:#1B3A6B;margin-bottom:18px}}label{{font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:4px}}input,select{{width:100%;padding:11px;border:1.5px solid #E0E0E0;border-radius:8px;font-size:14px;margin-bottom:12px}}.check{{display:flex;align-items:center;gap:10px;margin-bottom:14px;font-size:13px;color:#555}}.check input{{width:auto;margin:0}}button{{padding:13px 24px;background:#1B3A6B;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer}}</style>
</head><body>
<div class="top"><div class="logo">📚 MES EXERCICES</div><a href="/admin" class="back">← Retour dashboard</a></div>
<div class="card"><h1>+ Nouvelle commande manuelle</h1>
<form method="POST">
  <label>Prenom (optionnel)</label><input type="text" name="prenom" placeholder="Ex : Fatou">
  <label>Numero WhatsApp *</label><input type="tel" name="telephone" placeholder="+221 77 XXX XX XX" required>
  <label>Niveau *</label><select name="niveau" required><option value="">-- Choisir --</option>{options}</select>
  <div class="check"><input type="checkbox" name="livrer" id="livrer" checked><label for="livrer" style="margin:0">Envoyer le cahier maintenant par WhatsApp</label></div>
  <button type="submit">✅ Creer la commande</button>
</form></div></body></html>"""

@app.route("/health")
def health():
    return jsonify({"status":"ok","commandes":len(commandes)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
