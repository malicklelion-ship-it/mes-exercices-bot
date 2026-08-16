import os, logging, random, string, re, threading, time, requests, json
from flask import Flask, request, jsonify, session, redirect, url_for, Response
from functools import wraps

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "mesexercices2025secret"

ADMIN_PASSWORD = "mesexercices2025"
WAVE_BASE      = "https://pay.wave.com/m/M_sn_KPX6hNLZUljQ/c/sn/"
WHATSAPP_NUM   = "221771343499"
SITE_URL       = "https://mes-exercices.com"
GREEN_INSTANCE = "710722708786"
GREEN_TOKEN    = "219438e83e1a4e929a867f34e27565a560c00bb08f6a4a6089"
GREEN_BASE     = f"https://7107.api.greenapi.com/waInstance{GREEN_INSTANCE}"
ORDERS_FILE    = "commandes.json"

PRIX = {"maternelle":1000,"ci":1000,"cp":1000,"ce1":1000,"ce2":1000,
        "cm1":1000,"cm2":1000,"cem1":1200,"cem2":1500,"pack":6000}
NOMS = {"maternelle":"Maternelle","ci":"CI - Cours d'Initiation",
        "cp":"CP - Cours Preparatoire","ce1":"CE1","ce2":"CE2",
        "cm1":"CM1","cm2":"CM2","cem1":"CEM1 (6eme)",
        "cem2":"CEM2 (BFEM)","pack":"Pack Complet (9 niveaux)"}

messages_traites = set()

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
def livrer_commande(c):
    try:
        from whatsapp import envoyer_livraison
        envoyer_livraison(c["telephone"], c["nom"], c["niveau"], c["ref"])
        c["statut"] = "livre"
        sauvegarder()
        log.info(f"✅ LIVRE: {c['ref']} → {c['telephone']}")
        return True
    except Exception as e:
        log.error(f"❌ Erreur livraison {c['ref']}: {e}")
        import traceback; log.error(traceback.format_exc())
        return False

def trouver_et_livrer(ref):
    """Trouve une commande par ref et la livre"""
    for c in commandes:
        if c["ref"] == ref.upper():
            if c["statut"] != "livre":
                return livrer_commande(c)
            else:
                # Deja livre — renvoyer quand meme
                try:
                    from whatsapp import envoyer_livraison
                    envoyer_livraison(c["telephone"],c["nom"],c["niveau"],c["ref"])
                    return True
                except:
                    return False
    return False

# ============================================================
# POLLING WHATSAPP
# ============================================================
def polling_whatsapp():
    log.info("🔄 Polling WhatsApp demarre")
    while True:
        try:
            r = requests.get(
                f"{GREEN_BASE}/receiveNotification/{GREEN_TOKEN}",
                timeout=15
            )
            if r.status_code != 200:
                time.sleep(5); continue

            text = r.text.strip()
            if not text or text in ("null","{}",""):
                time.sleep(3); continue

            try:
                data = r.json()
            except:
                time.sleep(3); continue

            if not data:
                time.sleep(3); continue

            receipt_id = data.get("receiptId")
            body = data.get("body", {})
            type_wh = body.get("typeWebhook","")

            if receipt_id:
                try:
                    requests.delete(
                        f"{GREEN_BASE}/deleteNotification/{GREEN_TOKEN}/{receipt_id}",
                        timeout=5
                    )
                except: pass

            if type_wh != "incomingMessageReceived":
                time.sleep(2); continue

            msg_id = body.get("idMessage","")
            if msg_id and msg_id in messages_traites:
                time.sleep(2); continue
            if msg_id:
                messages_traites.add(msg_id)

            msg_data = body.get("messageData",{})
            texte = msg_data.get("textMessageData",{}).get("textMessage","")

            if not texte:
                time.sleep(2); continue

            log.info(f"📩 Message WhatsApp: '{texte[:60]}'")

            # Chercher references MExxxxxx
            refs = re.findall(r'ME\d{6}', texte.upper())
            for ref in refs:
                log.info(f"🔍 Reference trouvee: {ref}")
                trouver_et_livrer(ref)

        except requests.exceptions.Timeout:
            time.sleep(10)
        except Exception as e:
            log.error(f"Erreur polling: {e}")
            time.sleep(15)

        time.sleep(2)

def demarrer_polling():
    t = threading.Thread(target=polling_whatsapp, daemon=True)
    t.start()
    log.info("✅ Polling demarre")

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

@app.route("/confirmer/<ref>")
def confirmer(ref):
    """
    Page de confirmation directe — le client arrive ici apres paiement
    Le cahier est livre immediatement sans passer par WhatsApp
    """
    ref = ref.upper()
    log.info(f"Confirmation directe recue pour: {ref}")

    for c in commandes:
        if c["ref"] == ref:
            # Livrer immediatement
            ok = trouver_et_livrer(ref)
            if ok:
                html = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Livraison confirmee - MES EXERCICES</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:#F0FFF4;display:flex;align-items:center;justify-content:center;
min-height:100vh;padding:20px}}
.card{{background:#fff;border-radius:16px;padding:36px 28px;max-width:420px;
width:100%;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,.1)}}
.check{{font-size:72px;margin-bottom:16px}}
h1{{color:#1A7A4A;font-size:22px;font-weight:800;margin-bottom:10px}}
p{{color:#555;font-size:14px;line-height:1.6;margin-bottom:8px}}
.ref{{background:#E8F5E9;border-radius:8px;padding:12px;margin:16px 0;
font-size:13px;color:#1A7A4A;font-weight:600}}
.btn{{display:block;background:#25D366;color:#fff;padding:14px;
border-radius:10px;text-decoration:none;font-size:15px;
font-weight:700;margin-top:16px}}
</style></head>
<body><div class="card">
  <div class="check">✅</div>
  <h1>Cahier envoyé sur WhatsApp !</h1>
  <p>Bonjour <strong>{c['nom']}</strong> !</p>
  <div class="ref">
    Commande : <strong>{ref}</strong><br>
    Niveau : {c['nom_niveau']}<br>
    Statut : ✅ Livré
  </div>
  <p>Votre cahier PDF a été envoyé sur WhatsApp au<br>
  <strong>{c['telephone']}</strong></p>
  <p style="margin-top:12px;font-size:12px;color:#888">
  Vous ne voyez pas le message ? Contactez-nous.</p>
  <a href="https://wa.me/{WHATSAPP_NUM}?text=Bonjour+j%27ai+commande+ref+{ref}" 
     class="btn">💬 Contacter le support</a>
</div></body></html>"""
                return html
            else:
                # Erreur livraison — rediriger vers WhatsApp
                return redirect(
                    f"https://wa.me/{WHATSAPP_NUM}?text=Bonjour+j%27ai+paye+ma+commande+ref+{ref}"
                )

    # Reference non trouvee
    html = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reference introuvable</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#FFF3F3;display:flex;
align-items:center;justify-content:center;min-height:100vh;padding:20px}}
.card{{background:#fff;border-radius:16px;padding:32px;max-width:400px;
width:100%;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
h1{{color:#c62828;font-size:18px;margin-bottom:12px}}
p{{color:#555;font-size:14px;margin-bottom:16px;line-height:1.6}}
.btn{{display:block;background:#25D366;color:#fff;padding:14px;
border-radius:10px;text-decoration:none;font-size:15px;font-weight:700}}
</style></head>
<body><div class="card">
  <div style="font-size:60px;margin-bottom:12px">⚠️</div>
  <h1>Reference introuvable</h1>
  <p>La reference <strong>{ref}</strong> n'a pas ete trouvee.<br>
  Contactez-nous sur WhatsApp avec votre reference.</p>
  <a href="https://wa.me/{WHATSAPP_NUM}?text=Bonjour+reference+{ref}" 
     class="btn">💬 Contacter sur WhatsApp</a>
</div></body></html>"""
    return html

@app.route("/")
def index():
    return Response(MAIN_HTML, mimetype="text/html")

@app.route("/commander", methods=["POST"])
def commander():
    niveau    = request.form.get("niveau")
    nom       = request.form.get("nom","").strip()
    telephone = request.form.get("telephone","").strip()
    if not niveau or not nom or not telephone:
        return redirect("/")

    ref  = gen_ref()
    prix = PRIX.get(niveau, 1000)

    commandes.append({
        "ref":ref,"niveau":niveau,"nom_niveau":NOMS.get(niveau,niveau),
        "nom":nom,"telephone":telephone,"prix":prix,"statut":"en_attente"
    })
    sauvegarder()
    log.info(f"📝 Commande: {ref} - {nom} - {niveau} - {prix}F")

    # Lien Wave avec montant pre-rempli et verrouille
    wave_url = f"{WAVE_BASE}?amount={prix}"
    # URL de confirmation directe
    confirm_url = f"{SITE_URL}/confirmer/{ref}"
    # Message WhatsApp pre-rempli
    wa_msg = f"Bonjour+j%27ai+paye+ma+commande+ref+{ref}+montant+{prix}+FCFA"
    wa_url = f"https://wa.me/{WHATSAPP_NUM}?text={wa_msg}"

    html = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paiement - MES EXERCICES</title>
<style>
:root{{--bleu:#1B3A6B;--jaune:#F5C518;--vert:#1A7A4A}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:#F0F4F8;color:#1A1A18}}
nav{{background:var(--bleu);padding:0 20px;height:52px;
display:flex;align-items:center;justify-content:space-between}}
.logo{{color:var(--jaune);font-size:14px;font-weight:800}}
.wrap{{max-width:460px;margin:24px auto;padding:0 14px}}
.card{{background:#fff;border-radius:14px;padding:24px;
box-shadow:0 2px 12px rgba(0,0,0,.08);margin-bottom:12px}}

/* Reference */
.ref-box{{background:#EFF6FF;border:2px solid var(--bleu);
border-radius:10px;padding:16px;text-align:center;margin-bottom:16px}}
.ref-box .label{{font-size:12px;color:#666;margin-bottom:4px}}
.ref-box .code{{font-size:34px;color:var(--bleu);letter-spacing:5px;
font-weight:900;display:block}}

/* Montant */
.montant-box{{background:#FFFBEA;border:2px solid var(--jaune);
border-radius:10px;padding:14px;text-align:center;margin-bottom:20px}}
.montant-box .niveau-nom{{font-size:13px;color:#888;margin-bottom:4px}}
.montant-box .montant{{font-size:30px;color:#B8860B;font-weight:900}}

/* Etapes */
.etape{{margin-bottom:20px}}
.etape-titre{{font-size:14px;font-weight:700;color:#1A1A18;
margin-bottom:10px;display:flex;align-items:center;gap:8px}}
.etape-num{{width:26px;height:26px;border-radius:50%;
background:var(--bleu);color:#fff;font-size:12px;font-weight:800;
display:inline-flex;align-items:center;justify-content:center;flex-shrink:0}}

/* Boutons */
.btn-wave{{display:flex;align-items:center;justify-content:center;
gap:10px;background:#1565C0;color:#fff;padding:16px;border-radius:10px;
text-decoration:none;font-size:15px;font-weight:700;margin-bottom:8px;
transition:opacity .2s}}
.btn-wave:hover{{opacity:.9}}
.btn-om{{display:flex;align-items:center;justify-content:center;
gap:10px;background:#E65100;color:#fff;padding:16px;border-radius:10px;
border:none;cursor:pointer;font-size:15px;font-weight:700;width:100%;
margin-bottom:8px}}
.om-box{{background:#FFF3E0;border-radius:10px;padding:14px;
font-size:13px;line-height:1.9;display:none;margin-bottom:8px}}
.om-box code{{background:#FFE0B2;padding:3px 9px;border-radius:5px;
font-weight:700;display:inline-block;font-size:14px}}

/* Confirmation directe */
.confirm-box{{background:#E8F5E9;border:2px solid #4CAF50;
border-radius:12px;padding:16px;margin-bottom:8px}}
.confirm-box p{{font-size:13px;color:#1B5E20;margin-bottom:10px;line-height:1.6}}
.btn-confirm{{display:flex;align-items:center;justify-content:center;
gap:10px;background:#1A7A4A;color:#fff;padding:16px;border-radius:10px;
text-decoration:none;font-size:15px;font-weight:800}}
.btn-confirm:hover{{background:#145c38}}

/* Séparateur */
.ou{{text-align:center;color:#aaa;font-size:12px;margin:8px 0;
display:flex;align-items:center;gap:8px}}
.ou::before,.ou::after{{content:'';flex:1;height:1px;background:#e0e0e0}}

/* WhatsApp backup */
.btn-wa{{display:flex;align-items:center;justify-content:center;
gap:10px;background:#25D366;color:#fff;padding:14px;border-radius:10px;
text-decoration:none;font-size:14px;font-weight:700}}
.note{{font-size:11px;color:#aaa;text-align:center;margin-top:8px;line-height:1.6}}

/* Badge securite */
.secure{{background:#F3F4F6;border-radius:8px;padding:10px;
text-align:center;font-size:11px;color:#666;margin-top:8px}}
</style></head>
<body>
<nav>
  <div class="logo">📚 MES EXERCICES</div>
  <a href="/" style="color:rgba(255,255,255,.6);font-size:12px;text-decoration:none">← Retour</a>
</nav>
<div class="wrap">
<div class="card">

  <div class="ref-box">
    <div class="label">Votre reference de commande</div>
    <span class="code">{ref}</span>
  </div>

  <div class="montant-box">
    <div class="niveau-nom">{NOMS.get(niveau,niveau)}</div>
    <div class="montant">{prix:,} FCFA</div>
  </div>

  <!-- ETAPE 1 : PAIEMENT -->
  <div class="etape">
    <div class="etape-titre">
      <span class="etape-num">1</span>
      Payez maintenant
    </div>

    <!-- Wave avec montant pre-rempli -->
    <a href="{wave_url}" class="btn-wave" target="_blank"
       onclick="sessionStorage.setItem('paid','yes')">
      💙 Payer {prix:,} FCFA avec Wave
    </a>

    <!-- Orange Money -->
    <button class="btn-om"
      onclick="var o=document.getElementById('om');
               o.style.display=o.style.display=='block'?'none':'block'">
      🟠 Payer avec Orange Money
    </button>
    <div class="om-box" id="om">
      <strong>Composez sur votre telephone :</strong><br>
      <code>*144*2*{WHATSAPP_NUM}*{prix}#</code><br><br>
      <strong>Ou dans l'app Orange Money :</strong><br>
      Transfert → <code>77 134 34 99</code> → <code>{prix} FCFA</code><br>
      Validez avec votre code PIN
    </div>
  </div>

  <!-- ETAPE 2 : CONFIRMATION -->
  <div class="etape">
    <div class="etape-titre">
      <span class="etape-num">2</span>
      Confirmez et recevez votre cahier
    </div>

    <!-- OPTION A : Confirmation directe (recommandee) -->
    <div class="confirm-box">
      <p>⚡ <strong>Option recommandee</strong> — Cliquez apres avoir paye :<br>
      Votre cahier est envoye <strong>instantanement</strong> sur WhatsApp !</p>
      <a href="{confirm_url}" class="btn-confirm">
        ✅ J'ai paye — Envoyer mon cahier maintenant !
      </a>
    </div>

    <div class="ou">ou</div>

    <!-- OPTION B : Via WhatsApp -->
    <a href="{wa_url}" class="btn-wa" target="_blank">
      💬 Confirmer via WhatsApp
    </a>
    <p class="note">
      Message pre-rempli avec votre reference <strong>{ref}</strong><br>
      Livraison automatique en moins de 2 minutes
    </p>
  </div>

  <div class="secure">
    🔒 Paiement securise · Vos donnees sont protegees<br>
    Support : +221 77 134 34 99
  </div>

</div>
</div>

<script>
// Si le client revient apres paiement Wave, proposer la confirmation
window.addEventListener('focus', function() {{
  if (sessionStorage.getItem('paid') === 'yes') {{
    document.querySelector('.confirm-box').style.border = '3px solid #1A7A4A';
    document.querySelector('.btn-confirm').style.animation = 'pulse 1s infinite';
  }}
}});
</script>
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
button{{width:100%;background:#1B3A6B;color:#fff;border:none;padding:12px;
border-radius:6px;font-size:15px;cursor:pointer}}
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
        st="✅ Livre" if c["statut"]=="livre" else "⏳ En attente"
        rows+=f"""<tr>
<td><strong>{c['ref']}</strong></td>
<td>{c['nom']}</td>
<td>{c['telephone']}</td>
<td>{c['nom_niveau']}</td>
<td>{c['prix']:,} F</td>
<td><span style="background:{sc};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{st}</span></td>
<td>
<a href="/livrer/{c['ref']}" style="background:#1B3A6B;color:#fff;padding:4px 9px;border-radius:4px;font-size:11px;text-decoration:none;margin-right:3px">📤 Livrer</a>
<a href="/admin/renvoyer/{c['ref']}" style="background:#1A7A4A;color:#fff;padding:4px 9px;border-radius:4px;font-size:11px;text-decoration:none">🔄 Renvoyer</a>
</td></tr>"""
    total=len(commandes)
    livres=sum(1 for c in commandes if c["statut"]=="livre")
    ca=sum(c["prix"] for c in commandes if c["statut"]=="livre")
    return Response(f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="15">
<title>Dashboard - MES EXERCICES</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#f0f4f8}}
header{{background:#1B3A6B;color:#fff;padding:14px 18px;
display:flex;justify-content:space-between;align-items:center}}
header h1{{font-size:15px}}
.out{{color:#F5C518;text-decoration:none;font-size:12px}}
.banner{{background:#E8F5E9;padding:8px 18px;font-size:12px;
color:#1B5E20;text-align:center;font-weight:600;border-bottom:1px solid #A5D6A7}}
.stats{{display:flex;gap:10px;padding:14px;flex-wrap:wrap}}
.stat{{background:#fff;border-radius:8px;padding:12px 16px;flex:1;
min-width:100px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.stat .n{{font-size:24px;font-weight:800;color:#1B3A6B}}
.stat .l{{font-size:10px;color:#888;margin-top:2px}}
.cont{{padding:0 14px 14px}}
.new-btn{{display:inline-block;background:#F5C518;color:#1B3A6B;
padding:8px 16px;border-radius:6px;text-decoration:none;
font-weight:700;margin-bottom:12px;font-size:13px}}
table{{width:100%;border-collapse:collapse;background:#fff;
border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);
font-size:12px}}
th{{background:#1B3A6B;color:#fff;padding:10px;text-align:left}}
td{{padding:10px;border-bottom:1px solid #f0f0f0}}
tr:last-child td{{border-bottom:none}}
.empty{{text-align:center;padding:36px;color:#999;
background:#fff;border-radius:8px}}</style></head>
<body>
<header>
  <h1>📚 MES EXERCICES — Dashboard</h1>
  <a href="/admin/logout" class="out">Déconnexion</a>
</header>
<div class="banner">
  ⚡ Livraison auto active — {total} commandes en mémoire
</div>
<div class="stats">
  <div class="stat"><div class="n">{total-livres}</div><div class="l">En attente</div></div>
  <div class="stat"><div class="n">{livres}</div><div class="l">Livrées</div></div>
  <div class="stat"><div class="n">{total}</div><div class="l">Total</div></div>
  <div class="stat"><div class="n">{ca:,} F</div><div class="l">CA total</div></div>
</div>
<div class="cont">
  <a href="/admin/nouvelle" class="new-btn">+ Commande manuelle</a>
  {"<table><thead><tr><th>Réf</th><th>Nom</th><th>Tél</th><th>Niveau</th><th>Prix</th><th>Statut</th><th>Actions</th></tr></thead><tbody>"+rows+"</tbody></table>" if commandes else '<div class="empty">Aucune commande pour le moment</div>'}
</div></body></html>""",mimetype="text/html")

@app.route("/livrer/<ref>")
@login_required
def livrer(ref):
    ok = trouver_et_livrer(ref)
    return redirect(url_for("admin"))

@app.route("/admin/renvoyer/<ref>")
@login_required
def renvoyer(ref):
    trouver_et_livrer(ref)
    return redirect(url_for("admin"))

@app.route("/admin/nouvelle", methods=["GET","POST"])
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
        sauvegarder()
        return redirect(url_for("admin"))
    opts="".join([f'<option value="{k}">{v} — {PRIX[k]:,} F</option>' for k,v in NOMS.items()])
    return Response(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Nouvelle commande</title>
<style>body{{font-family:Arial,sans-serif;background:#f0f4f8;display:flex;
justify-content:center;padding:28px 14px}}
.c{{background:#fff;border-radius:10px;padding:22px;max-width:380px;
width:100%;box-shadow:0 2px 8px rgba(0,0,0,.1)}}
h2{{color:#1B3A6B;margin-bottom:16px}}
label{{display:block;margin-bottom:4px;font-weight:700;font-size:13px}}
select,input{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;
font-size:14px;margin-bottom:12px}}
button{{width:100%;background:#1B3A6B;color:#fff;border:none;padding:12px;
border-radius:6px;font-size:14px;cursor:pointer}}
a{{display:block;text-align:center;margin-top:10px;color:#666;
font-size:13px;text-decoration:none}}</style></head>
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

MAIN_HTML = """<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MES EXERCICES — Cahiers scolaires numeriques</title>
<style>
:root{--bleu:#1B3A6B;--jaune:#F5C518;--vert:#1A7A4A}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#FAFAF8;color:#1A1A18}
nav{background:var(--bleu);padding:0 20px;display:flex;align-items:center;justify-content:space-between;height:54px;position:sticky;top:0;z-index:100}
.nav-logo{color:var(--jaune);font-size:14px;font-weight:800}
.nav-cta{background:var(--jaune);color:var(--bleu);padding:7px 14px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:700}
.hero{background:var(--bleu);padding:54px 20px 62px;text-align:center}
.hero h1{color:#fff;font-size:clamp(24px,5vw,44px);font-weight:800;line-height:1.15;margin-bottom:12px}
.hero h1 em{color:var(--jaune);font-style:normal}
.hero p{color:rgba(255,255,255,.8);font-size:14px;max-width:460px;margin:0 auto 24px;line-height:1.6}
.flags{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin-bottom:24px}
.flag{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);color:#fff;font-size:11px;font-weight:600;padding:4px 11px;border-radius:14px}
.btn-hero{background:var(--jaune);color:var(--bleu);font-weight:800;font-size:15px;padding:13px 24px;border-radius:10px;text-decoration:none;display:inline-block}
.proof{background:#FFFBEA;border-top:1px solid #F5C518;border-bottom:1px solid #F5C518;padding:10px 20px}
.proof-inner{max-width:900px;margin:0 auto;display:flex;gap:18px;justify-content:center;flex-wrap:wrap}
.pi{font-size:12px;font-weight:600;color:var(--bleu)}
.section{max-width:1000px;margin:0 auto;padding:44px 18px}
.section h2{font-size:clamp(20px,3vw,30px);font-weight:800;color:var(--bleu);margin-bottom:22px;text-align:center}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:12px}
.card{background:#fff;border:1.5px solid #E8E8E6;border-radius:12px;padding:16px;cursor:pointer;transition:all .15s}
.card:hover{border-color:var(--bleu);transform:translateY(-2px);box-shadow:0 6px 18px rgba(27,58,107,.1)}
.card.pack{border-color:var(--jaune);grid-column:1/-1;background:#FFFBEA}
.niv{font-size:10px;font-weight:700;background:#EFF6FF;color:var(--bleu);padding:2px 8px;border-radius:10px;display:inline-block;margin-bottom:7px}
.card h3{font-size:13px;font-weight:700;margin-bottom:3px}
.card p{font-size:11px;color:#666;margin-bottom:9px;line-height:1.4}
.price{font-size:19px;font-weight:800;color:var(--bleu);margin-bottom:9px}
.pack .price{color:#B8860B}
.btn-card{width:100%;padding:9px;border-radius:8px;border:none;cursor:pointer;font-size:12px;font-weight:700;background:var(--bleu);color:#fff}
.pack .btn-card{background:var(--jaune);color:var(--bleu)}
.cs{background:var(--bleu);padding:52px 18px}
.ci{max-width:840px;margin:0 auto}
.ct{color:#fff;font-size:clamp(20px,3vw,32px);font-weight:800;text-align:center;margin-bottom:5px}
.cst{color:rgba(255,255,255,.7);text-align:center;font-size:13px;margin-bottom:28px}
.fg{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:580px){.fg{grid-template-columns:1fr}}
.fc{background:#fff;border-radius:12px;padding:20px}
.fc h3{font-size:14px;font-weight:700;color:var(--bleu);margin-bottom:14px}
.ng{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:12px}
.nb{border:2px solid #E0E0E0;border-radius:8px;padding:8px 5px;cursor:pointer;text-align:center;background:#fff;transition:all .15s}
.nb:hover,.nb.sel{border-color:var(--bleu);background:#EFF6FF}
.nb .nn{font-weight:700;font-size:11px}
.nb .np{color:var(--bleu);font-size:10px;margin-top:1px}
.pb{grid-column:1/-1;border-color:var(--jaune);background:#FFFBEA}
.pb.sel{border-color:#B8860B}
.rc{background:#EFF6FF;border-radius:7px;padding:9px;margin-bottom:10px;display:none;font-size:12px}
.rc strong{color:var(--bleu);font-size:16px}
label{display:block;margin-bottom:3px;font-weight:600;font-size:12px}
input{width:100%;padding:9px;border:1.5px solid #E0E0E0;border-radius:7px;font-size:13px;margin-bottom:10px}
input:focus{outline:none;border-color:var(--bleu)}
.bcmd{width:100%;background:var(--jaune);color:var(--bleu);border:none;padding:13px;border-radius:9px;font-size:14px;font-weight:800;cursor:pointer}
.ic{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.2);border-radius:12px;padding:20px;color:#fff}
.ic h3{font-size:14px;font-weight:700;color:var(--jaune);margin-bottom:14px}
.step{display:flex;gap:9px;align-items:flex-start;margin-bottom:12px}
.sn{width:26px;height:26px;border-radius:50%;background:var(--jaune);color:var(--bleu);font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.st strong{display:block;font-size:12px;font-weight:700;margin-bottom:1px}
.st span{font-size:11px;color:rgba(255,255,255,.7)}
.ab{background:#E8F5E9;border:1px solid #66BB6A;border-radius:7px;padding:9px 12px;font-size:12px;color:#1B5E20;text-align:center;margin:12px 0;font-weight:600}
footer{background:#1A1A18;color:rgba(255,255,255,.5);padding:26px 18px;text-align:center;font-size:12px}
.fl{color:var(--jaune);font-size:14px;font-weight:800;margin-bottom:7px}
.wa-f{position:fixed;bottom:20px;right:20px;background:#25D366;color:#fff;width:50px;height:50px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:22px;text-decoration:none;box-shadow:0 4px 12px rgba(0,0,0,.3);z-index:999}
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
    <span class="pi">⚡ Livraison instantanée WhatsApp</span>
    <span class="pi">📄 100 pages par cahier</span>
    <span class="pi">✅ 500+ exercices</span>
    <span class="pi">💰 Dès 1 000 FCFA</span>
    <span class="pi">🇸🇳 Programme sénégalais</span>
  </div>
</div>
<div class="section" id="cahiers">
  <h2>9 cahiers · Un pour chaque niveau</h2>
  <div class="grid">
    <div class="card" onclick="sc('maternelle')"><div class="niv">Maternelle · 4-6 ans</div><h3>📚 Maternelle</h3><p>Lettres, chiffres. Montessori + Jolly Phonics.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('ci')"><div class="niv">CI · 6-7 ans</div><h3>📚 CI</h3><p>Lecture syllabique, additions.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('cp')"><div class="niv">CP · 6-7 ans</div><h3>📚 CP</h3><p>Lecture complète, soustraction.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('ce1')"><div class="niv">CE1 · 7-8 ans</div><h3>📚 CE1</h3><p>Multiplication. Singapour Math.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('ce2')"><div class="niv">CE2 · 8-9 ans</div><h3>📚 CE2</h3><p>Division, compréhension.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('cm1')"><div class="niv">CM1 · 9-10 ans</div><h3>📚 CM1</h3><p>Géométrie, fractions.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('cm2')"><div class="niv">CM2 · CFEE</div><h3>📚 CM2</h3><p>Préparation CFEE.</p><div class="price">1 000 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('cem1')"><div class="niv">CEM1 · 6ème</div><h3>📚 CEM1</h3><p>Algèbre, littérature.</p><div class="price">1 200 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card" onclick="sc('cem2')"><div class="niv">CEM2 · BFEM ⭐</div><h3>📚 CEM2</h3><p>Préparation BFEM.</p><div class="price">1 500 FCFA</div><button class="btn-card">Commander →</button></div>
    <div class="card pack" onclick="sc('pack')"><div class="niv" style="background:#FFF3CD;color:#B8860B">🔥 MEILLEUR CHOIX -44%</div><h3>📚 Pack Complet — 9 niveaux</h3><p>Tous les cahiers. Économisez 4 700 FCFA !</p><div class="price">6 000 FCFA <span style="font-size:12px;color:#999;text-decoration:line-through">10 700 FCFA</span></div><button class="btn-card">Commander le Pack →</button></div>
  </div>
</div>
<section class="cs" id="commander">
  <div class="ci">
    <div class="ct">📚 Commander votre cahier</div>
    <div class="cst">Payez Wave ou Orange Money · Reçu sur WhatsApp en 2 minutes !</div>
    <div class="fg">
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
          <div class="rc" id="rc">Niveau : <span id="rn"></span><br>Montant : <strong id="rp"></strong></div>
          <label>Prénom et nom</label>
          <input type="text" name="nom" placeholder="Fatou Diallo" required>
          <label>Numéro WhatsApp</label>
          <input type="tel" name="telephone" placeholder="221771234567" required>
          <button type="submit" class="bcmd">✅ Commander →</button>
        </form>
      </div>
      <div class="ic">
        <h3>⚡ Comment ça marche ?</h3>
        <div class="step"><div class="sn">1</div><div class="st"><strong>Choisissez et commandez</strong><span>Sélectionnez niveau, remplissez le formulaire</span></div></div>
        <div class="step"><div class="sn">2</div><div class="st"><strong>Payez le montant exact</strong><span>Wave avec montant pré-rempli ou Orange Money *144#</span></div></div>
        <div class="step"><div class="sn">3</div><div class="st"><strong>Cliquez "J'ai payé"</strong><span>Un bouton vert vous envoie le cahier instantanément</span></div></div>
        <div class="step"><div class="sn">4</div><div class="st"><strong>Recevez en 2 minutes !</strong><span>PDF livré automatiquement sur WhatsApp</span></div></div>
        <div class="ab">⚡ 100% automatique — livraison instantanée</div>
        <div style="font-size:12px;color:rgba(255,255,255,.8);margin-top:10px">
          💙 Wave (montant auto) · 🟠 Orange Money<br>
          📞 <strong style="color:#fff">+221 77 134 34 99</strong>
        </div>
      </div>
    </div>
  </div>
</section>
<footer>
  <div class="fl">📚 MES EXERCICES</div>
  <div>Les meilleures méthodes du monde · Pour chaque enfant du Sénégal 🇸🇳</div>
  <div style="margin-top:8px">
    <a href="https://wa.me/221771343499" style="color:var(--jaune)">WhatsApp</a> ·
    <a href="tel:+221771343499" style="color:var(--jaune)">+221 77 134 34 99</a>
  </div>
</footer>
<a href="https://wa.me/221771343499" class="wa-f">💬</a>
<script>
var px={"maternelle":1000,"ci":1000,"cp":1000,"ce1":1000,"ce2":1000,"cm1":1000,"cm2":1000,"cem1":1200,"cem2":1500,"pack":6000};
var nm={"maternelle":"Maternelle","ci":"CI","cp":"CP","ce1":"CE1","ce2":"CE2","cm1":"CM1","cm2":"CM2","cem1":"CEM1","cem2":"CEM2 BFEM","pack":"Pack Complet"};
function ch(n,el){document.querySelectorAll('.nb').forEach(b=>b.classList.remove('sel'));el.classList.add('sel');document.getElementById('ni').value=n;document.getElementById('rn').textContent=nm[n];document.getElementById('rp').textContent=px[n].toLocaleString()+' FCFA';document.getElementById('rc').style.display='block';}
function sc(n){document.getElementById('commander').scrollIntoView({behavior:'smooth'});setTimeout(function(){var el=document.getElementById('btn-'+n);if(el)ch(n,el);},600);}
</script>
</body></html>"""

# Demarrer le polling WhatsApp
demarrer_polling()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
