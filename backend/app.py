from flask import Flask
from flask_cors import CORS
from config import Config
from db.models import db
import threading


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:4200",
                "http://localhost:3000",
                "http://192.168.*.*:*",
                "http://10.0.*.*:*"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    from api.auth import auth_bp
    from api.vehicles import vehicle_bp
    from api.services import service_bp
    from api.warranties import warranty_bp
    from api.uploads import upload_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(vehicle_bp, url_prefix='/api/vehicle')
    app.register_blueprint(service_bp, url_prefix='/api/service')
    app.register_blueprint(warranty_bp, url_prefix='/api/warranty')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')

    @app.route('/api/health')
    def health():
        from blockchain.client import web3_client
        try:
            connected = web3_client.w3.is_connected()
        except Exception:
            connected = False
        return {
            'status': 'healthy',
            'blockchain': {'connected': connected}
        }, 200

    from blockchain.keystore import keystore
    if Config.DEPLOYER_ADDRESS and Config.DEPLOYER_PRIVATE_KEY:
        keystore.store_key(Config.DEPLOYER_ADDRESS, Config.DEPLOYER_PRIVATE_KEY)

    from blockchain.event_monitor import init_event_monitor
    monitor_thread = threading.Thread(target=init_event_monitor, args=(app,), daemon=True)
    monitor_thread.start()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
