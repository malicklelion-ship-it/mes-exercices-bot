import os, logging, random, string, re, threading, time, requests, json, hmac, hashlib, base64
from flask import Flask, request, jsonify, session, redirect, url_for, Response
from functools import wraps

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "mesexercices2025secret"

ADMIN_PASSWORD = "mesexercices2025"
SECRET_KEY     = "mes2025secret"  # Pour signer les URLs
WAVE_BASE      = "https://pay.wave.com/m/M_sn_KPX6hNLZUljQ/c/sn/"
WHATSAPP_NUM   = "221771343499"
SITE_URL       = "https://mes-exercices.com"
ORDERS_FILE    = "commandes.json"

PRIX = {"maternelle":1000,"ci":1000,"cp":1000,"ce1":1000,"ce2":1000,
        "cm1":1000,"cm2":1000,"cem1":1200,"cem2":1500,"pack":6000}
NOMS = {"maternelle":"Maternelle","ci":"CI - Cours d'Initiation",
        "cp":"CP - Cours Preparatoire","ce1":"CE1","ce2":"CE2",
        "cm1":"CM1","cm2":"CM2","cem1":"CEM1 (6eme)",
        "cem2":"CEM2 (BFEM)","pack":"Pack Complet (9 niveaux)"}

# ============================================================
# SIGNATURE SECURISEE — URL autonome meme apres redemarrage
# ============================================================
def signer(ref, niveau, telephone, nom):
    """Cree une signature HMAC pour verifier l'URL"""
    data = f"{ref}:{niveau}:{telephone}:{nom}"
    sig = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    return sig

def verifier_signature(ref, niveau, telephone, nom, sig):
    """Verifie que la signature est valide"""
    expected = signer(ref, niveau, telephone, nom)
    return hmac.compare_digest(expected, sig)

def encoder_nom(nom):
    """Encode le nom pour URL"""
    return base64.urlsafe_b64encode(nom.encode()).decode()

def decoder_nom(nom_enc):
    """Decode le nom depuis URL"""
    try:
        return base64.urlsafe_b64decode(nom_enc.encode()).decode()
    except:
        return nom_enc

# ============================================================
# PERSISTANCE JSON
# ============================================================
def charger_commandes():
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE,"r") as f:
                data = json.load(f)
                log.info(f"✅ {len(data)} commandes chargees")
                return data
    except Exception as e:
        log.error(f"Erreur chargement: {e}")
    return []

def sauvegarder():
    try:
        with open(ORDERS_FILE,"w") as f:
            json.dump(commandes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Erreur sauvegarde: {e}")

commandes = charger_commandes()

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
# LIVRAISON
# ============================================================
def livrer_commande_directe(ref, niveau, telephone, nom):
    """Livre sans avoir besoin de la commande en memoire"""
    try:
        from whatsapp import envoyer_livraison
        envoyer_livraison(telephone, nom, niveau, ref)
        # Mettre a jour le statut si la commande existe en memoire
        for c in commandes:
            if c["ref"] == ref:
                c["statut"] = "livre"
                sauvegarder()
                break
        log.info(f"✅ LIVRE: {ref} → {telephone}")
        return True
    except Exception as e:
        log.error(f"❌ Erreur livraison {ref}: {e}")
        import traceback; log.error(traceback.format_exc())
        return False

def livrer_par_ref(ref):
    """Livre depuis la memoire/fichier"""
    for c in commandes:
        if c["ref"] == ref:
            return livrer_commande_directe(
                c["ref"], c["niveau"], c["telephone"], c["nom"]
            )
    return False

# ============================================================
# ROUTES
# ============================================================
@app.route("/health")
def health():
    return jsonify({
        "status":"ok",
        "commandes":len(commandes),
        "livrees":sum(1 for c in commandes if c["statut"]=="livre")
    })

@app.route("/confirmer/<ref>/<niveau>/<telephone>/<nom_enc>/<sig>")
def confirmer(ref, niveau, telephone, nom_enc, sig):
    """
    URL autonome — contient toutes les infos necessaires.
    Fonctionne meme apres redemarrage du serveur !
    """
    nom = decoder_nom(nom_enc)

    # Verifier la signature pour eviter la fraude
    if not verifier_signature(ref, niveau, telephone, nom, sig):
        return Response("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Erreur</title></head>
<body style="font-family:Arial;text-align:center;padding:50px">
<h2 style="color:red">❌ Lien invalide</h2>
<p>Ce lien n'est pas valide. Contactez le support.</p>
<a href="https://wa.me/221771343499" style="background:#25D366;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none">
💬 Contacter WhatsApp</a>
</body></html>""", mimetype="text/html")

    log.info(f"Confirmation: {ref} - {niveau} - {telephone} - {nom}")

    # Livrer directement avec les infos de l'URL
    ok = livrer_commande_directe(ref, niveau, telephone, nom)

    if ok:
        nom_niveau = NOMS.get(niveau, niveau)
        prix = PRIX.get(niveau, 0)
        html = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Livraison confirmee !</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:linear-gradient(135deg,#E8F5E9,#F0FFF4);
min-height:100vh;display:flex;align-items:center;
justify-content:center;padding:20px}}
.card{{background:#fff;border-radius:20px;padding:36px 28px;
max-width:420px;width:100%;text-align:center;
box-shadow:0 8px 32px rgba(0,0,0,.12)}}
.check{{font-size:80px;margin-bottom:16px;animation:pop .5s ease}}
@keyframes pop{{0%{{transform:scale(0)}}70%{{transform:scale(1.2)}}100%{{transform:scale(1)}}}}
h1{{color:#1A7A4A;font-size:22px;font-weight:800;margin-bottom:8px}}
.ref{{background:#E8F5E9;border-radius:10px;padding:14px;margin:16px 0}}
.ref .label{{font-size:12px;color:#666;margin-bottom:4px}}
.ref .code{{font-size:22px;color:#1A7A4A;font-weight:800;letter-spacing:3px}}
p{{color:#555;font-size:14px;line-height:1.6;margin-bottom:8px}}
.wa-btn{{display:flex;align-items:center;justify-content:center;gap:8px;
background:#25D366;color:#fff;padding:14px;border-radius:10px;
text-decoration:none;font-size:15px;font-weight:700;margin-top:16px}}
.badge{{display:inline-block;background:#E8F5E9;color:#1A7A4A;
padding:4px 12px;border-radius:20px;font-size:12px;
font-weight:600;margin-top:8px}}
</style></head>
<body><div class="card">
  <div class="check">✅</div>
  <div style="background:#fff;border-radius:12px;padding:8px 16px;display:inline-block;margin:0 auto 12px"><img src="data:image/png;base64,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" alt="MES EXERCICES" style="height:54px;object-fit:contain;display:block"></div><h1>Cahier envoyé avec succès !</h1>
  <div class="ref">
    <div class="label">Référence commande</div>
    <div class="code">{ref}</div>
  </div>
  <p>Bonjour <strong>{nom}</strong> !</p>
  <p>Votre cahier <strong>{nom_niveau}</strong> a été envoyé sur WhatsApp au numéro :<br>
  <strong>+{telephone}</strong></p>
  <div class="badge">📱 Vérifiez vos messages WhatsApp</div>
  <p style="margin-top:16px;font-size:12px;color:#888">
  Vous ne recevez pas le message ? Contactez-nous.</p>
  <a href="https://wa.me/{WHATSAPP_NUM}?text=Bonjour+ref+{ref}+je+n%27ai+pas+recu+mon+cahier"
     class="wa-btn">💬 Contacter le support</a>
</div></body></html>"""
        return html
    else:
        return redirect(
            f"https://wa.me/{WHATSAPP_NUM}?text=Bonjour+j%27ai+paye+ref+{ref}"
        )

@app.route("/")
def index():
    return Response(MAIN_HTML, mimetype="text/html")

@app.route("/commander", methods=["POST"])
def commander():
    niveau    = request.form.get("niveau","").strip()
    nom       = request.form.get("nom","").strip()
    telephone = request.form.get("telephone","").strip().replace("+","").replace(" ","")
    if not niveau or not nom or not telephone:
        return redirect("/")

    ref  = gen_ref()
    prix = PRIX.get(niveau, 1000)

    # Sauvegarder en memoire + fichier
    commandes.append({
        "ref":ref,"niveau":niveau,"nom_niveau":NOMS.get(niveau,niveau),
        "nom":nom,"telephone":telephone,"prix":prix,"statut":"en_attente"
    })
    sauvegarder()
    log.info(f"📝 Commande: {ref} - {nom} - {niveau} - {prix}F")

    # Creer URL de confirmation autonome avec signature
    nom_enc = encoder_nom(nom)
    sig = signer(ref, niveau, telephone, nom)
    confirm_url = f"{SITE_URL}/confirmer/{ref}/{niveau}/{telephone}/{nom_enc}/{sig}"
    wave_url = f"{WAVE_LINK}?amount={prix}"
    wa_msg = f"Bonjour+j%27ai+paye+ma+commande+ref+{ref}+montant+{prix}+FCFA"

    html = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paiement - MES EXERCICES</title>
<style>
:root{{--bleu:#1B3A6B;--jaune:#F5821F;--vert:#1A7A4A}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:#F0F4F8;color:#1A1A18}}
nav{{background:var(--bleu);padding:0 20px;height:52px;
display:flex;align-items:center;justify-content:space-between}}
.logo{{color:var(--jaune);font-size:14px;font-weight:800}}
.wrap{{max-width:460px;margin:24px auto;padding:0 14px}}
.card{{background:#fff;border-radius:14px;padding:24px;
box-shadow:0 2px 12px rgba(0,0,0,.08);margin-bottom:12px}}
.ref-box{{background:#EFF6FF;border:2px solid var(--bleu);
border-radius:10px;padding:16px;text-align:center;margin-bottom:16px}}
.ref-box .label{{font-size:12px;color:#666;margin-bottom:4px}}
.ref-box .code{{font-size:34px;color:var(--bleu);letter-spacing:5px;
font-weight:900;display:block}}
.mt-box{{background:#FFFBEA;border:2px solid var(--jaune);
border-radius:10px;padding:12px;text-align:center;margin-bottom:18px}}
.mt-box .nv{{font-size:12px;color:#888}}
.mt-box .mt{{font-size:30px;color:#B8860B;font-weight:900;display:block;margin-top:3px}}
.etape{{margin-bottom:18px}}
.et{{font-size:14px;font-weight:700;margin-bottom:10px;
display:flex;align-items:center;gap:8px}}
.en{{width:26px;height:26px;border-radius:50%;background:var(--bleu);
color:#fff;font-size:12px;font-weight:800;display:inline-flex;
align-items:center;justify-content:center;flex-shrink:0}}
.bwave{{display:flex;align-items:center;justify-content:center;gap:8px;
background:#1565C0;color:#fff;padding:15px;border-radius:10px;
text-decoration:none;font-size:15px;font-weight:700;margin-bottom:8px}}
.bom{{display:flex;align-items:center;justify-content:center;gap:8px;
background:#E65100;color:#fff;padding:15px;border-radius:10px;
border:none;cursor:pointer;font-size:15px;font-weight:700;
width:100%;margin-bottom:8px}}
.om-box{{background:#FFF3E0;border-radius:10px;padding:14px;
font-size:13px;line-height:1.9;display:none;margin-bottom:8px}}
.om-box code{{background:#FFE0B2;padding:3px 8px;border-radius:5px;
font-weight:700;display:inline-block}}
.confirm-box{{background:#E8F5E9;border:2px solid #4CAF50;
border-radius:12px;padding:16px;margin-bottom:8px;text-align:center}}
.confirm-box p{{font-size:13px;color:#1B5E20;margin-bottom:12px;line-height:1.6}}
.bconfirm{{display:flex;align-items:center;justify-content:center;gap:8px;
background:#1A7A4A;color:#fff;padding:16px;border-radius:10px;
text-decoration:none;font-size:16px;font-weight:800;
box-shadow:0 4px 12px rgba(26,122,74,.3)}}
.ou{{text-align:center;color:#aaa;font-size:12px;margin:8px 0;
display:flex;align-items:center;gap:8px}}
.ou::before,.ou::after{{content:'';flex:1;height:1px;background:#e0e0e0}}
.bwa{{display:flex;align-items:center;justify-content:center;gap:8px;
background:#25D366;color:#fff;padding:13px;border-radius:10px;
text-decoration:none;font-size:14px;font-weight:700}}
.note{{font-size:11px;color:#aaa;text-align:center;margin-top:6px;line-height:1.5}}
.secure{{background:#F3F4F6;border-radius:8px;padding:9px;
text-align:center;font-size:11px;color:#666;margin-top:8px}}
</style></head>
<body>
<nav>
  <div class="logo"><div style="background:#fff;border-radius:6px;padding:3px 8px;display:inline-flex;align-items:center"><img src="data:image/png;base64,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" alt="MES EXERCICES" style="height:54px;object-fit:contain;display:block"></div></div>
  <a href="/" style="color:rgba(255,255,255,.6);font-size:12px;text-decoration:none">← Retour</a>
</nav>
<div class="wrap"><div class="card">
  <div class="ref-box">
    <div class="label">Votre référence de commande</div>
    <span class="code">{ref}</span>
  </div>
  <div class="mt-box">
    <div class="nv">{NOMS.get(niveau,niveau)}</div>
    <span class="mt">{prix:,} FCFA</span>
  </div>

  <div class="etape">
    <div class="et"><span class="en">1</span> Payez maintenant</div>
    <a href="{wave_url}" class="bwave" target="_blank">
      💙 Payer {prix:,} FCFA avec Wave
    </a>
    <button class="bom" onclick="var o=document.getElementById('om');o.style.display=o.style.display=='block'?'none':'block'">
      🟠 Payer avec Orange Money
    </button>
    <div class="om-box" id="om">
      <strong>Par telephone :</strong><br>
      <code>*144*2*{WHATSAPP_NUM}*{prix}#</code><br><br>
      <strong>Par app Orange Money :</strong><br>
      Transfert → <code>77 134 34 99</code> → <code>{prix} FCFA</code>
    </div>
  </div>

  <div class="etape">
    <div class="et"><span class="en">2</span> Recevez votre cahier PDF</div>
    <div class="confirm-box">
      <p>⚡ Cliquez apres avoir paye :<br>
      Votre PDF arrive en moins de <strong>30 secondes</strong> !</p>
      <a href="{confirm_url}" class="bconfirm">
        ✅ J'ai payé — Envoyer mon cahier !
      </a>
    </div>
    <div class="ou">ou</div>
    <a href="https://wa.me/{WHATSAPP_NUM}?text={wa_msg}" class="bwa" target="_blank">
      💬 Confirmer via WhatsApp
    </a>
    <p class="note">Message pré-rempli avec votre référence {ref}</p>
  </div>

  <div class="secure">🔒 Paiement sécurisé · Support : +221 77 134 34 99</div>
</div></div>
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
    return Response(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Admin</title>
<style>body{{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;justify-content:center;
align-items:center;min-height:100vh;margin:0}}
.c{{background:#fff;border-radius:12px;padding:28px;width:300px}}
h2{{text-align:center;color:#1B3A6B;margin-bottom:18px}}
input{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;
margin-bottom:12px;font-size:14px;box-sizing:border-box}}
button{{width:100%;background:#1B3A6B;color:#fff;border:none;
padding:12px;border-radius:6px;font-size:15px;cursor:pointer}}
.e{{color:red;font-size:12px;margin-bottom:8px}}</style></head>
<body><div class="c"><h2>🔒 Admin MES EXERCICES</h2>
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
        st="✅ Livre" if c["statut"]=="livre" else "⏳ Attente"
        rows+=f"""<tr>
<td><strong>{c['ref']}</strong></td><td>{c['nom']}</td>
<td>{c['telephone']}</td><td>{c['nom_niveau']}</td>
<td>{c['prix']:,} F</td>
<td><span style="background:{sc};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{st}</span></td>
<td>
<a href="/admin/livrer/{c['ref']}" style="background:#1B3A6B;color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;text-decoration:none;margin-right:3px">📤 Livrer</a>
<a href="/admin/renvoyer/{c['ref']}" style="background:#1A7A4A;color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;text-decoration:none">🔄 Renvoyer</a>
</td></tr>"""
    total=len(commandes)
    livres=sum(1 for c in commandes if c["statut"]=="livre")
    ca=sum(c["prix"] for c in commandes if c["statut"]=="livre")
    return Response(f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="20">
<title>Dashboard - MES EXERCICES</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#f0f4f8}}
header{{background:#1B3A6B;color:#fff;padding:14px 18px;
display:flex;justify-content:space-between;align-items:center}}
header h1{{font-size:15px}}
.out{{color:#F5C518;text-decoration:none;font-size:12px}}
.banner{{background:#E8F5E9;padding:8px 18px;font-size:12px;
color:#1B5E20;text-align:center;font-weight:600;
border-bottom:1px solid #A5D6A7}}
.stats{{display:flex;gap:10px;padding:14px;flex-wrap:wrap}}
.stat{{background:#fff;border-radius:8px;padding:12px 16px;
flex:1;min-width:100px;text-align:center;
box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.stat .n{{font-size:24px;font-weight:800;color:#1B3A6B}}
.stat .l{{font-size:10px;color:#888;margin-top:2px}}
.cont{{padding:0 14px 14px}}
.nb{{display:inline-block;background:#F5C518;color:#1B3A6B;
padding:8px 16px;border-radius:6px;text-decoration:none;
font-weight:700;margin-bottom:12px;font-size:13px}}
table{{width:100%;border-collapse:collapse;background:#fff;
border-radius:8px;overflow:hidden;
box-shadow:0 1px 4px rgba(0,0,0,.08);font-size:12px}}
th{{background:#1B3A6B;color:#fff;padding:10px;text-align:left}}
td{{padding:10px;border-bottom:1px solid #f0f0f0}}
.empty{{text-align:center;padding:36px;color:#999;
background:#fff;border-radius:8px}}</style></head>
<body>
<header>
  <h1><span style="background:#fff;border-radius:6px;padding:2px 6px;display:inline-flex;align-items:center;vertical-align:middle;margin-right:8px"><img src="data:image/png;base64,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" alt="MES EXERCICES" style="height:54px;object-fit:contain;display:block"></span> Dashboard</h1>
  <a href="/admin/logout" class="out">Déconnexion</a>
</header>
<div class="banner">⚡ URLs autonomes — Livraison fonctionne même après redémarrage</div>
<div class="stats">
  <div class="stat"><div class="n">{total-livres}</div><div class="l">En attente</div></div>
  <div class="stat"><div class="n">{livres}</div><div class="l">Livrées</div></div>
  <div class="stat"><div class="n">{total}</div><div class="l">Total</div></div>
  <div class="stat"><div class="n">{ca:,} F</div><div class="l">CA (F)</div></div>
</div>
<div class="cont">
  <a href="/admin/nouvelle" class="nb">+ Commande manuelle</a>
  {"<table><thead><tr><th>Réf</th><th>Nom</th><th>Tél</th><th>Niveau</th><th>Prix</th><th>Statut</th><th>Actions</th></tr></thead><tbody>"+rows+"</tbody></table>" if commandes else '<div class="empty">Aucune commande</div>'}
</div></body></html>""",mimetype="text/html")

@app.route("/admin/livrer/<ref>")
@login_required
def livrer(ref):
    livrer_par_ref(ref)
    return redirect(url_for("admin"))

@app.route("/admin/renvoyer/<ref>")
@login_required
def renvoyer(ref):
    livrer_par_ref(ref)
    return redirect(url_for("admin"))

@app.route("/admin/nouvelle", methods=["GET","POST"])
@login_required
def nouvelle():
    if request.method=="POST":
        niveau=request.form.get("niveau")
        nom=request.form.get("nom","")
        telephone=request.form.get("telephone","").replace("+","").replace(" ","")
        ref=gen_ref()
        commandes.append({
            "ref":ref,"niveau":niveau,"nom_niveau":NOMS.get(niveau,niveau),
            "nom":nom,"telephone":telephone,
            "prix":PRIX.get(niveau,0),"statut":"en_attente"
        })
        sauvegarder()
        return redirect(url_for("admin"))
    opts="".join([f'<option value="{k}">{v} — {PRIX[k]:,} F</option>' for k,v in NOMS.items()])
    return Response(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Nouvelle commande</title>
<style>body{{font-family:Arial,sans-serif;background:#f0f4f8;
display:flex;justify-content:center;padding:28px 14px}}
.c{{background:#fff;border-radius:10px;padding:22px;
max-width:380px;width:100%;box-shadow:0 2px 8px rgba(0,0,0,.1)}}
h2{{color:#1B3A6B;margin-bottom:16px}}
label{{display:block;margin-bottom:4px;font-weight:700;font-size:13px}}
select,input{{width:100%;padding:10px;border:1px solid #ddd;
border-radius:6px;font-size:14px;margin-bottom:12px}}
button{{width:100%;background:#1B3A6B;color:#fff;border:none;
padding:12px;border-radius:6px;font-size:14px;cursor:pointer}}
a{{display:block;text-align:center;margin-top:10px;
color:#666;font-size:13px;text-decoration:none}}</style></head>
<body><div class="c"><h2>Nouvelle commande</h2>
<form method="POST">
<label>Niveau</label><select name="niveau">{opts}</select>
<label>Nom client</label><input name="nom" placeholder="Fatou Diallo" required>
<label>Telephone WhatsApp</label>
<input name="telephone" placeholder="221771234567" required>
<button>Enregistrer</button>
</form><a href="/admin">← Retour</a></div></body></html>""",mimetype="text/html")

@app.route("/admin/logout")
def logout():
    session.pop("admin",None)
    return redirect(url_for("login"))

WAVE_LINK = "https://pay.wave.com/m/M_sn_KPX6hNLZUljQ/c/sn/"

MAIN_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MES EXERCICES — Les meilleures méthodes du monde pour vos enfants</title>
<meta name="description" content="Cahiers scolaires numériques PDF pour tous les niveaux du Sénégal. Méthodes Finlande, Singapour, Japon. Livraison instantanée sur WhatsApp.">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Poppins:wght@700;800;900&display=swap');

:root{
  --navy: #1B3A6B;
  --navy-dark: #0F2347;
  --navy-light: #2A5298;
  --orange: #F5821F;
  --orange-light: #FF9A40;
  --orange-pale: #FFF4EB;
  --white: #FFFFFF;
  --gray-50: #F8F9FA;
  --gray-100: #F0F2F5;
  --gray-200: #E0E4EA;
  --gray-500: #6B7280;
  --gray-700: #374151;
  --shadow-sm: 0 1px 3px rgba(0,0,0,.08);
  --shadow-md: 0 4px 16px rgba(0,0,0,.1);
  --shadow-lg: 0 8px 32px rgba(0,0,0,.14);
  --shadow-orange: 0 8px 24px rgba(245,130,31,.35);
  --radius: 14px;
  --radius-sm: 8px;
}

*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:'Inter',system-ui,sans-serif;background:var(--gray-50);color:var(--gray-700);line-height:1.6}

/* ── NAVBAR ── */
nav{
  background:var(--white);
  border-bottom:1px solid var(--gray-200);
  padding:0 32px;
  display:flex;align-items:center;justify-content:space-between;
  height:72px;position:sticky;top:0;z-index:100;
  box-shadow:var(--shadow-sm);
}
.nav-logo img{height:52px;object-fit:contain;display:block}
.nav-links{display:flex;gap:32px;align-items:center}
.nav-links a{color:var(--gray-700);text-decoration:none;font-size:14px;font-weight:500;transition:color .2s}
.nav-links a:hover{color:var(--orange)}
.nav-cta{
  background:var(--orange);color:var(--white)!important;
  padding:10px 22px;border-radius:50px;font-weight:700!important;
  font-size:14px!important;box-shadow:var(--shadow-orange);
  transition:transform .15s,box-shadow .15s!important;
}
.nav-cta:hover{transform:translateY(-2px);box-shadow:0 12px 28px rgba(245,130,31,.45)!important}
@media(max-width:640px){
  .nav-links{display:none}
  .nav-cta{display:block!important;padding:8px 16px!important}
}

/* ── HERO ── */
.hero{
  background:linear-gradient(135deg, var(--navy-dark) 0%, var(--navy) 50%, var(--navy-light) 100%);
  padding:80px 24px 90px;text-align:center;position:relative;overflow:hidden;
}
.hero::before{
  content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;
  background:radial-gradient(ellipse at 30% 50%, rgba(245,130,31,.12) 0%, transparent 60%),
              radial-gradient(ellipse at 70% 30%, rgba(255,255,255,.06) 0%, transparent 50%);
  pointer-events:none;
}
.hero-logo{
  display:inline-block;background:var(--white);
  border-radius:20px;padding:14px 28px;
  box-shadow:0 8px 32px rgba(0,0,0,.2);
  margin-bottom:32px;
}
.hero-logo img{height:80px;object-fit:contain;display:block}
.hero-eyebrow{
  display:inline-flex;align-items:center;gap:8px;
  background:rgba(245,130,31,.15);border:1px solid rgba(245,130,31,.3);
  color:var(--orange-light);font-size:12px;font-weight:700;
  letter-spacing:1.5px;text-transform:uppercase;
  padding:6px 18px;border-radius:50px;margin-bottom:24px;
}
.hero h1{
  font-family:'Poppins',sans-serif;
  color:var(--white);font-size:clamp(32px,5vw,60px);
  font-weight:900;line-height:1.05;letter-spacing:-1px;
  margin-bottom:20px;max-width:800px;margin-left:auto;margin-right:auto;
}
.hero h1 em{color:var(--orange);font-style:normal}
.hero-sub{
  color:rgba(255,255,255,.75);font-size:17px;
  max-width:520px;margin:0 auto 36px;line-height:1.65;
}
.hero-flags{
  display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:40px;
}
.flag{
  background:rgba(255,255,255,.1);
  border:1px solid rgba(255,255,255,.2);
  color:rgba(255,255,255,.9);
  font-size:12px;font-weight:600;
  padding:6px 14px;border-radius:50px;
  backdrop-filter:blur(4px);
}
.hero-ctas{display:flex;gap:14px;justify-content:center;flex-wrap:wrap;margin-bottom:56px}
.btn-primary{
  background:var(--orange);color:var(--white);
  font-family:'Poppins',sans-serif;font-weight:800;font-size:16px;
  padding:16px 36px;border-radius:50px;border:none;
  cursor:pointer;text-decoration:none;display:inline-block;
  box-shadow:var(--shadow-orange);
  transition:transform .2s,box-shadow .2s;
}
.btn-primary:hover{transform:translateY(-3px);box-shadow:0 16px 40px rgba(245,130,31,.5)}
.btn-secondary{
  background:rgba(255,255,255,.1);color:var(--white);
  border:1.5px solid rgba(255,255,255,.3);
  font-weight:600;font-size:15px;
  padding:16px 28px;border-radius:50px;
  text-decoration:none;display:inline-block;
  transition:background .2s;
  backdrop-filter:blur(4px);
}
.btn-secondary:hover{background:rgba(255,255,255,.2)}
.hero-stats{
  display:flex;gap:48px;justify-content:center;flex-wrap:wrap;
}
.hstat-num{color:var(--orange);font-family:'Poppins',sans-serif;font-size:36px;font-weight:900;line-height:1}
.hstat-lbl{color:rgba(255,255,255,.55);font-size:12px;margin-top:4px}

/* ── PROOF STRIP ── */
.proof{
  background:var(--white);
  border-bottom:1px solid var(--gray-200);
  padding:14px 24px;
}
.proof-inner{
  max-width:1000px;margin:0 auto;
  display:flex;gap:0;flex-wrap:wrap;
  justify-content:center;
}
.proof-item{
  display:flex;align-items:center;gap:8px;
  font-size:13px;font-weight:600;color:var(--navy);
  padding:0 24px;border-right:1px solid var(--gray-200);
}
.proof-item:last-child{border-right:none}
.proof-item .dot{
  width:7px;height:7px;border-radius:50%;
  background:var(--orange);flex-shrink:0;
}

/* ── SECTIONS ── */
.section{max-width:1080px;margin:0 auto;padding:72px 24px}
.section-label{
  font-size:11px;font-weight:700;letter-spacing:2px;
  text-transform:uppercase;color:var(--orange);margin-bottom:8px;
}
.section-title{
  font-family:'Poppins',sans-serif;
  font-size:clamp(26px,3.5vw,42px);font-weight:800;
  color:var(--navy);letter-spacing:-.5px;margin-bottom:12px;
}
.section-sub{font-size:16px;color:var(--gray-500);max-width:520px;line-height:1.65}

/* ── PRODUITS GRID ── */
.products-grid{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(210px,1fr));
  gap:18px;margin-top:40px;
}
.product-card{
  background:var(--white);
  border:1.5px solid var(--gray-200);
  border-radius:var(--radius);
  padding:22px;cursor:pointer;
  transition:transform .2s,box-shadow .2s,border-color .2s;
  position:relative;
}
.product-card:hover{
  transform:translateY(-4px);
  box-shadow:var(--shadow-lg);
  border-color:var(--navy);
}
.product-card.pack{
  border-color:var(--orange);
  background:linear-gradient(135deg,#FFF9F5,#FFFBF8);
  grid-column:1/-1;
}
.product-card.pack:hover{border-color:var(--orange-light)}
.badge-top{
  position:absolute;top:-10px;left:16px;
  font-size:10px;font-weight:700;padding:4px 12px;
  border-radius:50px;white-space:nowrap;
}
.badge-navy{background:var(--navy);color:var(--white)}
.badge-orange{background:var(--orange);color:var(--white)}
.niveau-pill{
  display:inline-block;font-size:10px;font-weight:700;
  padding:3px 10px;border-radius:50px;margin-bottom:10px;
}
.np-mat{background:#FFF3E0;color:#E65100}
.np-ci{background:#FCE4EC;color:#C62828}
.np-cp{background:#E8F5E9;color:#2E7D32}
.np-ce1{background:#E3F2FD;color:#1565C0}
.np-ce2{background:#F3E5F5;color:#6A1B9A}
.np-cm1{background:#E8F5E9;color:#1B5E20}
.np-cm2{background:#FBE9E7;color:#BF360C}
.np-cem1{background:#E0F2F1;color:#00695C}
.np-cem2{background:#EDE7F6;color:#4527A0}
.np-pack{background:var(--navy);color:var(--white)}
.product-name{font-weight:700;font-size:15px;color:var(--navy);margin-bottom:6px}
.product-desc{font-size:12px;color:var(--gray-500);margin-bottom:14px;line-height:1.5}
.product-price{font-size:22px;font-weight:800;color:var(--navy);margin-bottom:14px}
.pack .product-price{color:var(--orange)}
.btn-acheter{
  width:100%;padding:11px;border-radius:50px;border:none;
  cursor:pointer;font-size:13px;font-weight:700;
  background:var(--navy);color:var(--white);
  transition:background .2s,transform .15s;
}
.btn-acheter:hover{background:var(--navy-light);transform:translateY(-1px)}
.pack .btn-acheter{background:var(--orange)}
.pack .btn-acheter:hover{background:var(--orange-light)}

/* ── MÉTHODES ── */
.methodes-section{
  background:linear-gradient(135deg,var(--navy-dark),var(--navy));
  padding:72px 24px;
}
.methodes-grid{
  max-width:1080px;margin:40px auto 0;
  display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;
}
.methode-card{
  background:rgba(255,255,255,.07);
  border:1px solid rgba(255,255,255,.12);
  border-radius:var(--radius);padding:22px;
  transition:background .2s,transform .2s;
}
.methode-card:hover{background:rgba(255,255,255,.12);transform:translateY(-2px)}
.m-flag{font-size:28px;margin-bottom:10px}
.m-name{font-weight:700;font-size:14px;color:var(--orange-light);margin-bottom:3px}
.m-pays{font-size:11px;color:rgba(255,255,255,.45);margin-bottom:8px}
.m-desc{font-size:12px;color:rgba(255,255,255,.7);line-height:1.6}

/* ── TÉMOIGNAGES ── */
.temoignages-grid{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
  gap:20px;margin-top:36px;
}
.temo{
  background:var(--white);border:1.5px solid var(--gray-200);
  border-radius:var(--radius);padding:24px;
}
.temo-stars{color:var(--orange);font-size:15px;margin-bottom:10px}
.temo-text{font-size:14px;color:var(--gray-500);line-height:1.7;margin-bottom:16px;font-style:italic}
.temo-name{font-size:13px;font-weight:700;color:var(--navy)}
.temo-role{font-size:11px;color:var(--gray-500)}

/* ── FORMULAIRE COMMANDER ── */
.commande-section{
  background:linear-gradient(135deg,var(--navy) 0%,var(--navy-light) 100%);
  padding:72px 24px;
}
.commande-inner{max-width:940px;margin:0 auto}
.commande-title{
  font-family:'Poppins',sans-serif;
  color:var(--white);font-size:clamp(26px,4vw,42px);
  font-weight:900;text-align:center;margin-bottom:8px;
}
.commande-sub{
  color:rgba(255,255,255,.7);text-align:center;
  font-size:15px;margin-bottom:40px;
}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px}
@media(max-width:640px){.form-grid{grid-template-columns:1fr}}

.form-card{background:var(--white);border-radius:var(--radius);padding:28px}
.form-card h3{font-size:16px;font-weight:700;color:var(--navy);margin-bottom:20px}
.niveaux-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
.niv-btn{
  border:2px solid var(--gray-200);border-radius:10px;
  padding:10px 8px;cursor:pointer;text-align:center;
  background:var(--white);transition:all .15s;
}
.niv-btn:hover{border-color:var(--navy);background:var(--gray-50)}
.niv-btn.sel{border-color:var(--orange);background:var(--orange-pale)}
.nn{font-weight:700;font-size:12px;color:var(--navy)}
.np{color:var(--orange);font-size:11px;margin-top:2px;font-weight:600}
.pack-btn{grid-column:1/-1;border-color:var(--orange-light);background:var(--orange-pale)}
.pack-btn.sel{border-color:var(--orange);background:#FDEBD0}
.recap{
  background:var(--gray-50);border:1px solid var(--gray-200);
  border-radius:10px;padding:12px;margin-bottom:14px;
  display:none;font-size:13px;
}
.recap strong{color:var(--orange);font-size:18px}
label{display:block;margin-bottom:5px;font-weight:600;font-size:13px;color:var(--gray-700)}
input{
  width:100%;padding:12px 14px;
  border:1.5px solid var(--gray-200);border-radius:10px;
  font-size:14px;margin-bottom:14px;
  transition:border-color .2s;font-family:inherit;
}
input:focus{outline:none;border-color:var(--orange);box-shadow:0 0 0 3px rgba(245,130,31,.1)}
.btn-commander{
  width:100%;background:var(--orange);color:var(--white);
  border:none;padding:15px;border-radius:50px;
  font-size:16px;font-weight:800;cursor:pointer;
  font-family:'Poppins',sans-serif;
  box-shadow:var(--shadow-orange);
  transition:transform .2s,box-shadow .2s;
}
.btn-commander:hover{transform:translateY(-2px);box-shadow:0 12px 32px rgba(245,130,31,.5)}

.info-card{
  background:rgba(255,255,255,.08);
  border:1px solid rgba(255,255,255,.15);
  border-radius:var(--radius);padding:28px;color:var(--white);
}
.info-card h3{font-size:16px;font-weight:700;color:var(--orange-light);margin-bottom:20px}
.step{display:flex;gap:14px;align-items:flex-start;margin-bottom:18px}
.step-n{
  width:32px;height:32px;border-radius:50%;
  background:var(--orange);color:var(--white);
  font-size:14px;font-weight:800;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
}
.step-t strong{display:block;font-size:13px;font-weight:700;margin-bottom:2px}
.step-t span{font-size:12px;color:rgba(255,255,255,.65)}
.auto-badge{
  background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);
  border-radius:10px;padding:12px;font-size:12px;
  color:rgba(255,255,255,.9);text-align:center;
  margin-top:16px;font-weight:600;
}

/* ── FAQ ── */
.faq-list{margin-top:32px}
.faq-item{
  background:var(--white);border:1.5px solid var(--gray-200);
  border-radius:var(--radius);margin-bottom:10px;overflow:hidden;
}
.faq-q{
  padding:18px 22px;font-size:14px;font-weight:700;
  cursor:pointer;display:flex;justify-content:space-between;align-items:center;
  color:var(--navy);
}
.faq-q:hover{background:var(--gray-50)}
.faq-a{
  display:none;padding:0 22px 18px;
  font-size:13px;color:var(--gray-500);line-height:1.7;
}
.faq-item.open .faq-a{display:block}
.faq-arrow{
  width:24px;height:24px;border-radius:50%;
  background:var(--gray-100);color:var(--gray-500);
  display:flex;align-items:center;justify-content:center;
  font-size:11px;flex-shrink:0;transition:transform .2s,background .2s;
}
.faq-item.open .faq-arrow{transform:rotate(180deg);background:var(--orange);color:var(--white)}

/* ── CTA FINAL ── */
.cta-final{
  background:var(--orange);padding:72px 24px;text-align:center;
}
.cta-final h2{
  font-family:'Poppins',sans-serif;
  color:var(--white);font-size:clamp(26px,4vw,44px);
  font-weight:900;margin-bottom:12px;
}
.cta-final p{color:rgba(255,255,255,.8);font-size:15px;margin-bottom:28px}
.btn-cta-white{
  background:var(--white);color:var(--orange);
  font-family:'Poppins',sans-serif;font-weight:800;font-size:16px;
  padding:16px 40px;border-radius:50px;
  text-decoration:none;display:inline-block;
  box-shadow:0 8px 24px rgba(0,0,0,.15);
  transition:transform .2s,box-shadow .2s;
}
.btn-cta-white:hover{transform:translateY(-3px);box-shadow:0 14px 36px rgba(0,0,0,.2)}

/* ── FOOTER ── */
footer{
  background:var(--navy-dark);
  color:rgba(255,255,255,.5);
  padding:48px 24px;text-align:center;
}
.footer-logo{
  display:inline-block;background:var(--white);
  border-radius:14px;padding:10px 20px;margin-bottom:20px;
}
.footer-logo img{height:48px;object-fit:contain;display:block}
.footer-tagline{font-size:13px;margin-bottom:20px;color:rgba(255,255,255,.5)}
.footer-links{
  display:flex;gap:24px;justify-content:center;
  flex-wrap:wrap;margin-bottom:20px;
}
.footer-links a{
  color:rgba(255,255,255,.6);text-decoration:none;
  font-size:13px;font-weight:500;transition:color .2s;
}
.footer-links a:hover{color:var(--orange)}
.footer-bottom{font-size:11px;color:rgba(255,255,255,.25)}

/* ── BOUTON WA FLOTTANT ── */
.wa-float{
  position:fixed;bottom:24px;right:24px;
  background:#25D366;color:var(--white);
  width:56px;height:56px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:26px;text-decoration:none;
  box-shadow:0 4px 16px rgba(37,211,102,.4);
  z-index:999;transition:transform .2s,box-shadow .2s;
}
.wa-float:hover{transform:scale(1.1);box-shadow:0 8px 24px rgba(37,211,102,.5)}
</style>
</head>
<body>

<!-- NAVBAR -->
<nav>
  <div class="nav-logo">
    <img src="data:image/png;base64,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" alt="MES EXERCICES" style="height:54px;object-fit:contain;display:block">
  </div>
  <div class="nav-links">
    <a href="#methodes">Méthodes</a>
    <a href="#cahiers">Cahiers</a>
    <a href="#faq">FAQ</a>
    <a href="#commander" class="nav-cta">Commander →</a>
  </div>
</nav>

<!-- HERO -->
<div class="hero">
  <div style="position:relative;z-index:1">
    <div class="hero-logo">
      <img src="data:image/png;base64,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" alt="MES EXERCICES" style="height:54px;object-fit:contain;display:block">
    </div>
    <div class="hero-eyebrow">
      <span>★</span> Lancement Officiel 2025-2026 · Sénégal
    </div>
    <h1>Les <em>meilleures méthodes<br>du monde</em> pour vos enfants</h1>
    <p class="hero-sub">Cahiers scolaires numériques PDF — De la Maternelle au BFEM — Adaptés au programme sénégalais</p>
    <div class="hero-flags">
      <span class="flag">🇫🇮 Finlande #1 PISA</span>
      <span class="flag">🇸🇬 Singapour Maths</span>
      <span class="flag">🇯🇵 Japon</span>
      <span class="flag">🍀 Montessori</span>
      <span class="flag">🇫🇷 France MEN</span>
      <span class="flag">🌐 IB PYP</span>
      <span class="flag">🇬🇧 Jolly Phonics</span>
    </div>
    <div class="hero-ctas">
      <a href="#commander" class="btn-primary">📚 Commander maintenant →</a>
      <a href="#methodes" class="btn-secondary">Découvrir les méthodes</a>
    </div>
    <div class="hero-stats">
      <div><div class="hstat-num">9</div><div class="hstat-lbl">Niveaux scolaires</div></div>
      <div><div class="hstat-num">7</div><div class="hstat-lbl">Méthodes mondiales</div></div>
      <div><div class="hstat-num">100</div><div class="hstat-lbl">Pages par cahier</div></div>
      <div><div class="hstat-num">500+</div><div class="hstat-lbl">Exercices par cahier</div></div>
    </div>
  </div>
</div>

<!-- PROOF STRIP -->
<div class="proof">
  <div class="proof-inner">
    <div class="proof-item"><span class="dot"></span> Livraison instantanée WhatsApp</div>
    <div class="proof-item"><span class="dot"></span> PDF imprimable à l'infini</div>
    <div class="proof-item"><span class="dot"></span> Programme MEN Sénégal</div>
    <div class="proof-item"><span class="dot"></span> Diplôme de réussite inclus</div>
    <div class="proof-item"><span class="dot"></span> Wave · Orange Money</div>
  </div>
</div>

<!-- MÉTHODES -->
<section class="methodes-section" id="methodes">
  <div style="max-width:1080px;margin:0 auto">
    <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:rgba(245,130,31,.7);margin-bottom:8px">Nos sources</div>
    <div style="font-family:'Poppins',sans-serif;font-size:clamp(26px,4vw,42px);font-weight:900;color:#fff;margin-bottom:10px">
      7 systèmes d'excellence,<br><em style="color:var(--orange)">tous les #1 mondiaux</em>
    </div>
    <div class="methodes-grid">
      <div class="methode-card"><div class="m-flag">🇫🇮</div><div class="m-name">Finlande</div><div class="m-pays">PISA #1 mondial</div><div class="m-desc">Apprentissage par la curiosité et la créativité, pas la mémorisation.</div></div>
      <div class="methode-card"><div class="m-flag">🇸🇬</div><div class="m-name">Singapour</div><div class="m-pays">TIMSS #1 en maths</div><div class="m-desc">Modèle barre visuel — comprendre avant de calculer.</div></div>
      <div class="methode-card"><div class="m-flag">🇯🇵</div><div class="m-name">Japon</div><div class="m-pays">PISA Top 3</div><div class="m-desc">Rigueur, calligraphie et maîtrise progressive étape par étape.</div></div>
      <div class="methode-card"><div class="m-flag">🍀</div><div class="m-name">Montessori</div><div class="m-pays">100+ ans d'expérience</div><div class="m-desc">Matériel sensoriel et apprentissage autonome centré sur l'enfant.</div></div>
      <div class="methode-card"><div class="m-flag">🌐</div><div class="m-name">IB PYP</div><div class="m-pays">159 pays</div><div class="m-desc">Esprit critique et connexions interdisciplinaires dès le plus jeune âge.</div></div>
      <div class="methode-card"><div class="m-flag">🇫🇷</div><div class="m-name">France MEN</div><div class="m-pays">Programme officiel</div><div class="m-desc">Structure académique et excellence en langue française.</div></div>
      <div class="methode-card"><div class="m-flag">🇬🇧</div><div class="m-name">Jolly Phonics</div><div class="m-pays">Lecture rapide</div><div class="m-desc">Méthode phonique #1 pour apprendre à lire efficacement.</div></div>
    </div>
  </div>
</section>

<!-- CAHIERS -->
<div style="background:var(--gray-50);padding:4px 0">
<div class="section" id="cahiers">
  <div class="section-label">Nos produits</div>
  <div class="section-title">9 cahiers — Un pour chaque niveau</div>
  <div class="section-sub">De la Maternelle au BFEM, chaque cahier couvre les 3 trimestres avec 100 pages et 500+ exercices.</div>
  <div class="products-grid">
    <div class="product-card" onclick="sc('maternelle')">
      <div class="niveau-pill np-mat">Maternelle · 4-6 ans</div>
      <div class="product-name">📚 Cahier Maternelle</div>
      <div class="product-desc">Lettres, chiffres, formes, couleurs. Montessori + Jolly Phonics.</div>
      <div class="product-price">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="sc('ci')">
      <div class="niveau-pill np-ci">CI · 6-7 ans</div>
      <div class="product-name">📚 Cahier CI</div>
      <div class="product-desc">Lecture syllabique, additions simples. Jolly Phonics + Finlande.</div>
      <div class="product-price">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="sc('cp')">
      <div class="niveau-pill np-cp">CP · 6-7 ans</div>
      <div class="product-name">📚 Cahier CP</div>
      <div class="product-desc">Lecture complète, soustraction, grammaire de base. France MEN.</div>
      <div class="product-price">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="sc('ce1')">
      <div class="niveau-pill np-ce1">CE1 · 7-8 ans</div>
      <div class="product-name">📚 Cahier CE1</div>
      <div class="product-desc">Tables de multiplication, conjugaison. Singapour Math.</div>
      <div class="product-price">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="sc('ce2')">
      <div class="niveau-pill np-ce2">CE2 · 8-9 ans</div>
      <div class="product-name">📚 Cahier CE2</div>
      <div class="product-desc">Division, compréhension de texte, sciences. Méthode Japon.</div>
      <div class="product-price">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="sc('cm1')">
      <div class="niveau-pill np-cm1">CM1 · 9-10 ans</div>
      <div class="product-name">📚 Cahier CM1</div>
      <div class="product-desc">Géométrie, fractions, histoire du Sénégal. Common Core USA.</div>
      <div class="product-price">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="sc('cm2')">
      <div class="niveau-pill np-cm2">CM2 · CFEE</div>
      <div class="product-name">📚 Cahier CM2</div>
      <div class="product-desc">Préparation CFEE complète. Exercices types examens officiels.</div>
      <div class="product-price">1 000 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="sc('cem1')">
      <div class="niveau-pill np-cem1">CEM1 · 6ème</div>
      <div class="product-name">📚 Cahier CEM1</div>
      <div class="product-desc">Algèbre, analyse littéraire, biologie. Niveau collège complet.</div>
      <div class="product-price">1 200 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card" onclick="sc('cem2')" style="border-color:var(--navy)">
      <div class="badge-top badge-navy">⭐ BFEM</div>
      <div class="niveau-pill np-cem2">CEM2 · BFEM</div>
      <div class="product-name">📚 Cahier CEM2</div>
      <div class="product-desc">Préparation BFEM. Épreuves types, corrigés, méthodes avancées.</div>
      <div class="product-price">1 500 FCFA</div>
      <button class="btn-acheter">Commander →</button>
    </div>
    <div class="product-card pack" onclick="sc('pack')">
      <div class="badge-top badge-orange">🔥 MEILLEUR CHOIX — ÉCONOMIE -44%</div>
      <div style="margin-top:8px" class="niveau-pill np-pack">Pack Complet · 9 niveaux</div>
      <div class="product-name">📚 Pack Complet MES EXERCICES</div>
      <div class="product-desc">Les 9 cahiers en un seul achat. Économisez 4 700 FCFA par rapport aux achats séparés !</div>
      <div class="product-price">6 000 FCFA <span style="font-size:14px;color:var(--gray-500);text-decoration:line-through;font-weight:400">10 700 FCFA</span></div>
      <button class="btn-acheter">Commander le Pack →</button>
    </div>
  </div>
</div>
</div>

<!-- TÉMOIGNAGES -->
<div style="background:var(--white);padding:72px 24px">
  <div style="max-width:1080px;margin:0 auto">
    <div class="section-label" style="text-align:center">Témoignages</div>
    <div class="section-title" style="text-align:center;margin-bottom:32px">Ce que disent les parents</div>
    <div class="temoignages-grid">
      <div class="temo">
        <div class="temo-stars">★★★★★</div>
        <div class="temo-text">"Mon fils de CE1 a progressé en maths en 2 semaines. Les exercices avec les baobabs et les mangues, il adore !"</div>
        <div class="temo-name">Aïssatou Diallo</div>
        <div class="temo-role">Maman · Dakar</div>
      </div>
      <div class="temo">
        <div class="temo-stars">★★★★★</div>
        <div class="temo-text">"J'utilise le cahier CM2 pour préparer le CFEE de ma fille. La structure en 3 trimestres est parfaite et très bien organisée."</div>
        <div class="temo-name">Ibrahima Sow</div>
        <div class="temo-role">Papa · Thiès</div>
      </div>
      <div class="temo">
        <div class="temo-stars">★★★★★</div>
        <div class="temo-text">"Reçu en 4 minutes sur WhatsApp ! Imprimé le soir même, mon fils a commencé le lendemain. Excellent service !"</div>
        <div class="temo-name">Fatou Ndiaye</div>
        <div class="temo-role">Maman · Ziguinchor</div>
      </div>
    </div>
  </div>
</div>

<!-- FORMULAIRE COMMANDER -->
<section class="commande-section" id="commander">
  <div class="commande-inner">
    <div class="commande-title">📚 Commander votre cahier</div>
    <div class="commande-sub">Payez avec Wave ou Orange Money · PDF reçu sur WhatsApp en moins de 2 minutes !</div>
    <div class="form-grid">
      <div class="form-card">
        <h3>Choisissez votre niveau</h3>
        <form method="POST" action="/commander">
          <div class="niveaux-grid">
            <div class="niv-btn" id="btn-maternelle" onclick="ch('maternelle',this)"><div class="nn">Maternelle</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-ci" onclick="ch('ci',this)"><div class="nn">CI</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-cp" onclick="ch('cp',this)"><div class="nn">CP</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-ce1" onclick="ch('ce1',this)"><div class="nn">CE1</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-ce2" onclick="ch('ce2',this)"><div class="nn">CE2</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-cm1" onclick="ch('cm1',this)"><div class="nn">CM1</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-cm2" onclick="ch('cm2',this)"><div class="nn">CM2</div><div class="np">1 000 F</div></div>
            <div class="niv-btn" id="btn-cem1" onclick="ch('cem1',this)"><div class="nn">CEM1</div><div class="np">1 200 F</div></div>
            <div class="niv-btn" id="btn-cem2" onclick="ch('cem2',this)"><div class="nn">CEM2 BFEM</div><div class="np">1 500 F</div></div>
            <div class="niv-btn pack-btn" id="btn-pack" onclick="ch('pack',this)"><div class="nn">🔥 Pack 9 niveaux</div><div class="np">6 000 F (-44%)</div></div>
          </div>
          <input type="hidden" name="niveau" id="ni" required>
          <div class="recap" id="rc">
            Niveau : <span id="rn"></span><br>
            Montant : <strong id="rp"></strong>
          </div>
          <label>Votre prénom et nom</label>
          <input type="text" name="nom" placeholder="Ex: Fatou Diallo" required>
          <label>Votre numéro WhatsApp</label>
          <input type="tel" name="telephone" placeholder="Ex: 221771234567" required>
          <button type="submit" class="btn-commander">✅ Commander et payer →</button>
        </form>
      </div>
      <div class="info-card">
        <h3>Comment ça marche ?</h3>
        <div class="step"><div class="step-n">1</div><div class="step-t"><strong>Choisissez votre niveau</strong><span>Sélectionnez parmi les 9 niveaux disponibles</span></div></div>
        <div class="step"><div class="step-n">2</div><div class="step-t"><strong>Payez le montant exact</strong><span>Wave avec montant pré-rempli ou Orange Money *144#</span></div></div>
        <div class="step"><div class="step-n">3</div><div class="step-t"><strong>Cliquez "J'ai payé"</strong><span>Un bouton vert vous livre le cahier instantanément</span></div></div>
        <div class="step"><div class="step-n">4</div><div class="step-t"><strong>Recevez votre PDF !</strong><span>Cahier reçu sur WhatsApp en moins de 2 minutes</span></div></div>
        <div class="auto-badge">⚡ Livraison 100% automatique · Disponible 24h/24</div>
        <div style="margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,.1)">
          <div style="font-size:13px;color:rgba(255,255,255,.7)">Modes de paiement acceptés</div>
          <div style="display:flex;gap:10px;margin-top:8px">
            <span style="background:rgba(255,255,255,.12);padding:6px 14px;border-radius:50px;font-size:12px;font-weight:600;color:#fff">💙 Wave</span>
            <span style="background:rgba(255,255,255,.12);padding:6px 14px;border-radius:50px;font-size:12px;font-weight:600;color:#fff">🟠 Orange Money</span>
          </div>
          <div style="font-size:12px;color:rgba(255,255,255,.6);margin-top:12px">
            📞 <strong style="color:#fff">+221 77 134 34 99</strong>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- FAQ -->
<div class="section" id="faq">
  <div class="section-label">Questions fréquentes</div>
  <div class="section-title">Tout ce que vous devez savoir</div>
  <div class="faq-list">
    <div class="faq-item"><div class="faq-q">C'est quoi exactement MES EXERCICES ?<span class="faq-arrow">▾</span></div><div class="faq-a">MES EXERCICES est une collection de cahiers scolaires numériques PDF couvrant tous les niveaux du système sénégalais, de la Maternelle au BFEM. Chaque cahier contient 100 pages d'exercices inspirés des 7 meilleures méthodes éducatives mondiales, adaptées au programme officiel du MEN Sénégal.</div></div>
    <div class="faq-item"><div class="faq-q">Comment vais-je recevoir le cahier après paiement ?<span class="faq-arrow">▾</span></div><div class="faq-a">Après votre paiement Wave ou Orange Money, cliquez sur le bouton vert "J'ai payé". Le lien vers votre PDF sera envoyé automatiquement sur WhatsApp en moins de 2 minutes au numéro que vous avez fourni.</div></div>
    <div class="faq-item"><div class="faq-q">Puis-je imprimer le cahier plusieurs fois ?<span class="faq-arrow">▾</span></div><div class="faq-a">Oui ! Un achat = une licence illimitée pour votre usage personnel. Vous pouvez imprimer autant d'exemplaires que vous voulez, pour tous vos enfants.</div></div>
    <div class="faq-item"><div class="faq-q">Le programme est-il adapté au Sénégal ?<span class="faq-arrow">▾</span></div><div class="faq-a">Absolument ! Les cahiers suivent le programme officiel du MEN Sénégal avec des contextes africains (baobab, mil, Tabaski, Dakar...). Les méthodes mondiales sont intégrées EN PLUS du programme officiel.</div></div>
    <div class="faq-item"><div class="faq-q">Y a-t-il des tarifs pour les enseignants et les écoles ?<span class="faq-arrow">▾</span></div><div class="faq-a">Oui ! Les établissements scolaires et enseignants peuvent bénéficier de tarifs préférentiels. Contactez-nous sur WhatsApp (+221 77 134 34 99) pour un devis personnalisé.</div></div>
  </div>
</div>

<!-- CTA FINAL -->
<div class="cta-final">
  <div style="max-width:600px;margin:0 auto">
    <div style="font-size:48px;margin-bottom:12px">🎓</div>
    <h2>Offrez à votre enfant<br>le meilleur du monde</h2>
    <p>7 méthodes mondiales · 100 pages · 500+ exercices · Diplôme inclus</p>
    <a href="#commander" class="btn-cta-white">📚 Commander maintenant →</a>
  </div>
</div>

<!-- FOOTER -->
<footer>
  <div class="footer-logo">
    <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAAA4CAYAAAALrl3YAAAtVElEQVR42r28d5hlVZU2/q61z7m5QndVdQSa0E1oMo00gtAoptEBDDR+qOA4Y5oRjGMORekEEVBHHEfGwJiFNs2AjAKKbUAlCkgjNKGhc1V3pZvPOXu93x9n36JEv9/v+Wy+Oc9Tz6177j5n77323iu+a0mr1fowSRURAgZAAQBmRlVk+f9wqpr/AMBgEIqIkKRI/iyS0IRZlsUARFWF5JOt8nYIXwkgQ94pALjwN3f1nnUu7wnQxACNVL2ZFQB4M4vyfvOxmxnCOAxAZmaqqnN9kIx643jKWFIAkZllAKCRGgwFkjp//BQRek9V9QAkzEHC6+KnztcMkD8kluV9mQDaG4cAiEVEFIqEIjQzApqpokdcyzvVNP+0FAABy2BKklSNuvmnZgASMwOAbB4BEiFNVdMwaRqMqgpVTQCYKrwqUgAeiiRfb8ssvExVk/AfAWQKWD5WAwCvqmkYe4L83Yb8fYTCoijK350/QAp9vt/MA/C9jWFmcXhfpqqhD1BEsiiaG7/Re1PVNIy1t/AMf6kITVUzkpYvluV9KDIR8WEsWZhPb1w+jAdKzwXhIRWRohm8iFQB0AwlCqsATESqYeJOhBGA1HtfC5MTAMVwOiowQFVFKGWopiQrADxJdeIikimZv9cMzgwlAJ7e18wMBqiIOBFJKawGIgJAOXyWgIgAnIiUVDWMWY2ko2cZgFdo1CO2mZUAZE5cEQBV1VGkACAlWQ47XgHE+cJrMRDLec8SYF0Ki4HwsWVWBtBVRRw2lxOREqAZyTLyja0iUlBFIpRSeDYKtErDp4bTUSRZVxEZd+JK+Un0CUWqJJv5y2FC6YpIxXs2w0MqIl0RqYlIU0R6LzURllW16ZyLRUQ8fUJhX69dOLYJyaqINKEoBfaYkX5QxDVCO0cyE5GKUJpOXDEcmK5zUlLVlggLJAskuySrJJve+5Lk/KErIpUsyxLv/VA4ke18Hr5NsggA9D4hWRORZmDJEjZfDUBLnMQilDDmAXo2nXMFKAjVjlAGDUjNrArASM7RxYkrAFCSiffsI9nKaWqEoivCmipaAApm5kSkTXKZisgSkm0REedcQci6iNRItuf4orDunKsyJ2xKsiwidZJ9ItJWVcn5s8wCqHr6lKR3zsVCmRGRWpr6bs6BpeCcm6WwBsv5r6qqiJsWkYqINMNilEg2RFgj2VFVgWrReza89/1h06QkyySbJKsudk0ojGSJZDuKtOxiNwnAxKf9ImzEcRyT7NL7yDlXFCezQvaZmc+5r1JEZkn2ee89Kcw3mJsh2e+9T+ipkSKmcG9+kqwbTkiR9LMiUibZISniXFFEejTt5PsKJVIaZqioaltVMxGpOOd2SKvVenfOAub4WQwgVVUJrCgDoEFYajh2AOAC/457fJFkRUQagMWqEbMsU1LKImwr4KBqqjBSiiQTAFBoajBTRTEzo+IP+whHuxBYT6aqUe8eyVhE0tCuS7LqvU+jKOoJ3BSwMqJqizFa0m4OGdTUMgdVbwZT1RgadRSmZhaFeWaq2u2xFDNTEXHe+27o3wPIwolrRVHkghwQAEUzJKqIAGP+uPXYWiE82wUQPXnPNMsMzrmCAiiIiAbeFouIAxAHQrvwkkhVYxGJw4JFIuLMLBYRp/mzLgitCFA1s6KZxVEEAxCJcy7XYhAHYkWqKgaLwiRihcZCPqWPJ8cXqbp5PNg55xJVKElnZkUAjKJIAcSqUJhFKFe9br6pEN/08XNYrjrNEkWpLwVUNYoU0EzaMzXkupnMkyUFs7lF0lwryumjT44DPZYDmKjmYwasQEqEXIbFzjkFrDcPByBG/t5CjyZhoVVJ9gUWISISkUwkF3Y+CNYoCL6i994DQGiXkixSmJkCUESq2ulNhKTExdiRkjjnCiSzoPZFJBPnXCFoUvniAKmIFHwQ4L0+nJMCSQ9AsnwCiXMSBdnjSIlJdp1zBRFmFIpzzuUao8ZIU7HFh0v80A+k8NDNBfYNRHj856uk23RWLFp8yyV/63771VUoxh0Rr5oLnMx7X5mbR/zkPLz3PssyDSpuN4oiAZCaISKl1JubCL2qzs1DxIV5qAEWQ3Xu5If5xiSbKiLjgV8zLEZPqBdJ+iDQ+kSk4ZwrAIDPhWFVRJpCybUWaOK97w+CN3bOpaT02EjTk6WeUBcnFZJNKOKwy7qU/F4QhpgvrMMG4ZxgJjsURshPR9c5Vw7tYqF4eiakrxrQ1SxRDO2fdV/z3zdkLFdcOrun8JOLz+Ls+JB7/K5DbXDFzuzUt9zFTmfQ09HMMnpfEZFZ5+JIVeG979L7KpkL9SiKDEAnCP9u0OBIsiNujn4FM5ujVY+mgCmgXRGpqGqLOV2EZJvCEaVwife+HU5IMRekuQDKTwhLzrlZEekj2Q2rWRRhwzlXE0pHKC5N05qIdMRJRcR1zMzR+1LvfU6kE3ZMkZ5N730fLDcmNZcHDRGpee+7+YJISUQa4qQWFkeD0O/Ss08obRgoIiXv2Q4nvQtAvPcl79lU1SKiUgd7toD1u9bJkiU73B1jb3KdJ4bijZ9y2YoTdmenvOlrjr4WNCTtbT5VrYqwGzZqiSKN8FsHgFDmlInBIAvgnCvRPzkPM4NzruicqzvnAk3pgvxrkewPnIYirAhll7RarfcFrcAHQygOg+uxikxVXZZlFJFYRDwUJpSeylmQ/KwnwdJNSJbzdZNMRAoUdkUkpqeZWdBapBuEYDCq1AFGoUQUWlAjC0GFLZDMzMyClpR6zxgwiogPv3dJFgCYcy63UJMOxcV9LpvZGd90/ru09ehSiAG7MqBRgRVLk1x6zHT3JZ/+hpb6TUS8mfWEeZrbZYY/6ENYoM/p4nINqgnAhblob8wkC845b2b5PMiu5Ky7GxSCsoh0zKwoQvGe3jlXVst5fs+ylmAxOpKZqhJAlGWZ5Bs5uDkMamY+6M+9dhqs20hETES6AIRkBoPS08LjEojrcks9F6IizNUroeXGoalzLguT9AAQRZH33luWZU6EmXMuhZl677OgCfncXWHwPnVaGcikUtnNwtBgd+2/XmnJwGPWRIZOlCFtUDuzu9OT/urnHFzUposT770abI6vk+xZ2fk8ABWKV1VGUcRgFMfBVYQwhiwI7jlnAxTewr2wAZWkBbePAdrTYBN1IqV8J1NExFGYiTAO+rxKrpunIi4OWhQ86UhmzrkoHPPIe18OxM6tVEXEfIeZ976c7zTncjlkRrIU/GIaDEHvc4secRyrUApZlpmIlHtC3pNVVc2CLFPvfYFOCgBMnJTNDLmlnpalUqu7zT85Kb7hXW/HHV8a5H5Hlrn42Ej3zEaotyKopN033nQvlx+XFDZ+9ihMPT4iLqYTFwXjsJR3SydkMez0ssEQ6FQMC1bpbcgoipjTijFJb2ag0DlxqXMuDu0LIlKEohM2sXnvGYR/W0VkT25cBYErrkJKU3IebhRpBy2pFVgCnEgSBGk33K+r6q7c94StwRuVQGTcORdrpNuC0GuY2QRz9Xl77htiC8BeKBSw7ZYvVhPAhHMSm9m2wJrqMNuVZZkDsDMQrWGGiaCOb4MqnXMNaDRuKcpSrN3Fw190Y/qsN23CE7ctdg/8YgmG196crX3toyhKwd32pR0cWDItj/8axR9dUmIxnrEsmcrVbtuVbxxpirhx51wM1W3hwDazJJt2zkUAtqlql2Tde1/wPq1SpCf8IZQkTdM5QR88jG2hVEVkkmR/zr5YV9X9Iu/9UpJTqhoDKIKsk+wD0Ax6d9V736T3/XTSEkiwSDlrZstV9Vt79uy5e//99/fBwGwBKO3YscOWLVuWTU1NlR999NHWihUrSsPDw9nmzZtteHi49Oijj7b233//4qJFizwA27sXxS1b7myvWLGilCSJbzabvtfuwAMPLG/blvpKpZ4tXLiwODQ01N6zZ09peHg4A+Cf2gcAP71lS6V60Ekzm4HCr2/cFV2w4KqfdvuOuul5d7y+eNnnz7lu7a671kcP/bgxCfxg8eu+02DSLE7v2OGWLVvm9+7dWxwaGmqF+RiA7E/1EX5vAyhv2bIlWbx48VsBF9GzZrS2auRIFp1zDZL9AFokZ0mOkJw2s7Wqer1zrphk2akKf720Wq33BhU2C7uuEDSsYjh2luvV0iFZ9KSHmYlIrKog+XClUvkK/mcvnee2/6OLgEjOq10gHFaceeUzs0wvLXR2HXdi/aPDGzYh+f95zf/11W63X6Cqz/Wpn6Sw7EmvAJ1zSrIBoOycW+u9/6pz7mQzW27OLo0YdUj/Ju/5iEqQIcFo6zn1evyuF9Pokix4773mjNUFl0VRVWdDDEBJyrw4xtzfvt676qo74le88eoDz3/H14dzQ7xHRcro6Ohcv6OjozpvMQDAX/CWLx9w1POv+HzRt26Ns/pp3cSmVq+/tsBr4UZHP6Qkhbns25cxa/g+mGUZxUmVwtQ50SiKSHLYzF7kvX9IVQdEZMSTUyRvV6/nmNmrzWxCVRdKs9n8JxFpkYxybzGT4DzsBvdxb0EqIpKYmbrYKT07JBeS/HGtVvvhvEDP03CNKtZBsehIXrseGP3cYz8wRi+gJd4pxp3KTxf0V75w6/ff8hNPAKOjOgpgbGzMIBHS7775jNt1zbY3fnbPeWk3fU9irp8+sXazBVp34pyThw67amm7LmOXENj3MQcbyZrt9kX0vu2ce4zkeWa2Q0R2k3yRiDyoqm0zm3LODQSNtNs7xWZWEJGSNJvNi1V1MckOoIkIB0Rk2pODQnaDwBoguUdEFgQ9miRrzrkp0s+Wy9XP9Qb1dPOmZ5x96Ykzs4XbS0V/aSHib7tJdmqSujPVFY9w2v3FoftFr/nu1e94VAHYmu8s/f0ZY9897AAOnvb7y189/fD9n2m1O0fSW9n7RJvNRAqxzOwcecV+uOm4JkB5mhZEAKDb7R4hImJmrwkyQoO2tltEFiiQMNcaSXIWQEkVkmXGoDg1pdFofF9EbjKzERHpN7MHVfU4EdkEYITkgJltEpHjVfUBkgMAFgD4HYC/aLfbrx0ZGak/PQdjVDE2xrUvvnRlF5UPxezenlGG2h1+8O1vP7T/jWef3QIAFeBZL/v0aZMzyZUZ9ZDj99cTvrl5Tffvll9z97+uuXEKC1deJK+/4YcOwGFnfvyOdsfWNGb3eCByHa/bbnz95JtPHt49Lhd87zcchcjYvgmSHndot9uHiMg7zGx3znFgwTwoee9bTqRMYQaoBbFQB1AJdg9JLlAIHg7mP0KgZqGITIlIn4gkIjITRdGgqk5SWMtDF9KAYhjA9lqttmb+LtnXSwSsd+xfu2l0QX8tnmw0Wi83S372xrPPbq1ePVrAutHICPnZd97y89/f8q7jYifX3/NE6ycH6i9uqdWKt+Ld3zhCXv/fPwSAI878pw+lmVvTbjcybxC4+ImuFfv727ufie0PXAWJniYWOxdTP917P0EyokgqIhbsj45zUqYwAeYcju2gpXWDK6YkIntURWeDS4Qi0nMHdIMLnE5cCqAoIl2hxMgBDqlCi865pogMPWVQ+3I67C8u/MwSsvjckjbe+4zT9v9hVBw8qlqJvwpARkZg2DiWAeC6daNR5in3/uhtr1TAR5bKx7/0qbNErqOAeObZn3hxavFHWs2pbjdhtKi/8I2H3tv5K63UvvX4FMZh9cOnr7l4pYzBODqq+8q1gqU+GTwVieYGi5LeSEakZPnZBkO83ZlZL5ZDoSRQFNTM0uAWgZkxuDR88N0jWL+9IJQGVAqD398HT+c+X+t+CgUg23c2zzaqLO0rf/kH//XIX6sYT1h16A0AuPGMJ1nLxo1j2Wte85riJSIyw+GbCpX+X1y73jtgLHvmSz7+/Mm6XdNqdZKkK0UndvOdlw28Z3DLd69rv/47vzrqGYddh1JcqO349Tn5236qT4sunkf/IjOjULQHjAjxE5/HSPIwMSmleWFjNTMRSlmdcwu9Z5ekBLd5i2SFZNfMVBwLQQurkJIE9hQsd+kTkR3zd8mfe23cCBOAmeFv6FuP/OjbF+3qdjtvoG/ddvWV5+weHR2Nrj1yk/Da9Y6j+a748pe/3BlDZO8/5EeHfPWUm/rP2wB/+ksu/+vJWf3PxsxMqd3oFsoF+fn5xxReXn3W+3akXdliEzs/esCr/vVhq3O7m9l5ISQGxjba08GyvPcrSDacc2VPnwavdU4rYYX0SVCPCyJsBeelz1mWlEhOKsldwa1N79n13vflYVjEqupJ6QR5UhdhEbBerKLfzKYAHLyvLGt0dFSBMXv1G646wBifVCwXvnThe784EhUGVkYqXzYCY2Nj2XnnbfBy3gYvY2J3Xz06mH7hBS/mVcd+/U3PvLO1aNHAVw577qc/s3vKvjg9OVtKEu+qJXz1tX+5/IWfXjnWALzEC4a/qDXs17r5Y/trse/LKNkx7e+/+yDBPrMtBvf7w2Y2QnI2aFcIHuK+gFWYD8KokWypaiQiKrkLakkUzPgGgGhO9RKpkL4dBFDsvW+KSDWXLaIB8dFwzo0AuHVfT8hPc3bFTdsbZxMxjj6k8vW775p6JaSAQw5fft09N7EE/PsibL5xCI80DkLbDkTyk+XoFtzG3Ufe/7e3nl6c3jv9iQLaK9qtJpyk2xb2xR9+6NcfuXrsTgCjoxEgWefgt/1nadP3P1H4zedfNXv0X365/9EN74+33vISAJ8MbMv24YQQwEFRFI2bWfDzifZoSqIaTAYH1QJyv15JVdukL4TFmpBGo/HhYNoTBogT8SQ1uBxyz4mTEKiZM/5CnKAI4K5qtfrtfbNDRlVkzA5fd+lvjFz88M/ee+Ahz/rofeK0NLKg/Nli5I4eLnc5UmhKDK876s4enqlUt0xGK5h1n1GNY/XdOsj0ob6+8jeOXTXw2Q1Xv3UCGFXgEpLAnW88Mbru/Dv4wV8efg+FhcJHdq3yHxjaAXF73IcfP4ZMVf7MBenRpdlsngPglLBZHUlmlsGJ0xCSCAjMPFgUvCKR997CLac9uGWIQbCHxwyCHDmKL1PLhZOYGUKwSgN8Jd435Sqwq9dfdQAkOqlY1Kv/5u1fH9a4f/Vgf+njv/zeOz75xK76535xf3vrhrujZd+4K37mxs180e7x2efX0vGlfZj9cTWa+fgBy2sv+/sLjz/uoV98eGzD1W+dwPprHUYBrN+gIsIT//3OdOzZkkUHVf4tLjUPecd7vzaspcpXtOSPbt/w/gOfBrYFVe2G+EYPPAjNEYpiltk8ts4cOJFvgBwEkYPyIhFZQOG0UxcDiEi2nXNVT98UiOTxbNeGsEairapOnMT0bJFcLCLj+8KyAruyTdtbL5aohCWLOl+/fdPOszUe0umZXe85+gWXH9NfLn/7tl+/+ZIkzXW8T/7LvxTPXHomjz3/mMS84ZRzP/PBbic9+Z3vPO97WHlxcfRVC9OxsQ0ANhgAcPKqgV994a7nzExOvvBnd+9+4UOzx8p/3Lf1rCs+teiruG3be9zmm166j2yrx7KWkWw5x7L3vRC4xCJsq8bVECrvoXua80LWEgCCU5GI7ASx0Jvvqmov/NpQ1RgG773vOuf6QMySrFDo4dENgaNxksufMqj/e+1KgHa7c6Ex3Xzj19798GVf+dHOa771+4Ut4SmddnJukkUXHXLa5VDYN4cWFC9761vfejcAYOXFRTy8MJ2ZaZ8okAyArFy5EmNjbzUAePGrP3XUjj3pO0/+XxMXluKDNe2MjNfTI2/doQd+drLwmm/K2os7/NiBT8Sy7XzAfRJjG/2+CHUAW8zsOFVsd87VvPcZVDsgagDrzkmVlMRgHRWt9TQyy73nLZJLpNlsXhoCTL3IXUdEqp6+CUMhIMszESl7z46qutzQYVNEFojIDZVKZeOf5VwMxuCr3vbVpXfeu3tHmiSNUoT/0sg9MlAt3LX0gOGHnn3ygp23/XZm+L7f7Tq73kj+LipWDy5E6XdPOnzRRf/+qQt2YnRUj7m1/yuk4b5TGxdibMwuePOVQ3c/2P1EZu5CZXdrHMmV1UUH/VftjPUTI7/72sjLRu5ZrfXdzxjwew5aVXzsnDunVpRfueWKpa0bjtrVG9Of41xstVqvVuBAnyMnuz2aevquE1fO/YVwIoxIaQUsQ5avh8QiMiuNRuOD83nbvFhDGkXKLLNi4I8+M3Oatw3YKVYAvXvfhDpl/ds/UXrofvvnLOPpmc+WQHSxi6s53L0z66PI/apYdN885MAFv5qcSo4Yn2xf4j1H+kt89W03vOsHxzz/imtA4t6b/v4V6156xQt3T8vXBenkwgV9o5vlqN9xZsupA91tL6+69rq+ci3yUkC300BFO+OAbZvWRXcdd/Tqt33tihe0/hz2O0+ovwTAiUJpGswZDJpb5xKQ9ZKZiQbZ3JMb8+SJk0aj8Z6g5vp5Tq+Oam5R5sAuxMGKj4Jg9yFAxSiK7i8WixueDm+vCiAi+OCHrqnduWVqv4npxpHNRvIsD30+Ea+GONC3f7xkKP56qxudMdvw5/fXeLbP8FIjpa8af3vPlF1fKuk3d8vIT4ZaW151dN+u5x2zOEV/YXbLSIk3FwYW/vLW5up7bsZJj955+TNnkNtv++ztFRE2Go0XiMizSU6rquspSgEemwGIoErNhXoEoAuFU2gKmPOeNanX6x8TkZncBzN3lCoi0gJMvWexJ4BIJmYWBTW4papLROS6crl8yz7HQ9Zf67DhPPtTu1MFeOFrv7Bi9+6Zc5vN9E3U8spYOr+NC1Gj3e4cG7noCXUCy9KDGVUf8N12+rIDx9eeMfTA+PMOmrwKp/sNA2vvvG+283+KLq5XYIPfhwVREbFGY+avVePFOfiNnRzNyEhEWuKkQs8OYJGIcyLSCvDXdJ5Qn5V6q/UO9RyiMDGDdzmqsBGwt2mAU1YD2r3qnEsDUrwXxNpeq9W++DTGQwQgRkcvkU2bjpQN4/cLNo75OWtYgRPP+tSL6o3scu/tiCztGMWpQpBRcFBfF29Yee8T/+v5u9+Hs577bZGxZE5krVsX4QwAOMPG8uDUPrt8/tD9Xj/DezkHwK4AqksDCL0mIrMBFZqGXJmKiMz2MGAGExgWSr1evzTA7+MAmG6HBWiEiGExpCtUe0IprHoTsMXOxdeXy+UfP70Rwz+tAKz7KXRj7u0FSV37l5/8+5lW9o/ea+RJDBQ9/+HUh//hxZds/ieRjR0AuGUU0RkYNRkb49NB/P/vE9L4KzNbISKRCLt5ctOcolTpIXdUVQOHiQN4SwOWIRfqFMZCseBaV+b4K1OFN0McsFcWPnsTk4AxuqdSqVz7/ypi+Ce52/pr3YYN53kAWLf+U8+amEreHDktHr48vvLaL731lnwh1kVnXLLRi4D/r8czF8JtNs8CcCrJhjiJSNLyNAP13vs5j0gu1Gl5AiSCUAfJWBqN2Q8EZLYZjC7nb1lA3lkwYnpo9ygQnSKiZhY75+6tVCrX/E8uyBxrW3+tIizMk4u13l177Qb7n1iIp7KsmZmZs6MoepaQM8x3fI6VE0aSB6yinM4hiKFINU/dcHlwUQpKykBAuIsTF5Ps+hxVmIUoYiFkA5UCT+xB5zuSI9v3/GlVcVTzvz/6LuFz3vf1LqiG8qefGX1qWwCjgg3n2bp1oxHWvCEG1kVY84Z4w4ZrTWRU8vevd1gf2q9f7+besX69y+Ppoa+8zZ/6Tefu/x/H+KSn2xXciJm1gis9zd0iEotIJ2QYpDmdJQLQdeJKPbcVKQURmZF6vf4OAEMBUeJDalXdYLFCkxy/yyop9XlCKfPeV5xzXeewo1SqfjHwQf/HsoRC5pjM+aMXAcgnVzFXeQFvT4aDReQP4sJ8iqui9w7JEZMwC7z0j57J/WUCQEK7+eMDhPP7nx9LEMnzoHoKRa+P3jzDWAUAG43GGaS8RBXbhdIvTlKDZfSskqyLk6pQ5oS6czIbPCMkJTGzoQiKJUKZCelhRRFpiEgNHnVT0/wBaczLO3QkS3HsZgFdmqbZxnJZ+KSxmBN+2bFv/2ClEKUP3y6XigBHPut9f9tOcfCCgcIXxyc6n03TdjGKim5kOL4oTeXo6Zn0Ym+Zi5z/JxG5BgAOOvFdf5d5faVP23GhUHiiVIm/06i3z91x36fOXX7M214TqVszuKB2w5697feRaZE0v2R48OKp2c57Um+rOp1kulaJPvvYnWPfPvr09//F9Gzy4SxjXxzJNbFLf+6pb3j8Lnnl0c/50FlTe9sfMrKmkn196dLBH++e6H4sS1uFKC5H1aJ/Qzu1I70vvjNNu66v4sIYR3tsmgAwOzt7hKpMirCfQIdGFzhLA0BNKG3mGcxFgcySUhVB1wxKsqLKXUrPmSCcGfhcKfVpxwyFEA9JKCx57zs9D7A4SUmpeO9n4LA6RBgHSLpNm7YNkZThwepZMw18bP0brjpgYmJi2e69nU9O7p0+jsTJoli3bu3KT5+wevkV+w0v6N+2ffZLwwvK33jOKSs/cdqpq2d/9NvfVklWBXJu5BitPWHFx5Yt7b/6ta9ce3eW4ZlLjnznl0vFylVLlyz48dbtkyc5xaEnrdnvsjVHHfCpU05eWag3O+ct6C9//oSjV9zWTe2aF7z8H182NdO53oCfH33kks+VS/HgQQcte473+tyzLrj8+K1bp68pV4o3r9h/4ZVLFy1c3ukkpybd7olrjz/4ikMOGPznY1evWNxq6dcG+txXTzvl8I+vWLFw5+Tk5MBVV53lSA6SLOabNH5QRPpJtknGQYCkIdbREWFMTwolU9UCKS1S4gBST0gddB/4wAfWBe1Jeq56FaVz6hmscwEVcHROBQDMmwT/C5y4LMuytWmaHpMkyfOKlfjwSqm47lvfu/3ArdtnFvZXcOLdv9t6/lRdDz7qsMXJS194dOGmn95/OCRaNTHVPOyLn/6rod9t2jZ0/+bxNYtHhlZd+LITdp35jNWnRVF82PU33nPc7j3NlVPTrUNPWnPoSR/7wHnbVx+6hN+5/vevPWzl0K0b//M99z2yZff5d923fYlKYXWSpPt95L1nD373hvvWnP+S4/ccunLJwK/veHTZ4ODAcKfra4/d/rHrLzj3lPpFrztz+72bth2+c/fMwatX7feMTiftv3fj2LV/88rT8PoL1t0zMVF/wa13PLqy3U4Prtb61l5+ybnb77n/iZWPPLb3xFhtvyvGXnHIwQcuHj700P4Xeu8PN7NTkiQ5wXt/nPe+CYg65yBOIMz5kfceIioBKR9SFyAUikAgIlBViXrAagrFqdOQ1lYBrBV89UKyrZpb6oF3ap40ryUAg56UUGHBK7AYwJ5yuXjgha84bu/d9+04/Vvfu3Pni56z+j+2bJ9aa3A6smjQXTr60m2TU43Hli4enL7ikvU/3Lprcvdln7nlHZf928+POvsvTroUwFAc6/4H7je4e+zdZ99WKhVHABzw/R/ec+bQUDzzyON7Dh4fn1yedLPGouFK51/+8dyHd+2efDCO4uWtdtr99nW/fekDm3cNX/y6Z1+/ds1BjddefPWCjb+8b2TtCSsPu/u+x0tDg+VDvPni4sV927bumDrxwc3bjl803Ne6Z9MTx3nvB+ix458/cM49pVK5umzJ4NA/vO+s7ztXOOR5516+/IKL/uPE+3/20R1mlonIcpJ1g5VUtOmcS0N2buqcOCOciLTi2JWZ46MLANSpa5Asq2hKMDYgNu9nIxGZIjmgop0QwSoHH/2gRjojkASKik99AqCmqg1VTQJr6wpZBtSLc61SqeQarVYdwIJdE9PTSxfVHn7XRc+/67EtE/VKtbjiG9/5zUh/X1zePT4tl15540kTexurH3hwx47rbrxnTaFQ3lZvp7Z0uPZjwGqAtpPE79y+q3Hc6GX/VSrGUXLicSsGrvne7dU7b3rfRz/6if/+0Kv+7gvvOuHYAx4c39tcOHb5dafuGp859i1/85xtA7VC9Rv//rrr/+VzN/lv/+ftR3/iIy///n/f8vuZF73qs284fOXShUmaPPySFx7zSKuVRpe866zZn//qoe3PefknXlOtlP2yxX2Ns15w9CMUO/iyf7u5mGbUk9cckF5/473POXC/kbhUiu1FZx7TBDAp4paQvuk9FkZRNJk7ZKM4y5LEYH1ikgAaaGodEdQAZFAYFCUxaeVAxExVoy5VF0m9Xr+U5KxzLrbMInHS6iV+Aoi890URaQdLsxsQ79F8690558xMQgJmpVh03Tvu2bqkEDsef/RBjwHov++Bx6Op6VZx9arF3R/e8sDidicpZxntjFNWPdHqpO7mnz24ctFwpX7heSf/vt32tSiCPLh5t9z1u637t9up9vUVW0tG+hKnrvuc01c3d++e8r+849HhQw9Zktx53+MLm412KXLOP/vUIx7fvGX34JErF48vXTxQ/t4P7xt49imHPrFo0UD52u/ftmLHrhm+7C+Pf0JEonvvf3z4uacd+Wix7Pq/tuH2/smpdvX8lz9jApY1fvTT+1c2254+Mz5v3eGzjVZ35oc/vv/QVYcsSs89a80jjUbHkWzFsat6z3ZAKVZDxYaqiHTFObEsc0Gm9KtqR1UBhaP3HVIqeZ0YQ/B7NaTRaHwglJowEbFeMr6q+izLomAERiKSOudclmUgaSSLItJ1zjkRejNYlmVDIjIbRRErlWICAHv3zg5677uLFg2k3sOmZtrR8ML+VtBMqs1m3arVvsYcPilLqp0kKVQqcX12tlvt7++fCa7pXqpZCPe7IiypQQuzAf2XAih731Xnis28LkpqQBwBKev1JOrrq3bn5XUogAQ+LbZSL5VSTMAZkNr4eL2waNHCGQA1AAafSuZ9KSqU6gB8s9mM6X3BE2VV14oiTQFDllmUq7OuRdKpgt6zl5uZkHQ59NcQ7nV7Wr8ZKI5xND/SFwQ1AziuEOL0Of4hPwESgvWQPAUNZhmgqk5dWiqV9mZZooDp9HSz6JxYuRx3RUqdrdv3Dn/7urtPO3zVsgebzfbme3+/4+iBWqm+aKhc7u+r1gwyPl1vu/5aYevpJ61qfP5rvzx1aro5eMSqxY9GcZTVKsVulvrhdpJkxUJU7iZ+a73ePGBoQZ8TkR0eWFCvd2ZPOn4Fdo7PVGfrnXohjgcF7EzsbVUa7W5raGFl547te5cNDJTbpWIJ3jNZOFhO9182tGPD9bc/t9HsFryl3cMOWj4800ymJvbWp5XZxEWvO3PX4pEFVp+aKToneYEEIYuFYtd7z1BjJVWFOFfohnR+ZJmBQjg4MxhEn0yUyCFWBIUFGExVPEPWbL+qzpCMA1KiA6AqIi2DxSqIAWnn99gGxJGM1UnbUSue7IgxMrECgKZzcZ/3aRZFcGaMvNdOX1+xOLGn2dq9tzGxaHi6/pvf7nhno9G6e7tg6uEt0bIndk66/Zf0LVy+dKg2Xe8cWauW77v1jkcOetZJK6+79ro7T1g03Nc/O9uyZidru0h47OH7Lcy8DZnR33HPVi0UtLpzoj60aGRw4eNbJ78E8UduenDX81cdvOihZiftr8+2CqRNN1v+xL6+4nRfpTCzY3x2yeBAFeViVHjxmUfdt3XHFBePLBjvdJHtnWk2n9g6cciRRyxrgnro3smWrdh/0ZYkSXrof4mi2IXc8iqI1MxEXJ78H6opdQI9IxFpm7eqOm2H7z02VhFI12h5RQ2db6mTieUQ0opQ6uJYzjNP1Qul6sXXQ15c7lL2rPaK0oQU5yzLsmGNokmXg8R8rwyT975RKRWi3z6wY3h6ppUNDhQX91fLDw30lbXZTqOpmWY2vKA6AGF9z97m4sNXLd/7y9sfdEcfsbyzd6rtndPBYiTZ5EzL12qVyn7LFmx/6JHdB5ULrt1otWerlcpwkvrdqtg/Umwl6Q26pN3uThRiWQrReiGKk043WxIX3I79ly4o7ZxoRDSfJmm6oL9WHP/JLx/se/2rT985Pl7n3Zu2rzrqsCVbR4b6Sj+4+b6RU088ZFulUohD8YRKyPrtudDrcRyX88IyJt77OVf7PPd7bqlLnsgDQw+EXReR/kCrxGBDUq/XLyNlWiR3v/dQJyFBMw5GYzP49HuW+nyh3g7JjzKv9FIruPIjirR8mtZIdgYGKoGn+0bSSRd47xNx4kqlgviUTQprkUij3uoU+vrKrt3upsV8sk0DojguZt6nvt1sD9b6yzP5CWeRZINkfxTFs2asJEni4ti1nXN9QLQH8HGSpNVCIa5nme9LvW8XIlVSoiiSZquV9lcqcavR6JZUoZVKuZ4kaX+a+m4xdlGSZRIQnE8iRwyOwraQNXGuGWRtmZ4tOtaEf0gr59x81EkvzFELVnwU8tunZXZ29v3BkvR5tquLPH0aYsE9QFyc1/CQiJRe8n8UFqBA0oeqcWUKu0LGWWYg6eM4jkMifZxlGb2nOScF51zXDFCFZGaQXJlIRCR2zvkky+ierBMS5Qm7tNwbzSxNfayqRmG+2/ISFqGwgZqQUWYGBVScaykQe89Y8iIGhSwz66ULiDDx3sehAEJG9sor+SqA1MUudeJi732vnWme8RulaZoGpadXeKEQCi/EPQ+6iIskt+/igHwnn5yvC+nTXiilKMR5DWRw8cGcOEdhFhZFw0vUck8cVCE5lo5ORBhqHLqQy60AzMXOW2ZufrsoiiCOInkhAFWFzzHeAjyJ7DMzQ6QqImLepwoIcs8zSW8ERAuFyEjSjAKzUOiKeTlImIqoxc6BpANZhIjFseuaZULC4tgRgHhmJiYaRZEZTGiMAXpVcapxx8xgmamnp3NOoyhiDwSXZRlzYIkgKD89Lcg555j/oIAZjQw2NkScQEwCGJtBk6JC4FVEqvR+LukzoLYjGJDXu2KvQlAcSkpA8gXrrXiWF4aBBBBxBIAwSBBqYbd4b2ZwOXgsyf1i5kLVHO2dNgnVgPLJ+dS5uFcTS+gZh2zggvfeI68l4gL4e258TpwDLAuaYq/QWZRlZqGGSi/q6CSv8hOHihPIoTv53EIeIMIJSEgWPOcqIrnQrhBogOAP7FDy8QXsrQvcJc5zRAD6vERiKKqThnIgkYg0FMBOCivBldwVSi0YhS5ARduhbF3DOVcMsPuuUGqSF4wphfqMweWCmZ52EUKX4dm4SJLe+26Pd4q4kDfBjnOuJiIN5tWFAsJeavS+IXmhlyyAyQISX4oUEe99V8Kz86oadURcVURmvfd9gVgt56RXCa8U7nVFpObpG6EyHXtl+kg2JK9QofPHJ5RiXvUvH5/3PqeBwvLSg1IRSiPgnkHv597X66NXgtDMpsOYnfe+DWCpAljtxE2FakA1ABMAhqFohePYH+6NhJw4iEgfgAmojojITKi4WQnpCUuCtWoUhmdthGTdOSfOubwPwXBu+QMha2sCwIiI/FEfpEwHw7UCxR7ARgJh6UT6YNZ7dtY5J0Ht3CXiBgHsCQrHAjPbKyILgyBF8ONNKHQkaEYqIjWzfL6SV/HJRKTPnuyjzrwMSc05TGhOg2kYjHmpwClVHfqjeUB7aQo90Mh0aDcbZNkggE3/Gw1u8LuMda9zAAAAAElFTkSuQmCC" alt="MES EXERCICES" style="height:54px;object-fit:contain;display:block">
  </div>
  <div class="footer-tagline">Les meilleures méthodes du monde · Pour chaque enfant d'Afrique 🇸🇳</div>
  <div class="footer-links">
    <a href="https://wa.me/221771343499">WhatsApp</a>
    <a href="tel:+221771343499">+221 77 134 34 99</a>
    <a href="#commander">Commander</a>
    <a href="#faq">FAQ</a>
    <a href="#methodes">Méthodes</a>
  </div>
  <div class="footer-bottom">© 2025-2026 MES EXERCICES · Tous droits réservés<br>
  🇫🇮 Finlande · 🇸🇬 Singapour · 🇯🇵 Japon · 🍀 Montessori · 🌐 IB PYP · 🇫🇷 France MEN · 🇬🇧 Jolly Phonics</div>
</footer>

<a href="https://wa.me/221771343499" class="wa-float" title="WhatsApp">💬</a>

<script>
var px={"maternelle":1000,"ci":1000,"cp":1000,"ce1":1000,"ce2":1000,"cm1":1000,"cm2":1000,"cem1":1200,"cem2":1500,"pack":6000};
var nm={"maternelle":"Maternelle","ci":"CI","cp":"CP","ce1":"CE1","ce2":"CE2","cm1":"CM1","cm2":"CM2","cem1":"CEM1","cem2":"CEM2 BFEM","pack":"Pack Complet"};
function ch(n,el){document.querySelectorAll('.niv-btn').forEach(b=>b.classList.remove('sel'));el.classList.add('sel');document.getElementById('ni').value=n;document.getElementById('rn').textContent=nm[n];document.getElementById('rp').textContent=px[n].toLocaleString()+' FCFA';document.getElementById('rc').style.display='block';}
function sc(n){document.getElementById('commander').scrollIntoView({behavior:'smooth'});setTimeout(function(){var el=document.getElementById('btn-'+n);if(el)ch(n,el);},600);}
document.querySelectorAll('.faq-item').forEach(item=>{item.querySelector('.faq-q').addEventListener('click',()=>item.classList.toggle('open'));});
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
