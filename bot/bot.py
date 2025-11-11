import sys
import io
# Configuration de l'encodage UTF-8 pour Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

# -----------------------------
# CHARGEMENT DU TOKEN
# -----------------------------
try:
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    if not TOKEN:
        raise ValueError("Token non trouvé dans .env")
    print("✅ Token chargé depuis .env")
except:
    TOKEN = "8378719608:AAERI_6EF45m2PKkoevA6gIRNP1OhKXn3W0"
    print("⚠️  Utilisation du token direct (fallback)")
    ADMIN_CHAT_ID = None

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
USER_STATES = {}
USER_CARTS = {}  # Panier pour chaque utilisateur

print(f"🚀 Token utilisé: {TOKEN[:10]}...")

# -----------------------------
# CLAVIERS
# -----------------------------
def get_main_keyboard():
    """Clavier principal avec panier"""
    keyboard = [
        ["🔵 Mon Profil", "🔵 Magasin"],
        ["🔵 Mon Panier", "💎 Depot Crypto"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choisissez une option..."
    )

def get_profile_keyboard():
    """Clavier du profil"""
    keyboard = [
        ["📘 Mes Achats", "🔄 Recommencer"],
        ["◀️ Retour"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choisissez une option..."
    )

def get_shop_keyboard():
    """Clavier du magasin avec retour"""
    keyboard = [
        ["🔵 Voir Panier", "◀️ Retour"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choisissez un produit..."
    )

def get_cart_keyboard():
    """Clavier du panier"""
    keyboard = [
        ["💎 Payer Tout", "🗑️ Vider Panier"],
        ["◀️ Retour au Magasin"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Gérez votre panier..."
    )

def get_product_action_keyboard():
    """Clavier pour choisir l'action sur un produit"""
    keyboard = [
        ["🔵 Ajouter au Panier", "💎 Acheter Maintenant"],
        ["◀️ Retour"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choisissez une action..."
    )

def get_back_keyboard():
    """Bouton retour simple"""
    return ReplyKeyboardMarkup(
        [["◀️ Retour"]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Retour..."
    )

def get_yes_no_keyboard():
    """Boutons Oui/Non"""
    return ReplyKeyboardMarkup(
        [["Oui", "Non"]],
        one_time_keyboard=False,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Oui ou Non..."
    )

# -----------------------------
# COMMANDE /START
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    # Réinitialiser l'état
    USER_STATES[user_id] = None

    # Récupérer solde utilisateur
    balance = 0.0
    purchases = 0
    try:
        res = requests.get(f"{API_URL}/user/{user_id}")
        if res.status_code == 200:
            data = res.json()
            balance = data.get("balance", 0.0)
            purchases = data.get("total_purchases", 0)
    except Exception:
        pass

    welcome_text = f"""
╔═══════════════════════════════╗
║   🛍️ LISTMARKET PREMIUM      ║
╚═══════════════════════════════╝

👋 Bienvenue @{user.username or 'Client'} !

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 VOTRE COMPTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Solde disponible : {balance:.2f} €
📦 Achats effectués : {purchases}
🕒 {datetime.now().strftime('%H:%M - %d/%m/%Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ NOS SERVICES PREMIUM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Listes téléphoniques qualifiées (+ 6M)
✅ Bases d'emails vérifiées (+ 5.9M)
✅ Fiches clients bancaires détaillées
✅ Bases ciblées (seniors, banques...)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 Support : @NumPlace_bot
🌐 Canal officiel : @NumPlace_bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔒 Paiements 100% sécurisés
⚡ Livraison instantanée
🎯 Données vérifiées et à jour
"""
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

# -----------------------------
# GESTION DES MESSAGES
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    text = update.message.text.strip()

    state = USER_STATES.get(user_id)

    # ========== MENU PRINCIPAL ==========
    if text == "🔵 Mon Profil" or text == "🧑 Mon Profil":
        await show_profile(update, context)

    elif text == "🔵 Magasin" or text == "🛍 Magasin":
        await show_shop(update, context)

    elif text == "🔵 Mon Panier" or text == "🛒 Mon Panier" or text == "🔵 Voir Panier" or text == "🛒 Voir Panier":
        await show_cart(update, context)

    elif text == "💎 Depot Crypto" or text == "💰 Depot Crypto":
        await start_deposit(update, context)

    elif text == "◀️ Retour" or text == "🔙 Retour" or text == "◀️ Retour au Magasin" or text == "🔙 Retour au Magasin":
        # Vérifier le contexte pour savoir où retourner
        if isinstance(state, dict):
            if state.get("in_shop") or state.get("in_cart"):
                await show_shop(update, context)
                return
        await start(update, context)

    # ========== PROFIL ==========
    elif text == "📘 Mes Achats" or text == "📜 Mes Achats":
        await show_purchases(update, context)

    elif text == "🔄 Recommencer":
        await start(update, context)

    # ========== PANIER ==========
    elif text == "💎 Payer Tout" or text == "💳 Payer Tout":
        await checkout_cart(update, context)

    elif text == "🗑️ Vider Panier":
        await clear_cart(update, context)

    # ========== DEPOT ==========
    elif isinstance(state, dict) and state.get("state") == "awaiting_deposit_amount":
        await handle_deposit_amount(update, context)

    elif isinstance(state, dict) and state.get("state") == "awaiting_crypto_amount":
        await handle_crypto_amount(update, context)

    # ========== ACHAT ==========
    elif isinstance(state, dict) and state.get("state") == "confirm_purchase":
        await handle_purchase_confirmation(update, context)

    else:
        # Message par défaut
        await update.message.reply_text(
            "Je n'ai pas compris. Utilisez les boutons du menu.",
            reply_markup=get_main_keyboard()
        )

# -----------------------------
# AFFICHER LE PROFIL
# -----------------------------
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    user_info = {}
    try:
        res = requests.get(f"{API_URL}/user/{user_id}")
        if res.status_code == 200:
            user_info = res.json()
    except Exception as e:
        print(f"Erreur API user: {e}")

    username = user_info.get("username") or user.username or "Client"
    grade = user_info.get("grade") or "Membre"
    balance = user_info.get("balance", 0.0)
    total_purchases = user_info.get("total_purchases", 0)
    total_deposits = user_info.get("total_deposits", 0.0)

    profile_text = f"""
╔═══════════════════════════════╗
║      👤 PROFIL CLIENT        ║
╚═══════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 INFORMATIONS DU COMPTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 Utilisateur : @{username}
🆔 ID Client : {user_id}
⭐ Statut : {grade}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 STATISTIQUES FINANCIÈRES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💵 Solde disponible : {balance:.2f} €
📦 Total achats : {total_purchases}
💳 Total dépôts : {total_deposits:.2f} €
📊 Dépensé : {total_deposits - balance:.2f} €

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕒 Mis à jour : {datetime.now().strftime('%H:%M - %d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Astuce : Rechargez votre compte pour
   accéder à nos produits premium !
"""
    await update.message.reply_text(profile_text, reply_markup=get_profile_keyboard())

# -----------------------------
# AFFICHER LES ACHATS
# -----------------------------
async def show_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    try:
        res = requests.get(f"{API_URL}/user/{user_id}/purchases")
        if res.status_code == 200:
            data = res.json()
            purchases = data.get("purchases", [])

            if not purchases:
                purchases_text = """
╔═══════════════════════════════╗
║    📜 HISTORIQUE D'ACHATS     ║
╚═══════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Aucun achat effectué
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Rendez-vous dans le magasin pour
   découvrir nos produits !
"""
            else:
                purchases_text = f"""
╔═══════════════════════════════╗
║    📜 HISTORIQUE D'ACHATS     ║
╚═══════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Total : {len(purchases)} achat(s)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
                for i, purchase in enumerate(purchases[-10:], 1):
                    product = purchase.get('product', 'Produit inconnu')
                    price = purchase.get('price', 0)
                    purchases_text += f"{i}. 📋 {product}\n"
                    purchases_text += f"   💰 Prix: {price:.2f} €\n\n"

                if len(purchases) > 10:
                    purchases_text += f"\n💡 Affichage des 10 derniers achats sur {len(purchases)}\n"

            await update.message.reply_text(purchases_text, reply_markup=get_profile_keyboard())
        else:
            await update.message.reply_text(
                "❌ Erreur lors de la récupération des achats",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        await update.message.reply_text(
            "❌ Erreur lors de la récupération des achats",
            reply_markup=get_main_keyboard()
        )
        print(f"Erreur récupération achats: {e}")

# -----------------------------
# AFFICHER LE MAGASIN
# -----------------------------
async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    try:
        res = requests.get(f"{API_URL}/products").json()
        available_products = [p for p in res.get("products", []) if p.get("available", 0) > 0]

        if not available_products:
            await update.message.reply_text(
                "❌ Aucun produit disponible pour le moment.",
                reply_markup=get_main_keyboard()
            )
            return

        products_text = f"""
╔═══════════════════════════════╗
║    🛍️ CATALOGUE PREMIUM      ║
╚═══════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 PRODUITS DISPONIBLES ({len(available_products)})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        # Créer des boutons inline cliquables pour chaque produit
        keyboard = []
        for p in available_products:
            name = p.get('filename', 'Produit inconnu')
            price = p.get('price', 0)
            stock = p.get('available', 0)
            desc = p.get('description', '')

            products_text += f"{'═' * 31}\n"
            products_text += f"📋 {name}\n"
            products_text += f"\n"
            products_text += f"   💵 Prix : {price:.2f} € / unité\n"
            products_text += f"   📊 Stock : {stock:,} disponibles\n"
            if desc:
                products_text += f"   📝 {desc}\n"
            products_text += "\n"

            # Bouton cliquable pour ce produit
            button_text = f"🛒 {name} - {price:.2f} €"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_{name}")])

        products_text += f"""{'═' * 31}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👇 Cliquez sur un produit pour l'acheter
⚡ Livraison immédiate après paiement
"""

        await update.message.reply_text(
            products_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Erreur lors du chargement des produits",
            reply_markup=get_main_keyboard()
        )
        print(f"Erreur API produits: {e}")

# -----------------------------
# GESTION DES CALLBACKS (BOUTONS INLINE)
# -----------------------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    callback_data = query.data

    # Sélection d'un produit
    if callback_data.startswith("select_"):
        product_name = callback_data[7:]  # Enlever "select_"

        try:
            res = requests.get(f"{API_URL}/products").json()
            product = next((p for p in res.get("products", []) if p.get("filename") == product_name and p.get("available", 0) > 0), None)

            if product:
                price = product.get('price')

                # Afficher les options d'action
                action_text = f"""
╔═══════════════════════════════╗
║    🛍️ PRODUIT SÉLECTIONNÉ    ║
╚═══════════════════════════════╝

📋 Produit : {product_name}
💰 Prix : {price:.2f} €

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Que voulez-vous faire ?
"""
                keyboard = [
                    [
                        InlineKeyboardButton("🔵 Ajouter au Panier", callback_data=f"cart_{product_name}"),
                        InlineKeyboardButton("💎 Acheter Maintenant", callback_data=f"buy_{product_name}")
                    ],
                    [InlineKeyboardButton("◀️ Retour", callback_data="back_shop")]
                ]
                await query.edit_message_text(action_text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await query.edit_message_text("❌ Produit non trouvé ou indisponible.")
        except Exception as e:
            await query.edit_message_text("❌ Erreur lors de la sélection du produit")
            print(f"Erreur sélection produit: {e}")

    # Ajouter au panier
    elif callback_data.startswith("cart_"):
        product_name = callback_data[5:]  # Enlever "cart_"

        try:
            res = requests.get(f"{API_URL}/products").json()
            product = next((p for p in res.get("products", []) if p.get("filename") == product_name), None)

            if product:
                price = product.get('price')

                if user_id not in USER_CARTS:
                    USER_CARTS[user_id] = []

                USER_CARTS[user_id].append({
                    "product": product_name,
                    "price": price
                })

                cart_count = len(USER_CARTS[user_id])

                await query.edit_message_text(
                    f"✅ Produit ajouté au panier !\n\n📋 {product_name}\n💰 {price:.2f} €\n\n🛒 Panier : {cart_count} article(s)\n\n💡 Retournez au magasin pour continuer vos achats"
                )
        except Exception as e:
            await query.edit_message_text("❌ Erreur lors de l'ajout au panier")
            print(f"Erreur ajout panier: {e}")

    # Acheter maintenant
    elif callback_data.startswith("buy_"):
        product_name = callback_data[4:]  # Enlever "buy_"

        try:
            res = requests.get(f"{API_URL}/products").json()
            product = next((p for p in res.get("products", []) if p.get("filename") == product_name), None)

            if product:
                price = product.get('price')

                confirm_text = f"""
╔═══════════════════════════════╗
║    ✅ CONFIRMATION D'ACHAT    ║
╚═══════════════════════════════╝

📋 Produit : {product_name}
💰 Prix : {price:.2f} €

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Voulez-vous confirmer cet achat ?
"""
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Oui", callback_data=f"confirm_{product_name}"),
                        InlineKeyboardButton("❌ Non", callback_data="back_shop")
                    ]
                ]
                await query.edit_message_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            await query.edit_message_text("❌ Erreur lors de la préparation de l'achat")
            print(f"Erreur préparation achat: {e}")

    # Confirmer l'achat
    elif callback_data.startswith("confirm_"):
        product_name = callback_data[8:]  # Enlever "confirm_"

        try:
            resp = requests.post(f"{API_URL}/purchase", json={"user_id": user_id, "product": product_name})
            if resp.status_code == 200:
                data = resp.json()
                line = data.get("line")
                new_balance = data.get("balance")
                price = next((p.get('price') for p in requests.get(f"{API_URL}/products").json().get("products", []) if p.get("filename") == product_name), 0)

                success_text = f"""
╔═══════════════════════════════╗
║    ✅ ACHAT CONFIRMÉ         ║
╚═══════════════════════════════╝

📋 Produit : {product_name}
💰 Prix payé : {price:.2f} €
💵 Nouveau solde : {new_balance:.2f} €

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 CONTENU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{line}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕒 {datetime.now().strftime('%H:%M - %d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Merci de votre achat !
"""
                await query.edit_message_text(success_text)
            else:
                try:
                    detail = resp.json().get("detail")
                except Exception:
                    detail = resp.text
                await query.edit_message_text(f"❌ Achat refusé: {detail}")
        except Exception as e:
            await query.edit_message_text("❌ Erreur lors de l'achat")
            print(f"Erreur achat: {e}")

    # Retour au magasin
    elif callback_data == "back_shop":
        await query.delete_message()  # Supprimer le message précédent

    # Sélection d'une crypto
    elif callback_data.startswith("crypto_"):
        crypto_currency = callback_data[7:]  # Enlever "crypto_"
        USER_STATES[user_id] = {
            "state": "awaiting_crypto_amount",
            "crypto_currency": crypto_currency
        }

        # Récupérer les infos de la crypto
        try:
            res = requests.get(f"{API_URL}/crypto/currencies")
            cryptos = res.json().get("currencies", {})
            crypto_info = cryptos.get(crypto_currency, {})

            min_amount = crypto_info.get("min_amount", 10)
            icon = crypto_info.get("icon", "💎")
            name = crypto_info.get("name", crypto_currency.upper())

            amount_text = f"""
╔═══════════════════════════════╗
║   {icon} DÉPÔT {name.upper()}
╚═══════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 MONTANT DU DÉPÔT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💵 Montant minimum : {min_amount} EUR
🌐 Network : {crypto_info.get('network', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👉 Entrez le montant en EUR :

Exemple : 50
"""
            await query.edit_message_text(amount_text)
        except Exception as e:
            await query.edit_message_text(f"❌ Erreur: {e}")

    # Retour au menu principal
    elif callback_data == "back_main":
        await query.delete_message()

    # Vérifier le statut d'un paiement
    elif callback_data.startswith("check_payment_"):
        payment_id = callback_data[14:]  # Enlever "check_payment_"
        await check_crypto_payment_status(query, payment_id)

# -----------------------------
# AFFICHER LE PANIER
# -----------------------------
async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    cart = USER_CARTS.get(user_id, [])

    if not cart:
        cart_text = """
╔═══════════════════════════════╗
║      🛒 MON PANIER           ║
╚═══════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛒 Votre panier est vide
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Rendez-vous au magasin pour
   ajouter des produits !
"""
        await update.message.reply_text(cart_text, reply_markup=get_main_keyboard())
    else:
        total = sum(item['price'] for item in cart)

        cart_text = f"""
╔═══════════════════════════════╗
║      🛒 MON PANIER           ║
╚═══════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Articles : {len(cart)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        for i, item in enumerate(cart, 1):
            cart_text += f"{i}. 📋 {item['product']}\n"
            cart_text += f"   💰 {item['price']:.2f} €\n\n"

        cart_text += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 TOTAL : {total:.2f} €
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💳 Payer Tout - Acheter tous les articles
🗑️ Vider Panier - Supprimer tous les articles
"""

        await update.message.reply_text(cart_text, reply_markup=get_cart_keyboard())
        USER_STATES[user_id] = {"in_cart": True}

# -----------------------------
# PAYER TOUT LE PANIER
# -----------------------------
async def checkout_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    cart = USER_CARTS.get(user_id, [])

    if not cart:
        await update.message.reply_text(
            "❌ Votre panier est vide.",
            reply_markup=get_main_keyboard()
        )
        return

    total = sum(item['price'] for item in cart)

    # Acheter tous les produits
    results = []
    failed = []

    for item in cart:
        try:
            resp = requests.post(f"{API_URL}/purchase", json={"user_id": user_id, "product": item['product']})
            if resp.status_code == 200:
                data = resp.json()
                results.append({
                    "product": item['product'],
                    "price": item['price'],
                    "line": data.get("line")
                })
            else:
                failed.append(item['product'])
        except Exception as e:
            failed.append(item['product'])
            print(f"Erreur achat {item['product']}: {e}")

    # Vider le panier
    USER_CARTS[user_id] = []

    if results:
        success_text = f"""
╔═══════════════════════════════╗
║    ✅ ACHAT CONFIRMÉ         ║
╚═══════════════════════════════╝

📦 {len(results)} produit(s) acheté(s)
💰 Total payé : {sum(r['price'] for r in results):.2f} €

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 VOS PRODUITS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        for i, r in enumerate(results, 1):
            success_text += f"{i}. 📋 {r['product']}\n"
            success_text += f"   💰 {r['price']:.2f} €\n"
            success_text += f"   📄 {r['line']}\n\n"

        if failed:
            success_text += f"\n⚠️ Échec pour : {', '.join(failed)}\n"

        success_text += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕒 {datetime.now().strftime('%H:%M - %d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Merci de votre achat !
"""
        await update.message.reply_text(success_text, reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(
            "❌ Échec de tous les achats. Vérifiez votre solde.",
            reply_markup=get_main_keyboard()
        )

    USER_STATES[user_id] = None

# -----------------------------
# VIDER LE PANIER
# -----------------------------
async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    USER_CARTS[user_id] = []

    await update.message.reply_text(
        "🗑️ Panier vidé avec succès.",
        reply_markup=get_main_keyboard()
    )
    USER_STATES[user_id] = None

# -----------------------------
# CONFIRMATION ACHAT IMMÉDIAT
# -----------------------------
async def handle_purchase_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip().lower()

    state = USER_STATES.get(user_id)
    product_name = state.get("product")
    price = state.get("price")

    if text == "oui":
        try:
            resp = requests.post(f"{API_URL}/purchase", json={"user_id": user_id, "product": product_name})
            if resp.status_code == 200:
                data = resp.json()
                line = data.get("line")
                new_balance = data.get("balance")

                success_text = f"""
╔═══════════════════════════════╗
║    ✅ ACHAT CONFIRMÉ         ║
╚═══════════════════════════════╝

📋 Produit : {product_name}
💰 Prix payé : {price:.2f} €
💵 Nouveau solde : {new_balance:.2f} €

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 CONTENU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{line}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕒 {datetime.now().strftime('%H:%M - %d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Merci de votre achat !
"""
                await update.message.reply_text(success_text, reply_markup=get_main_keyboard())
            else:
                try:
                    detail = resp.json().get("detail")
                except Exception:
                    detail = resp.text
                await update.message.reply_text(
                    f"❌ Achat refusé: {detail}",
                    reply_markup=get_main_keyboard()
                )
        except Exception as e:
            await update.message.reply_text(
                "❌ Erreur lors de l'achat",
                reply_markup=get_main_keyboard()
            )
            print(f"Erreur achat: {e}")
    else:
        await update.message.reply_text(
            "❌ Achat annulé.",
            reply_markup=get_main_keyboard()
        )

    USER_STATES[user_id] = None

# -----------------------------
# DEPOT - DEBUT
# -----------------------------
async def start_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Récupérer les cryptos disponibles
    try:
        res = requests.get(f"{API_URL}/crypto/currencies")
        if res.status_code == 200:
            cryptos = res.json().get("currencies", {})
        else:
            cryptos = {}
    except:
        cryptos = {}

    deposit_text = """
╔═══════════════════════════════╗
║   💎 DÉPÔT CRYPTO            ║
╚═══════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 CRYPTOMONNAIES ACCEPTÉES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # Créer les boutons pour chaque crypto
    keyboard = []
    for crypto_key, crypto_info in cryptos.items():
        icon = crypto_info.get("icon", "💎")
        name = crypto_info.get("name", crypto_key.upper())
        min_amount = crypto_info.get("min_amount", 10)
        button_text = f"{icon} {name} (Min: {min_amount}€)"

        deposit_text += f"\n{icon} {name}\n   Network: {crypto_info.get('network', 'N/A')}\n   Minimum: {min_amount} EUR\n"

        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"crypto_{crypto_key}")])

    deposit_text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Paiement depuis n'importe quel wallet
✅ Confirmation automatique
✅ Crédité instantanément
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👉 Sélectionnez votre cryptomonnaie :
"""

    keyboard.append([InlineKeyboardButton("◀️ Retour", callback_data="back_main")])

    await update.message.reply_text(
        deposit_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    USER_STATES[user_id] = {"state": "awaiting_crypto_selection"}

# -----------------------------
# DEPOT - MONTANT
# -----------------------------
async def handle_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if text == "🔙 Retour":
        await start(update, context)
        return

    text = text.replace(',', '.')
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Montant invalide. Entrez un nombre en euros, ex: 12.5",
            reply_markup=get_back_keyboard()
        )
        return

    if amount < 10:
        await update.message.reply_text(
            "❌ Le dépôt minimum est de 10 €.",
            reply_markup=get_back_keyboard()
        )
        return

    deposit_info_text = f"""
╔═══════════════════════════════╗
║   💰 INFORMATIONS PAIEMENT    ║
╚═══════════════════════════════╝

💵 Montant : {amount:.2f} €

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 ADRESSES CRYPTO (Exodus)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

₿ BTC:
bc1q...

☀️ SOL:
7FxdtgP28UYF1IAUImTubPRo63glwXnh92tlTmWi1oQ5n

⟠ ETH:
0xabc...

🪙 LTC:
ltc1qlx6qc8tz6rtr4udzapedvskeutux996ewwdy0a

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📸 Après paiement, envoyez ici la capture d'écran
   Votre ID sera joint automatiquement
"""
    await update.message.reply_text(deposit_info_text, reply_markup=get_back_keyboard())
    USER_STATES[user_id] = {"state": "awaiting_deposit_proof", "amount": amount}

# -----------------------------
# CRYPTO - MONTANT
# -----------------------------
async def handle_crypto_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = USER_STATES.get(user_id, {})
    crypto_currency = state.get("crypto_currency")

    text = update.message.text.strip().replace(',', '.')

    try:
        amount_eur = float(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Montant invalide. Entrez un nombre, ex: 50",
            reply_markup=get_back_keyboard()
        )
        return

    # Récupérer les infos de la crypto
    try:
        res = requests.get(f"{API_URL}/crypto/currencies")
        cryptos = res.json().get("currencies", {})
        crypto_info = cryptos.get(crypto_currency, {})
        min_amount = crypto_info.get("min_amount", 10)

        if amount_eur < min_amount:
            await update.message.reply_text(
                f"❌ Le montant minimum est de {min_amount} EUR",
                reply_markup=get_back_keyboard()
            )
            return

        # Créer le paiement
        payment_res = requests.post(
            f"{API_URL}/crypto/create-payment",
            json={
                "user_id": user_id,
                "amount_eur": amount_eur,
                "crypto_currency": crypto_currency
            }
        )

        if payment_res.status_code == 200:
            payment_data = payment_res.json()

            icon = crypto_info.get("icon", "💎")
            name = crypto_info.get("name", crypto_currency.upper())
            pay_amount = payment_data.get("pay_amount")
            pay_address = payment_data.get("pay_address")
            payment_id = payment_data.get("payment_id")

            payment_text = f"""
╔═══════════════════════════════╗
║   {icon} PAIEMENT {name.upper()}       ║
╚═══════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 DÉTAILS DU PAIEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💵 Montant en EUR : {amount_eur:.2f} €
{icon} Montant à envoyer : {pay_amount} {crypto_currency.upper()}
🌐 Network : {crypto_info.get('network', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 ADRESSE DE PAIEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<code>{pay_address}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ IMPORTANT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Envoyez EXACTEMENT {pay_amount} {crypto_currency.upper()}
✅ Sur le réseau {crypto_info.get('network', 'N/A')}
✅ À l'adresse ci-dessus
⏱️ Votre solde sera crédité automatiquement
   après confirmation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕒 Paiement ID : {payment_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            keyboard = [
                [InlineKeyboardButton("🔄 Vérifier le paiement", callback_data=f"check_payment_{payment_id}")],
                [InlineKeyboardButton("◀️ Retour", callback_data="back_main")]
            ]

            await update.message.reply_text(
                payment_text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            USER_STATES[user_id] = {
                "state": "awaiting_crypto_payment",
                "payment_id": payment_id
            }

        else:
            error_detail = payment_res.json().get("detail", "Erreur inconnue")
            await update.message.reply_text(
                f"❌ Erreur lors de la création du paiement:\n{error_detail}",
                reply_markup=get_main_keyboard()
            )
            USER_STATES[user_id] = None

    except Exception as e:
        print(f"Erreur création paiement crypto: {e}")
        await update.message.reply_text(
            "❌ Erreur lors de la création du paiement. Veuillez réessayer.",
            reply_markup=get_main_keyboard()
        )
        USER_STATES[user_id] = None

# -----------------------------
# CRYPTO - VÉRIFIER STATUT
# -----------------------------
async def check_crypto_payment_status(query, payment_id):
    """Vérifier le statut d'un paiement crypto"""
    try:
        res = requests.get(f"{API_URL}/crypto/payment-status/{payment_id}")

        if res.status_code == 200:
            payment_data = res.json()
            payment_status = payment_data.get("payment_status")
            pay_amount = payment_data.get("pay_amount")
            pay_currency = payment_data.get("pay_currency", "").upper()
            actually_paid = payment_data.get("actually_paid")

            status_icons = {
                "waiting": "⏳",
                "confirming": "🔄",
                "confirmed": "✅",
                "sending": "📤",
                "finished": "✅",
                "failed": "❌",
                "refunded": "↩️",
                "expired": "⏰"
            }

            icon = status_icons.get(payment_status, "❓")

            if payment_status in ["finished", "confirmed"]:
                status_text = f"""
╔═══════════════════════════════╗
║   ✅ PAIEMENT CONFIRMÉ        ║
╚═══════════════════════════════╝

{icon} Statut : {payment_status.upper()}
💎 Montant : {pay_amount} {pay_currency}
✅ Payé : {actually_paid if actually_paid else pay_amount} {pay_currency}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 Votre solde a été crédité !
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Merci pour votre paiement !
"""
                await query.edit_message_text(status_text)

            elif payment_status == "waiting":
                status_text = f"""
╔═══════════════════════════════╗
║   ⏳ EN ATTENTE DE PAIEMENT   ║
╚═══════════════════════════════╝

{icon} Statut : EN ATTENTE
💎 Montant attendu : {pay_amount} {pay_currency}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ Nous attendons votre paiement...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                keyboard = [
                    [InlineKeyboardButton("🔄 Vérifier à nouveau", callback_data=f"check_payment_{payment_id}")],
                    [InlineKeyboardButton("◀️ Retour", callback_data="back_main")]
                ]
                await query.edit_message_text(
                    status_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            else:
                status_text = f"""
╔═══════════════════════════════╗
║   {icon} STATUT DU PAIEMENT    ║
╚═══════════════════════════════╝

{icon} Statut : {payment_status.upper()}
💎 Montant : {pay_amount} {pay_currency}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                keyboard = [
                    [InlineKeyboardButton("🔄 Actualiser", callback_data=f"check_payment_{payment_id}")],
                    [InlineKeyboardButton("◀️ Retour", callback_data="back_main")]
                ]
                await query.edit_message_text(
                    status_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        else:
            await query.edit_message_text("❌ Erreur lors de la vérification du paiement")

    except Exception as e:
        print(f"Erreur vérification statut: {e}")
        await query.edit_message_text("❌ Erreur lors de la vérification du paiement")

# -----------------------------
# DEPOT - PHOTO
# -----------------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = USER_STATES.get(user_id)

    if isinstance(state, dict) and state.get("state") == "awaiting_deposit_proof":
        try:
            photo = update.message.photo[-1]
            file_id = photo.file_id
            amount_info = state.get("amount")
            caption = f"""Preuve de dépôt
User ID: {user_id}
Username: @{update.message.from_user.username or 'ANON'}
Montant déclaré: {amount_info if amount_info is not None else 'N/A'} €
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

            if ADMIN_CHAT_ID:
                await context.bot.send_photo(chat_id=int(ADMIN_CHAT_ID), photo=file_id, caption=caption)
                await update.message.reply_text(
                    "✅ Merci ! Votre preuve a été transmise à l'admin.\n💰 Crédit sous peu.",
                    reply_markup=get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "✅ Merci ! Admin non configuré.\n📞 Envoyez votre capture à @NumPlace_bot.",
                    reply_markup=get_main_keyboard()
                )
        except Exception as e:
            print(f"Erreur transfert preuve: {e}")
            await update.message.reply_text(
                "❌ Erreur lors de l'envoi de la preuve. Réessayez.",
                reply_markup=get_back_keyboard()
            )
        finally:
            USER_STATES[user_id] = None
    else:
        # Photo hors contexte - ignorer
        await update.message.reply_text(
            "Je n'ai pas compris. Utilisez les boutons du menu.",
            reply_markup=get_main_keyboard()
        )

# -----------------------------
# INITIALISATION DU BOT
# -----------------------------
if __name__ == "__main__":
    print("🚀 Démarrage du bot...")
    print(f"🔍 API URL: {API_URL}")

    try:
        app = ApplicationBuilder().token(TOKEN).build()

        # Configurer le menu de commandes (bouton à gauche)
        commands = [
            BotCommand("start", "🏠 Menu principal"),
            BotCommand("profil", "🔵 Mon profil"),
            BotCommand("magasin", "🔵 Voir le magasin"),
            BotCommand("panier", "🔵 Mon panier"),
            BotCommand("depot", "💎 Dépôt crypto")
        ]

        # Appliquer les commandes au menu
        async def post_init(application):
            await application.bot.set_my_commands(commands)

        app.post_init = post_init

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("profil", lambda u, c: show_profile(u, c)))
        app.add_handler(CommandHandler("magasin", lambda u, c: show_shop(u, c)))
        app.add_handler(CommandHandler("panier", lambda u, c: show_cart(u, c)))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        print("✅ Bot lancé avec succès! En attente de messages...")
        print("📋 Menu de commandes configuré (bouton à gauche)")
        app.run_polling()

    except Exception as e:
        print(f"❌ Erreur critique: {e}")
