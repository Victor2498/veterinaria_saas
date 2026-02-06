import mercadopago
import os
from typing import Dict, Any

def get_mp_sdk():
    access_token = os.getenv("MP_ACCESS_TOKEN", "TEST-7957283416238475-020612-4a0b6e92736e4b8a91283c4d5e6f7a8b") # Credencial del dueño del SaaS
    return mercadopago.SDK(access_token)

async def create_plan_payment_link(org_slug: str, plan_name: str, price: float):
    """
    Crea una preferencia de Mercado Pago para cambiar el plan.
    """
    sdk = get_mp_sdk()
    
    preference_data = {
        "items": [
            {
                "title": f"Suscripción DogBot SaaS - Plan {plan_name}",
                "quantity": 1,
                "unit_price": price,
                "currency_id": "ARS"
            }
        ],
        "back_urls": {
            "success": f"https://tusisistema.com/admin/subscription?status=success&plan={plan_name}",
            "failure": f"https://tusisistema.com/admin/subscription?status=failure",
            "pending": f"https://tusisistema.com/admin/subscription?status=pending"
        },
        "auto_return": "approved",
        "external_reference": f"{org_slug}:{plan_name}", # Para identificar el pago después
        "notification_url": "https://tusisistema.com/api/billing/webhook" # Opcional: para procesar el pago automáticamente
    }
    
    preference_response = sdk.preference().create(preference_data)
    preference = preference_response["response"]
    
    return preference.get("init_point") # El link para pagar
