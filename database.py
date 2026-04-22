import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

# Garante que as variáveis de ambiente sejam lidas
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

host_atual = os.getenv('DB_HOST')
print(f"Tentando conectar no host: {host_atual}")

# 1. Empacota as credenciais usando as variáveis do .env
dbconfig = {
    "host": os.getenv('DB_HOST'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_NAME')
}

# 2. Cria a "piscina" de conexões globais
try:
    conexao_pool = pooling.MySQLConnectionPool(
        pool_name="advocacia_pool",
        pool_size=5,
        pool_reset_session=True,
        **dbconfig
    )
    print("Banco de Dados: Connection Pool criado com sucesso!")
except mysql.connector.Error as err:
    print(f"Erro ao criar o pool de conexões: {err}")

# 3. A função que empresta as conexões (que será usada por todas as rotas)
def get_db_connection():
    try:
        return conexao_pool.get_connection()
    except mysql.connector.Error as err:
        print(f"Falha ao obter conexão do pool: {err}")
        raise