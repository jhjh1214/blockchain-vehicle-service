import uuid
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from config import Config
from db.models import db
from extensions import limiter
import threading


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Warn (dev) or raise (prod) when insecure defaults are in use
    Config.validate()

    db.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        db.create_all()
        # Inline schema migrations — idempotent, compatible with SQLite and PostgreSQL
        from sqlalchemy import inspect, text
        try:
            inspector = inspect(db.engine)

            svc_cols = [c['name'] for c in inspector.get_columns('service_metadata')]
            if 'service_center_address' not in svc_cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE service_metadata ADD COLUMN service_center_address VARCHAR(42)"
                    ))
                    conn.commit()

            vin_cols = [c['name'] for c in inspector.get_columns('vehicle_vin_mapping')]
            if 'registered_by' not in vin_cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE vehicle_vin_mapping ADD COLUMN registered_by VARCHAR(42)"
                    ))
                    conn.commit()
                from db.models import User
                mfr = User.query.filter_by(role='MANUFACTURER').first()
                if mfr:
                    with db.engine.connect() as conn:
                        conn.execute(text(
                            "UPDATE vehicle_vin_mapping SET registered_by = :addr "
                            "WHERE registered_by IS NULL"
                        ), {'addr': mfr.blockchain_address})
                        conn.commit()

            if 'registration_status' not in vin_cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE vehicle_vin_mapping "
                        "ADD COLUMN registration_status VARCHAR(20) NOT NULL DEFAULT 'active'"
                    ))
                    conn.commit()

            user_cols = [c['name'] for c in inspector.get_columns('users')]
            if 'consent_given_at' not in user_cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN consent_given_at TIMESTAMP"
                    ))
                    conn.commit()

            if 'email_verified' not in user_cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE"
                    ))
                    conn.commit()

            if 'theme_preference' not in user_cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN theme_preference VARCHAR(10) NOT NULL DEFAULT 'light'"
                    ))
                    conn.commit()

            if 'ssm_number' not in user_cols:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN ssm_number VARCHAR(50)"))
                    conn.commit()

            if 'sc_brand' not in svc_cols:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE service_metadata ADD COLUMN sc_brand VARCHAR(100)"))
                    conn.commit()

            if 'integrity_status' not in svc_cols:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE service_metadata ADD COLUMN integrity_status VARCHAR(20)"))
                    conn.execute(text("ALTER TABLE service_metadata ADD COLUMN integrity_checked_at TIMESTAMP"))
                    conn.commit()

            if 'ecu_modules' not in svc_cols:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE service_metadata ADD COLUMN ecu_modules JSON"))
                    conn.commit()

            if inspector.has_table('dispute_messages'):
                dm_cols = [c['name'] for c in inspector.get_columns('dispute_messages')]
                if 'sender_name' not in dm_cols:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE dispute_messages ADD COLUMN sender_name VARCHAR"))
                        conn.commit()

            if inspector.has_table('notifications'):
                notif_cols = [c['name'] for c in inspector.get_columns('notifications')]
                with db.engine.connect() as conn:
                    if 'type' not in notif_cols:
                        conn.execute(text("ALTER TABLE notifications ADD COLUMN type VARCHAR(50)"))
                    if 'data' not in notif_cols:
                        conn.execute(text("ALTER TABLE notifications ADD COLUMN data JSON"))
                    if 'read' not in notif_cols:
                        conn.execute(text("ALTER TABLE notifications ADD COLUMN read BOOLEAN NOT NULL DEFAULT FALSE"))
                    conn.commit()

            # ensure new tables created by SQLAlchemy models exist
            db.create_all()

        except Exception:
            pass

    # CORS origins are configurable via CORS_ORIGINS env var (comma-separated)
    allowed_origins = [o.strip() for o in Config.CORS_ORIGINS.split(',') if o.strip()]
    CORS(app, resources={
        r'/api/*': {
            'origins': allowed_origins,
            'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            'allow_headers': ['Content-Type', 'Authorization', 'X-Request-ID'],
            'expose_headers': ['X-Request-ID'],
            'supports_credentials': True,
        }
    })

    # ── Request-ID propagation ────────────────────────────────
    @app.before_request
    def _inject_request_id():
        g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())

    @app.after_request
    def _add_request_id(response):
        response.headers['X-Request-ID'] = getattr(g, 'request_id', '')
        return response

    # ── Security headers ─────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'"
        if Config.USE_HTTPS:
            response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
        return response

    # ── Rate limit error handler ─────────────────────────────
    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({'error': 'Too many requests — please slow down and try again'}), 429

    # ── Blueprints ───────────────────────────────────────────
    from api.auth import auth_bp
    from api.vehicles import vehicle_bp
    from api.services import service_bp
    from api.warranties import warranty_bp
    from api.uploads import upload_bp
    from api.sc_management import sc_bp
    from api.admin import admin_bp
    from api.notifications import notifications_bp

    app.register_blueprint(auth_bp,          url_prefix='/api/auth')
    app.register_blueprint(vehicle_bp,        url_prefix='/api/vehicle')
    app.register_blueprint(service_bp,        url_prefix='/api/service')
    app.register_blueprint(warranty_bp,       url_prefix='/api/warranty')
    app.register_blueprint(upload_bp,         url_prefix='/api/upload')
    app.register_blueprint(sc_bp,             url_prefix='/api/sc')
    app.register_blueprint(admin_bp,          url_prefix='/api/admin')
    app.register_blueprint(notifications_bp,  url_prefix='/api/notifications')

    # ── Health ───────────────────────────────────────────────
    @app.route('/api/health')
    def health():
        from blockchain.client import web3_client
        from sqlalchemy import text as _text

        blockchain_ok = False
        try:
            blockchain_ok = web3_client.w3.is_connected()
        except Exception:
            pass

        db_ok = False
        try:
            db.session.execute(_text('SELECT 1'))
            db_ok = True
        except Exception:
            pass

        status = 'healthy' if (blockchain_ok and db_ok) else 'degraded'
        code = 200 if db_ok else 503  # DB down means we can't serve requests
        return jsonify({
            'status': status,
            'db': {'ok': db_ok},
            'blockchain': {'connected': blockchain_ok},
        }), code

    # ── Keystore bootstrap ───────────────────────────────────
    from blockchain.keystore import keystore
    if Config.DEPLOYER_ADDRESS and Config.DEPLOYER_PRIVATE_KEY:
        keystore.store_key(Config.DEPLOYER_ADDRESS, Config.DEPLOYER_PRIVATE_KEY)

    # ── Blockchain event monitor ─────────────────────────────
    from blockchain.event_monitor import init_event_monitor
    monitor_thread = threading.Thread(target=init_event_monitor, args=(app,), daemon=True)
    monitor_thread.start()

    # ── Background scheduler (warranty reminders etc.) ───────
    from core.scheduler import init_scheduler
    init_scheduler(app)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
