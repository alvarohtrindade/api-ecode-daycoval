import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

try:
    connection = mysql.connector.connect(
        host=os.getenv('AURORA_HOST'),
        port=int(os.getenv('AURORA_PORT', 3306)),
        user=os.getenv('AURORA_USER'),
        password=os.getenv('AURORA_PASSWORD'),
        database=os.getenv('AURORA_DATABASE', 'DW_DESENV')
    )
    
    cursor = connection.cursor()
    
    # Teste 1: Contar registros
    cursor.execute("SELECT COUNT(*) FROM CADFUN")
    total = cursor.fetchone()[0]
    print(f"✅ Total registros CADFUN: {total}")
    
    # Teste 2: Ver algumas amostras
    cursor.execute("""
    SELECT ID_FUNDO_CUSTODIANTE, NOME_FUNDO 
    FROM CADFUN 
    WHERE ID_FUNDO_CUSTODIANTE IS NOT NULL 
    LIMIT 10
    """)
    
    for row in cursor.fetchall():
        print(f"ID: {row[0]} | Nome: {row[1]}")
    
    cursor.close()
    connection.close()
    print("✅ Conexão Aurora funcionando!")
    
except Exception as e:
    print(f"❌ Erro: {e}")