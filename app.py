import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

# Nossas importações modulares
from database import get_db_connection
from forms import LoginForm

# Blueprints
from routes.pessoas import pessoas_bp
from routes.processos import processos_bp
from routes.tarefas import tarefas_bp
from routes.documentos import documentos_bp
from routes.pje import pje_bp

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Registrando os Módulos
app.register_blueprint(pessoas_bp)
app.register_blueprint(processos_bp)
app.register_blueprint(tarefas_bp)
app.register_blueprint(documentos_bp)
app.register_blueprint(pje_bp)

# Configurações de Upload globais para o app inteiro saber
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- LOGIN MANAGER ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"

class User(UserMixin):
    def __init__(self, id, email, password):
        self.id = id
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            return User(id=user_data['id'], email=user_data['email'], password=user_data['password'])
        return None
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (form.email.data,))
            user_data = cursor.fetchone()
            
            if user_data and check_password_hash(user_data['password'], form.password.data):
                user = User(id=user_data['id'], email=user_data['email'], password=user_data['password'])
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Login inválido. Verifique seu e-mail e senha.', 'danger')
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals() and conn.is_connected(): conn.close()
            
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'success')
    return redirect(url_for('login'))

# --- DASHBOARD CENTRAL ---
@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT DATE(data_geracao) as dia, COUNT(*) as total 
        FROM peticoes_geradas
        WHERE data_geracao >= CURDATE() - INTERVAL 30 DAY
        GROUP BY DATE(data_geracao)
        ORDER BY dia ASC
        """
        cursor.execute(query)
        peticoes_data = cursor.fetchall()
        
        labels = [dia['dia'].strftime('%d/%m') for dia in peticoes_data]
        data = [dia['total'] for dia in peticoes_data]
        chart_data = {'labels': labels, 'data': data}
        
        return render_template('index.html', chart_data=chart_data)
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG') == '1')