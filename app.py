from flask import Flask, jsonify

from api import user_bp, email_bp, file_bp, agent_bp, route_bp, roleplay_bp, admin_bp, roleplay_admin_bp
from config import Config
from models import db

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# 注册蓝图
app.register_blueprint(user_bp)
app.register_blueprint(email_bp)
app.register_blueprint(file_bp)
app.register_blueprint(agent_bp)
app.register_blueprint(route_bp)
app.register_blueprint(roleplay_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(roleplay_admin_bp)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})


@app.cli.command('init-db')
def init_db():
    """Initialize the database tables."""
    with app.app_context():
        db.create_all()
        print('Database tables created successfully.')


if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.FLASK_DEBUG)
