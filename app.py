from flask import Flask, send_from_directory
from models.database import init_db
from routes.auth import auth_bp
from routes.student import student_bp
from routes.hod import hod_bp
from routes.warden import warden_bp
from routes.security import security_bp
from seed_data import seed
import config

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = config.SECRET_KEY

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(hod_bp)
app.register_blueprint(warden_bp)
app.register_blueprint(security_bp)


# Serve HTML pages
@app.route('/')
def index():
    return send_from_directory('templates', 'login.html')


@app.route('/student')
def student_page():
    return send_from_directory('templates', 'student.html')


@app.route('/hod')
def hod_page():
    return send_from_directory('templates', 'hod.html')


@app.route('/warden')
def warden_page():
    return send_from_directory('templates', 'warden.html')


@app.route('/security')
def security_page():
    return send_from_directory('templates', 'security.html')


if __name__ == '__main__':
    init_db()
    seed()
    print("\n[*] Server running at http://localhost:5000")
    print("[*] Login page: http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
