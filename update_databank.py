import os
import mysql.connector
from dotenv import load_dotenv

# Carrega as senhas do seu .env
load_dotenv()

print("Conectando ao banco de dados...")

try:
    # Usa as mesmas credenciais do seu app.py
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME') # Deve apontar para o advocaica_digital
    )
    cursor = conn.cursor()

    print("Lendo o arquivo schema.sql...")
    with open('schema.sql', 'r', encoding='utf-8') as f:
        sql_file = f.read()

    print("Executando os comandos...")
    # O multi=True permite rodar vários comandos SQL de uma vez
    for result in cursor.execute(sql_file, multi=True):
        if result.with_rows:
            result.fetchall()

    conn.commit()
    print("✅ Tabelas criadas/atualizadas com sucesso!")

except mysql.connector.Error as err:
    print(f"❌ Erro no banco de dados: {err}")
except Exception as e:
    print(f"❌ Erro genérico: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals() and conn.is_connected():
        conn.close()