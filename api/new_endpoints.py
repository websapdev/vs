"""
New API endpoints for Vysalytica SaaS
To be integrated into api.py before the OPTIONS handler
"""

# =========================
# Authentication Endpoints
# =========================

@app.route("/api/v1/auth/signup", methods=["POST"])
def auth_signup():
    """Register a new user."""
    try:
        from api.vysalytica.auth import hash_password, create_access_token
        from api.vysalytica.db.models import User
        
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password required"}), 400
        
        db = SessionLocal()
        try:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return jsonify({"success": False, "error": "Email already registered"}), 400
            
            user = User(
                email=email,
                password_hash=hash_password(password),
                name=name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            token = create_access_token({"user_id": user.id, "email": user.email})
            
            return jsonify({
                "success": True,
                "data": {
                    "user": user.to_dict(),
                    "token": token
                }
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/auth/login", methods=["POST"])
def auth_login():
    """Login user."""
    try:
        from api.vysalytica.auth import verify_password, create_access_token
        from api.vysalytica.db.models import User
        
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password required"}), 400
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            
            if not user or not verify_password(password, user.password_hash):
                return jsonify({"success": False, "error": "Invalid credentials"}), 401
            
            if not user.is_active:
                return jsonify({"success": False, "error": "Account inactive"}), 403
            
            token = create_access_token({"user_id": user.id, "email": user.email})
            
            return jsonify({
                "success": True,
                "data": {
                    "user": user.to_dict(),
                    "token": token
                }
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/auth/me", methods=["GET"])
def auth_me():
    """Get current user info from token."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.db.models import User
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404
            
            return jsonify({"success": True, "data": user.to_dict()})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =========================
# Brand Management Endpoints
# =========================

@app.route("/api/v1/brands", methods=["GET"])
def get_brands():
    """Get all brands for the authenticated user."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.db.models import User, Brand
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        
        db = SessionLocal()
        try:
            brands = db.query(Brand).filter(Brand.user_id == user_id).all()
            return jsonify({
                "success": True,
                "data": [b.to_dict() for b in brands]
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/brands", methods=["POST"])
def create_brand():
    """Create a new brand."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.db.models import Brand
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        data = request.get_json()
        
        name = data.get("name")
        primary_url = data.get("primary_url")
        
        if not name or not primary_url:
            return jsonify({"success": False, "error": "Name and primary_url required"}), 400
        
        db = SessionLocal()
        try:
            brand = Brand(
                user_id=user_id,
                name=name,
                primary_url=primary_url,
                catalog_url=data.get("catalog_url"),
                competitors=data.get("competitors", [])
            )
            db.add(brand)
            db.commit()
            db.refresh(brand)
            
            return jsonify({"success": True, "data": brand.to_dict()})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/brands/<int:brand_id>", methods=["GET"])
def get_brand(brand_id):
    """Get a specific brand."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.db.models import Brand
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        
        db = SessionLocal()
        try:
            brand = db.query(Brand).filter(
                Brand.id == brand_id,
                Brand.user_id == user_id
            ).first()
            
            if not brand:
                return jsonify({"success": False, "error": "Brand not found"}), 404
            
            return jsonify({"success": True, "data": brand.to_dict()})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/brands/<int:brand_id>/audits", methods=["GET"])
def get_brand_audits(brand_id):
    """Get all audits for a brand."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.db.models import Brand
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        
        db = SessionLocal()
        try:
            brand = db.query(Brand).filter(
                Brand.id == brand_id,
                Brand.user_id == user_id
            ).first()
            
            if not brand:
                return jsonify({"success": False, "error": "Brand not found"}), 404
            
            audits = db.query(AuditRun).filter(AuditRun.brand_id == brand_id).order_by(
                AuditRun.created_at.desc()
            ).all()
            
            return jsonify({
                "success": True,
                "data": [a.to_dict() for a in audits]
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =========================
# Payment Endpoints
# =========================

@app.route("/api/v1/payments/create-checkout-session", methods=["POST"])
def create_checkout_session():
    """Create a Stripe checkout session."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.stripe_service import create_checkout_session as create_stripe_session
        from api.vysalytica.db.models import Payment
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        data = request.get_json()
        
        amount = data.get("amount", 10000)  # Default $100
        currency = data.get("currency", "usd")
        success_url = data.get("success_url", "http://localhost:3000/checkout/success")
        cancel_url = data.get("cancel_url", "http://localhost:3000/checkout/cancel")
        
        session_data = create_stripe_session(
            user_id=user_id,
            amount=amount,
            currency=currency,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if not session_data:
            return jsonify({"success": False, "error": "Failed to create checkout session"}), 500
        
        db = SessionLocal()
        try:
            payment = Payment(
                user_id=user_id,
                stripe_session_id=session_data["session_id"],
                amount=amount,
                currency=currency,
                status="pending"
            )
            db.add(payment)
            db.commit()
        finally:
            db.close()
        
        return jsonify({
            "success": True,
            "data": {
                "url": session_data["url"],
                "session_id": session_data["session_id"]
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/payments/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events."""
    try:
        from api.vysalytica.stripe_service import verify_webhook_signature
        from api.vysalytica.db.models import Payment
        
        payload = request.data
        sig_header = request.headers.get("Stripe-Signature")
        
        event = verify_webhook_signature(payload, sig_header)
        
        if not event:
            return jsonify({"success": False, "error": "Invalid signature"}), 400
        
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            session_id = session["id"]
            
            db = SessionLocal()
            try:
                payment = db.query(Payment).filter(
                    Payment.stripe_session_id == session_id
                ).first()
                
                if payment:
                    payment.status = "paid"
                    db.commit()
            finally:
                db.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
