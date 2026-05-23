from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from db.models import db
from extensions import limiter
import threading


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        db.create_all()

    CORS(app, resources={
        r'/api/*': {
            'origins': [
                'http://localhost:4200',
                'http://localhost:3000',
                'http://192.168.*.*:*',
                'http://10.0.*.*:*',
            ],
            'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            'allow_headers': ['Content-Type', 'Authorization'],
            'supports_credentials': True,
        }
    })

    # ── Security headers ─────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        # CSP — tightened for API-only service (no HTML served)
        response.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'"
        # HSTS — enable once HTTPS is in place (commented out for local dev)
        # response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
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

    app.register_blueprint(auth_bp,    url_prefix='/api/auth')
    app.register_blueprint(vehicle_bp, url_prefix='/api/vehicle')
    app.register_blueprint(service_bp, url_prefix='/api/service')
    app.register_blueprint(warranty_bp, url_prefix='/api/warranty')
    app.register_blueprint(upload_bp,  url_prefix='/api/upload')
    app.register_blueprint(sc_bp,      url_prefix='/api/sc')

    # ── Health ───────────────────────────────────────────────
    @app.route('/api/health')
    def health():
        from blockchain.client import web3_client
        try:
            connected = web3_client.w3.is_connected()
        except Exception:
            connected = False
        return {'status': 'healthy', 'blockchain': {'connected': connected}}, 200

    # ── Keystore bootstrap ───────────────────────────────────
    from blockchain.keystore import keystore
    if Config.DEPLOYER_ADDRESS and Config.DEPLOYER_PRIVATE_KEY:
        keystore.store_key(Config.DEPLOYER_ADDRESS, Config.DEPLOYER_PRIVATE_KEY)

    # ── Blockchain event monitor ─────────────────────────────
    from blockchain.event_monitor import init_event_monitor
    monitor_thread = threading.Thread(target=init_event_monitor, args=(app,), daemon=True)
    monitor_thread.start()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
