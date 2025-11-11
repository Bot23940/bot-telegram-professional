"""
Module de gestion des paiements crypto avec NowPayments
"""
import requests
import hashlib
import hmac
from typing import Dict, Optional, List
from datetime import datetime

class NowPaymentsAPI:
    def __init__(self, api_key: str, ipn_secret: Optional[str] = None):
        self.api_key = api_key
        self.ipn_secret = ipn_secret
        self.base_url = "https://api.nowpayments.io/v1"
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

    def get_available_currencies(self) -> List[str]:
        """Récupérer les cryptos disponibles"""
        try:
            response = requests.get(
                f"{self.base_url}/currencies",
                headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("currencies", [])
            return []
        except Exception as e:
            print(f"Erreur lors de la récupération des devises: {e}")
            return []

    def get_min_amount(self, currency_from: str, currency_to: str = "eur") -> Optional[float]:
        """Récupérer le montant minimum pour une crypto"""
        try:
            response = requests.get(
                f"{self.base_url}/min-amount",
                params={
                    "currency_from": currency_from.lower(),
                    "currency_to": currency_to.lower()
                },
                headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                return float(data.get("min_amount", 0))
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération du montant minimum: {e}")
            return None

    def estimate_price(self, amount: float, currency_from: str, currency_to: str = "eur") -> Optional[Dict]:
        """Estimer le prix de conversion"""
        try:
            response = requests.get(
                f"{self.base_url}/estimate",
                params={
                    "amount": amount,
                    "currency_from": currency_from.lower(),
                    "currency_to": currency_to.lower()
                },
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Erreur lors de l'estimation: {e}")
            return None

    def create_payment(
        self,
        price_amount: float,
        price_currency: str,
        pay_currency: str,
        order_id: str,
        order_description: str = "",
        ipn_callback_url: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Optional[Dict]:
        """Créer un nouveau paiement"""
        try:
            payload = {
                "price_amount": price_amount,
                "price_currency": price_currency.lower(),
                "pay_currency": pay_currency.lower(),
                "order_id": order_id,
                "order_description": order_description or f"Dépôt {pay_currency}",
            }

            if ipn_callback_url:
                payload["ipn_callback_url"] = ipn_callback_url
            if success_url:
                payload["success_url"] = success_url
            if cancel_url:
                payload["cancel_url"] = cancel_url

            response = requests.post(
                f"{self.base_url}/payment",
                json=payload,
                headers=self.headers
            )

            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            else:
                print(f"Erreur création paiement: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Erreur lors de la création du paiement: {e}")
            return None

    def get_payment_status(self, payment_id: str) -> Optional[Dict]:
        """Vérifier le statut d'un paiement"""
        try:
            response = requests.get(
                f"{self.base_url}/payment/{payment_id}",
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Erreur lors de la vérification du paiement: {e}")
            return None

    def verify_ipn_signature(self, request_body: bytes, received_signature: str) -> bool:
        """Vérifier la signature IPN (webhook)"""
        if not self.ipn_secret:
            print("⚠️  IPN Secret non configuré!")
            return False

        try:
            # Calculer la signature HMAC
            calculated_signature = hmac.new(
                self.ipn_secret.encode('utf-8'),
                request_body,
                hashlib.sha512
            ).hexdigest()

            # Comparer les signatures
            return hmac.compare_digest(calculated_signature, received_signature)
        except Exception as e:
            print(f"Erreur lors de la vérification de la signature: {e}")
            return False

    def get_exchange_rate(self, currency_from: str, currency_to: str = "eur") -> Optional[float]:
        """Obtenir le taux de change actuel"""
        try:
            estimate = self.estimate_price(1, currency_from, currency_to)
            if estimate:
                return float(estimate.get("estimated_amount", 0))
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération du taux: {e}")
            return None


# Configuration des cryptos supportées
# Clé = code utilisé dans le bot, api_code = code envoyé à NowPayments
SUPPORTED_CRYPTOS = {
    "btc": {
        "name": "Bitcoin",
        "symbol": "BTC",
        "icon": "₿",
        "min_amount": 10,
        "network": "Bitcoin",
        "api_code": "btc"
    },
    "sol": {
        "name": "Solana",
        "symbol": "SOL",
        "icon": "🌞",
        "min_amount": 5,
        "network": "Solana",
        "api_code": "sol"
    },
    "eth": {
        "name": "Ethereum",
        "symbol": "ETH",
        "icon": "⟠",
        "min_amount": 10,
        "network": "Ethereum",
        "api_code": "eth"
    },
    "ltc": {
        "name": "Litecoin",
        "symbol": "LTC",
        "icon": "Ł",
        "min_amount": 5,
        "network": "Litecoin",
        "api_code": "ltc"
    }
}


def format_crypto_amount(amount: float, currency: str) -> str:
    """Formater un montant crypto"""
    if currency.lower() == "btc":
        return f"{amount:.8f}"
    elif currency.lower() in ["eth", "sol"]:
        return f"{amount:.4f}"
    else:
        return f"{amount:.6f}"
