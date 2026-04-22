import os
import mysql.connector
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

def add_user():
    """
    Adiciona um novo usuário ao banco de dados de forma interativa.
    """
    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        cursor = conn.cursor()

        print("--- Adicionar Novo Usuário ---")
        email = input("Digite o e-mail do usuário: ")
        password = input("Digite a senha do usuário: ")

        if not email or not password:
            print("E-mail e senha não podem ser vazios.")
            return

        # Gera o hash da senha
        hashed_password = generate_password_hash(password)

        # Insere o novo usuário no banco de dados
        query = "INSERT INTO users (email, password) VALUES (%s, %s)"
        cursor.execute(query, (email, hashed_password))
        
        conn.commit()
        
        print(f"\nUsuário '{email}' adicionado com sucesso!")

    except mysql.connector.Error as err:
        print(f"Erro de banco de dados: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    add_user()