import sys
import io
# Configuration de l'encodage UTF-8 pour Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from fastapi import FastAPI, HTTPException, Form, Request, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from dotenv import load_dotenv
import os
import json
from pathlib import Path
from typing import Optional
import time
from backend.nowpayments import NowPaymentsAPI, SUPPORTED_CRYPTOS, format_crypto_amount

try:
    # Make .env loading non-fatal if file has invalid encoding/contents
    load_dotenv(override=False)
except Exception as e:
    print(f"⚠️  .env non chargé (ignoré): {e}")

app = FastAPI()

# --- Database file path ---
DB_FILE = Path("db/sales_db.json")

# --- NowPayments Configuration ---
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY", "MZ1RXTT-QPH4H3M-NJ7KM67-YEG5MEP")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET", "")  # À configurer dans .env
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # URL publique pour les webhooks

# Initialiser l'API NowPayments
nowpayments = NowPaymentsAPI(NOWPAYMENTS_API_KEY, NOWPAYMENTS_IPN_SECRET)

# --- Event: Charger les utilisateurs au démarrage ---
@app.on_event("startup")
async def load_users_on_startup():
    """Charge tous les utilisateurs depuis la DB au démarrage"""
    global USERS
    db = load_db()
    users_db = db.get("users", {})
    for user_id_str, user_data in users_db.items():
        USERS[int(user_id_str)] = user_data
    print(f"✅ {len(USERS)} utilisateurs chargés depuis la DB")

# --- Load/Save database functions ---
def load_db():
    """Charge la base de données depuis le fichier JSON"""
    if DB_FILE.exists():
        try:
            with open(DB_FILE, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur chargement DB: {e}")
    return {"sales": [], "leads": [], "sold_lines": {}, "users": {}}

def save_db(db_data):
    """Sauvegarde la base de données dans le fichier JSON"""
    try:
        DB_FILE.parent.mkdir(exist_ok=True)
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(db_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur sauvegarde DB: {e}")

# --- In-memory demo store (replace with real DB in production) ---
PRODUCTS = [
    {
        "filename": "Num List",
        "available": 6147195,
        "price": 4,
        "description": "Liste de numéros de téléphone (format standard)."
    },
    {
        "filename": "Num list personnes âgées (1900-1957)",
        "available": 854749,
        "price": 10,
        "description": "Numéros pour personnes âgées nées entre 1900 et 1957."
    },
    {
        "filename": "Num list banque",
        "available": 6148984,
        "price": 15,
        "description": "Numéros liés au secteur bancaire."
    },
    {
        "filename": "Mail List",
        "available": 5904180,
        "price": 4,
        "description": "Liste d'adresses e-mail (format standard)."
    },
    {
        "filename": "Fiches banque clients",
        "available": 6147196,
        "price": 0.5,
        "description": "Fiches triées par banque avec BIC et IBAN."
    },
    {
        "filename": "Fiches clients",
        "available": 6147196,
        "price": 0.5,
        "description": "Fiches clients, 0,50 € par fiche."
    },
]
USERS: dict[int, dict] = {}
SALES = []

def save_user(user_id: int):
    """Sauvegarde un utilisateur dans la DB"""
    db = load_db()
    if "users" not in db:
        db["users"] = {}
    db["users"][str(user_id)] = USERS[user_id]
    save_db(db)

def get_or_create_user(user_id: int) -> dict:
    # Charger depuis la DB si pas en mémoire
    if user_id not in USERS:
        db = load_db()
        users_db = db.get("users", {})
        if str(user_id) in users_db:
            USERS[user_id] = users_db[str(user_id)]
        else:
            USERS[user_id] = {
                "user_id": user_id,
                "username": None,
                "grade": "Membre",
                "balance": 0.0,
                "total_purchases": 0,
                "total_deposits": 0.0,
            }
            save_user(user_id)
    return USERS[user_id]

@app.get("/")
def home():
    return {"message": "✅ API du bot opérationnelle !"}

@app.get("/user/{user_id}")
def get_user(user_id: int):
    return get_or_create_user(user_id)

@app.get("/user/{user_id}/purchases")
def get_user_purchases(user_id: int):
    """Récupère l'historique des achats d'un utilisateur"""
    db = load_db()
    sales = db.get("sales", [])
    user_purchases = [sale for sale in sales if sale.get("user_id") == user_id]
    return {"purchases": user_purchases}

@app.get("/products")
def get_products():
    return {"products": PRODUCTS}

@app.post("/deposit")
def deposit(payload: dict):
    user_id = int(payload.get("user_id", 0))
    amount = float(payload.get("amount", 0))
    if user_id <= 0 or amount < 10:
        raise HTTPException(status_code=400, detail="Paramètres invalides")
    user = get_or_create_user(user_id)
    user["balance"] += amount
    user["total_deposits"] += amount
    save_user(user_id)  # Sauvegarder l'utilisateur
    return {"status": "ok", "balance": user["balance"]}

@app.post("/register_sale")
def register_sale(item: dict):
    print("Nouvelle vente enregistree :", item)
    return {"status": "success", "item": item}

# Mapping produits -> fichiers
PRODUCT_FILE_MAP = {
    "Num List": "fichiers/num_list.txt",
    "Num list personnes âgées (1900-1957)": "fichiers/num_list_personnes_agees.txt",
    "Num list banque": "fichiers/num_list_banque.txt",
    "Mail List": "fichiers/mail_list.txt",
    "Fiches banque clients": "fichiers/fiches_banque_clients.txt",
    "Fiches clients": "fichiers/fiches_clients.txt",
    "List par K": "fichiers/list_par_K.txt",
}

@app.get("/next_line/{filename}")
def next_line(filename: str):
    file_path = PRODUCT_FILE_MAP.get(filename)
    if not file_path or not os.path.exists(file_path):
        return {"index": 0, "line": f"Fichier non trouvé pour {filename}"}

    try:
        # Charger la DB pour voir quelles lignes ont été vendues
        db = load_db()
        sold_lines = db.get("sold_lines", {})
        sold_indices = sold_lines.get(filename, [])

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip() and not line.strip().startswith('#')]
            if not lines:
                return {"index": 0, "line": f"Fichier vide pour {filename}"}

            # Trouver la première ligne non vendue
            for idx, line in enumerate(lines):
                if idx not in sold_indices:
                    # Marquer cette ligne comme vendue
                    sold_indices.append(idx)
                    sold_lines[filename] = sold_indices
                    db["sold_lines"] = sold_lines
                    save_db(db)
                    return {"index": idx, "line": line}

            # Toutes les lignes ont été vendues
            return {"index": -1, "line": f"Stock épuisé pour {filename}"}
    except Exception as e:
        print(f"Erreur lecture fichier {file_path}: {e}")
        return {"index": 0, "line": f"Erreur lecture fichier: {e}"}

@app.post("/purchase")
def purchase(payload: dict):
    user_id = int(payload.get("user_id", 0))
    product_name = payload.get("product")
    if user_id <= 0 or not product_name:
        raise HTTPException(status_code=400, detail="Paramètres invalides")

    user = get_or_create_user(user_id)
    product = next((p for p in PRODUCTS if p["filename"] == product_name), None)
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if product["available"] <= 0:
        raise HTTPException(status_code=400, detail="Produit épuisé")
    price = float(product.get("price", 0))
    if user["balance"] < price:
        raise HTTPException(status_code=400, detail="Solde insuffisant")

    # Deduct and deliver
    user["balance"] -= price
    user["total_purchases"] += 1
    product["available"] -= 1
    line_resp = next_line(product_name)

    # Sauvegarder l'utilisateur
    save_user(user_id)

    # Sauvegarder la vente dans la DB
    sale = {
        "user_id": user_id,
        "product": product_name,
        "price": price,
        "line": line_resp["line"],
        "timestamp": str(os.path.getmtime(DB_FILE) if DB_FILE.exists() else 0)
    }
    SALES.append(sale)

    # Enregistrer dans la DB JSON
    db = load_db()
    db["sales"].append(sale)
    save_db(db)

    return {"status": "ok", "balance": user["balance"], "line": line_resp["line"], "price": price}

# --------------------
# Simple Admin Dashboard
# --------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_home():
    # Calculer les statistiques
    total_users = len(USERS)
    total_balance = sum(u['balance'] for u in USERS.values())
    total_purchases = sum(u['total_purchases'] for u in USERS.values())
    total_deposits = sum(u['total_deposits'] for u in USERS.values())
    total_revenue = total_deposits - total_balance
    total_stock = sum(p['available'] for p in PRODUCTS)

    users_html_rows = "".join([
        f"""<tr>
            <td><strong>{u['user_id']}</strong></td>
            <td>{u.get('username') or '<em>-</em>'}</td>
            <td><span class="balance">{u['balance']:.2f} €</span></td>
            <td><span class="badge">{u['total_purchases']}</span></td>
            <td><span class="deposit">{u['total_deposits']:.2f} €</span></td>
        </tr>"""
        for u in sorted(USERS.values(), key=lambda x: x['total_deposits'], reverse=True)
    ])

    products_html_rows = "".join([
        f"""<tr>
            <td><strong>{p['filename']}</strong></td>
            <td><span class="price">{p['price']} €</span></td>
            <td><span class="stock {'low' if p['available'] < 100 else ''}">{p['available']:,}</span></td>
        </tr>"""
        for p in PRODUCTS
    ])

    html = f"""<!DOCTYPE html>
    <html lang="fr">
      <head>
        <meta charset='utf-8'/>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard Admin - ListMarket Bot</title>
        <style>
          * {{ margin: 0; padding: 0; box-sizing: border-box; }}

          body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
          }}

          .container {{
            max-width: 1400px;
            margin: 0 auto;
          }}

          .header {{
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
          }}

          h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
          }}

          .subtitle {{
            color: #666;
            font-size: 1.1em;
          }}

          .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
          }}

          .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
          }}

          .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
          }}

          .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
          }}

          .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
          }}

          .section {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
          }}

          h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
          }}

          .credit-form {{
            background: #f8f9ff;
            padding: 25px;
            border-radius: 10px;
            border: 2px solid #667eea;
            margin-bottom: 20px;
          }}

          .form-group {{
            display: inline-block;
            margin-right: 15px;
            margin-bottom: 10px;
          }}

          label {{
            display: block;
            color: #333;
            font-weight: 600;
            margin-bottom: 5px;
            font-size: 0.9em;
          }}

          input[type=number] {{
            padding: 12px 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
            width: 200px;
            transition: border-color 0.3s ease;
          }}

          input[type=number]:focus {{
            outline: none;
            border-color: #667eea;
          }}

          button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
          }}

          button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
          }}

          table {{
            width: 100%;
            border-collapse: collapse;
          }}

          th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 1px;
          }}

          td {{
            padding: 15px;
            border-bottom: 1px solid #eee;
          }}

          tr:hover {{
            background: #f8f9ff;
          }}

          .balance {{
            color: #10b981;
            font-weight: 600;
            font-size: 1.1em;
          }}

          .deposit {{
            color: #667eea;
            font-weight: 600;
          }}

          .price {{
            color: #f59e0b;
            font-weight: 600;
          }}

          .stock {{
            padding: 5px 12px;
            background: #10b981;
            color: white;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
          }}

          .stock.low {{
            background: #ef4444;
          }}

          .badge {{
            background: #667eea;
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.9em;
            font-weight: 600;
          }}

          .note {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            border-radius: 8px;
            color: #92400e;
            margin-bottom: 20px;
          }}

          @media (max-width: 768px) {{
            .stats-grid {{
              grid-template-columns: 1fr;
            }}

            h1 {{
              font-size: 1.8em;
            }}

            input[type=number] {{
              width: 100%;
            }}

            .form-group {{
              display: block;
              margin-right: 0;
            }}
          }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>Dashboard Admin</h1>
            <p class="subtitle">ListMarket Bot - Gestion complète</p>
          </div>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">Utilisateurs</div>
              <div class="stat-value">{total_users}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Solde Total</div>
              <div class="stat-value">{total_balance:.2f} €</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Achats Total</div>
              <div class="stat-value">{total_purchases}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Dépôts Total</div>
              <div class="stat-value">{total_deposits:.2f} €</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Revenus</div>
              <div class="stat-value">{total_revenue:.2f} €</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Stock Total</div>
              <div class="stat-value">{total_stock:,}</div>
            </div>
          </div>

          <div class="section">
            <h2>Créditer un utilisateur</h2>
            <div class="note">
              <strong>Note:</strong> Crédit minimum pour un dépôt: 10.00 €
            </div>
            <form method="post" action="/admin/credit" class="credit-form">
              <div class="form-group">
                <label>ID Utilisateur Telegram</label>
                <input name="user_id" type="number" required placeholder="Ex: 123456789"/>
              </div>
              <div class="form-group">
                <label>Montant à créditer (€)</label>
                <input name="amount" type="number" step="0.01" min="0" required placeholder="Ex: 50.00"/>
              </div>
              <div class="form-group">
                <label>&nbsp;</label>
                <button type="submit">Créditer le compte</button>
              </div>
            </form>
          </div>

          <div class="section">
            <h2>Utilisateurs ({total_users})</h2>
            <table>
              <thead>
                <tr>
                  <th>ID Telegram</th>
                  <th>Username</th>
                  <th>Solde</th>
                  <th>Achats</th>
                  <th>Dépôts</th>
                </tr>
              </thead>
              <tbody>
                {users_html_rows or '<tr><td colspan=5 style="text-align:center; padding:30px; color:#999;">Aucun utilisateur pour le moment</td></tr>'}
              </tbody>
            </table>
          </div>

          <div class="section">
            <h2>Produits ({len(PRODUCTS)})</h2>
            <table>
              <thead>
                <tr>
                  <th>Nom du produit</th>
                  <th>Prix unitaire</th>
                  <th>Stock disponible</th>
                </tr>
              </thead>
              <tbody>
                {products_html_rows}
              </tbody>
            </table>
          </div>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/admin/credit")
def admin_credit(user_id: int = Form(...), amount: float = Form(...)):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Montant invalide")
    user = get_or_create_user(int(user_id))
    user["balance"] += float(amount)
    user["total_deposits"] += float(amount)
    save_user(int(user_id))  # Sauvegarder l'utilisateur
    return RedirectResponse(url="/admin", status_code=303)


# =============================================================================
# ENDPOINTS CRYPTO PAYMENT (NowPayments)
# =============================================================================

@app.get("/crypto/currencies")
def get_crypto_currencies():
    """Récupérer la liste des cryptos supportées"""
    return {
        "currencies": SUPPORTED_CRYPTOS,
        "available": list(SUPPORTED_CRYPTOS.keys())
    }


@app.post("/crypto/create-payment")
def create_crypto_payment(payload: dict):
    """Créer un paiement crypto"""
    try:
        user_id = int(payload.get("user_id", 0))
        amount_eur = float(payload.get("amount_eur", 0))
        crypto_currency = payload.get("crypto_currency", "")
        # Vérifier que la crypto est supportée
        if crypto_currency.lower() not in SUPPORTED_CRYPTOS:
            raise HTTPException(
                status_code=400,
                detail=f"Crypto non supportée. Cryptos disponibles: {list(SUPPORTED_CRYPTOS.keys())}"
            )

        crypto_info = SUPPORTED_CRYPTOS[crypto_currency.lower()]

        # Vérifier le montant minimum
        if amount_eur < crypto_info["min_amount"]:
            raise HTTPException(
                status_code=400,
                detail=f"Montant minimum: {crypto_info['min_amount']} USD"
            )

        # Générer un ID unique pour la commande
        order_id = f"user{user_id}_{int(time.time())}"

        # Utiliser le code API de la crypto (ex: eth pour Ethereum)
        api_currency = crypto_info.get("api_code", crypto_currency.lower())

        # Créer le paiement via NowPayments
        payment_data = nowpayments.create_payment(
            price_amount=amount_eur,
            price_currency="usd",
            pay_currency=api_currency,
            order_id=order_id,
            order_description=f"Dépôt de {amount_eur} USD pour utilisateur {user_id}",
            ipn_callback_url=f"{WEBHOOK_URL}/crypto/webhook" if WEBHOOK_URL else None
        )

        if not payment_data:
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de la création du paiement"
            )

        # Sauvegarder le paiement en attente dans la DB
        db = load_db()
        if "crypto_payments" not in db:
            db["crypto_payments"] = {}

        db["crypto_payments"][payment_data["payment_id"]] = {
            "user_id": user_id,
            "order_id": order_id,
            "amount_eur": amount_eur,
            "crypto_currency": crypto_currency.lower(),
            "pay_amount": payment_data.get("pay_amount"),
            "pay_address": payment_data.get("pay_address"),
            "payment_id": payment_data["payment_id"],
            "payment_status": payment_data.get("payment_status", "waiting"),
            "created_at": time.time(),
            "updated_at": time.time()
        }
        save_db(db)

        return {
            "success": True,
            "payment_id": payment_data["payment_id"],
            "pay_address": payment_data.get("pay_address"),
            "pay_amount": payment_data.get("pay_amount"),
            "pay_currency": crypto_currency.upper(),
            "price_amount": amount_eur,
            "price_currency": "EUR",
            "order_id": order_id,
            "payment_status": payment_data.get("payment_status"),
            "crypto_info": crypto_info
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Erreur création paiement crypto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/crypto/payment-status/{payment_id}")
def get_crypto_payment_status(payment_id: str):
    """Vérifier le statut d'un paiement crypto"""
    try:
        # Vérifier dans la DB locale
        db = load_db()
        local_payment = db.get("crypto_payments", {}).get(payment_id)

        if not local_payment:
            raise HTTPException(status_code=404, detail="Paiement non trouvé")

        # Vérifier le statut via l'API NowPayments
        payment_status = nowpayments.get_payment_status(payment_id)

        if payment_status:
            # Mettre à jour le statut local
            local_payment["payment_status"] = payment_status.get("payment_status")
            local_payment["updated_at"] = time.time()

            if "actually_paid" in payment_status:
                local_payment["actually_paid"] = payment_status["actually_paid"]

            db["crypto_payments"][payment_id] = local_payment
            save_db(db)

            return {
                "payment_id": payment_id,
                "payment_status": payment_status.get("payment_status"),
                "pay_amount": payment_status.get("pay_amount"),
                "actually_paid": payment_status.get("actually_paid"),
                "pay_address": payment_status.get("pay_address"),
                "price_amount": payment_status.get("price_amount"),
                "price_currency": payment_status.get("price_currency"),
                "pay_currency": payment_status.get("pay_currency"),
                "order_id": payment_status.get("order_id"),
                "created_at": local_payment.get("created_at"),
                "user_id": local_payment.get("user_id")
            }

        return local_payment

    except HTTPException:
        raise
    except Exception as e:
        print(f"Erreur vérification statut: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/crypto/webhook")
async def crypto_payment_webhook(request: Request, x_nowpayments_sig: Optional[str] = Header(None)):
    """Webhook pour recevoir les notifications de paiement NowPayments"""
    try:
        # Lire le body brut
        body = await request.body()

        # Vérifier la signature si IPN secret est configuré
        if NOWPAYMENTS_IPN_SECRET and x_nowpayments_sig:
            if not nowpayments.verify_ipn_signature(body, x_nowpayments_sig):
                print("⚠️  Signature IPN invalide!")
                raise HTTPException(status_code=401, detail="Signature invalide")

        # Parser les données
        data = await request.json()

        payment_id = data.get("payment_id")
        payment_status = data.get("payment_status")
        order_id = data.get("order_id")

        print(f"📩 Webhook reçu: {payment_id} - Statut: {payment_status}")

        # Charger la DB
        db = load_db()

        if payment_id not in db.get("crypto_payments", {}):
            print(f"⚠️  Paiement {payment_id} non trouvé dans la DB")
            return {"status": "payment_not_found"}

        payment_data = db["crypto_payments"][payment_id]
        user_id = payment_data["user_id"]
        amount_eur = payment_data["amount_eur"]

        # Mettre à jour le statut
        payment_data["payment_status"] = payment_status
        payment_data["updated_at"] = time.time()

        if "actually_paid" in data:
            payment_data["actually_paid"] = data["actually_paid"]

        # Si le paiement est confirmé ou partiellement confirmé
        if payment_status in ["finished", "confirmed", "sending"]:
            # Créditer l'utilisateur seulement si pas déjà crédité
            if not payment_data.get("credited", False):
                user = get_or_create_user(user_id)
                user["balance"] += amount_eur
                user["total_deposits"] += amount_eur
                save_user(user_id)

                payment_data["credited"] = True
                payment_data["credited_at"] = time.time()

                print(f"✅ Utilisateur {user_id} crédité de {amount_eur} EUR")

        # Sauvegarder
        db["crypto_payments"][payment_id] = payment_data
        save_db(db)

        return {"status": "ok", "payment_status": payment_status}

    except Exception as e:
        print(f"❌ Erreur webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/crypto/user-payments/{user_id}")
def get_user_crypto_payments(user_id: int):
    """Récupérer l'historique des paiements crypto d'un utilisateur"""
    try:
        db = load_db()
        all_payments = db.get("crypto_payments", {})

        user_payments = [
            payment for payment in all_payments.values()
            if payment.get("user_id") == user_id
        ]

        # Trier par date décroissante
        user_payments.sort(key=lambda x: x.get("created_at", 0), reverse=True)

        return {
            "user_id": user_id,
            "payments": user_payments,
            "total_payments": len(user_payments)
        }

    except Exception as e:
        print(f"Erreur récupération historique: {e}")
        raise HTTPException(status_code=500, detail=str(e))
