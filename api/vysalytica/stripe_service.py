"""
Stripe payment service for Vysalytica.
"""
import os
from typing import Optional

import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_mock")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_mock")


def create_checkout_session(
    user_id: int,
    amount: int,
    currency: str = "usd",
    success_url: str = "http://localhost:3000/checkout/success",
    cancel_url: str = "http://localhost:3000/checkout/cancel",
) -> Optional[dict]:
    """
    Create a Stripe Checkout session.
    
    Returns dict with session_id and url, or None on error.
    """
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": "Vysalytica AI Visibility Audit",
                        },
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"user_id": str(user_id)},
        )
        
        return {
            "session_id": session.id,
            "url": session.url,
        }
    except Exception as e:
        print(f"Stripe error: {e}")
        return None


def verify_webhook_signature(payload: bytes, sig_header: str) -> Optional[dict]:
    """
    Verify Stripe webhook signature and return the event.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        return event
    except Exception as e:
        print(f"Webhook verification error: {e}")
        return None
