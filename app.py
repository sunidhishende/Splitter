from flask import Flask
from backend.config import Config
from backend.db import db
from backend.migrate import migrate
from backend.websocket import socketio
from backend.api.groups import bp as groups_bp
from backend.api.transactions import bp as transactions_bp
from backend.api.payments import bp as payments_bp
from flask_cors import CORS
def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    
    app.register_blueprint(groups_bp, url_prefix='/api')
    app.register_blueprint(transactions_bp, url_prefix='/api')
    app.register_blueprint(payments_bp, url_prefix='/api')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
