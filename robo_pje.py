import requests
import os
from datetime import datetime

# --- CONFIGURAÇÕES DO SEU SERVIDOR NA NUVEM ---
URL_ORACLE = "http://132.145.142.209/api/salvar_pje"
TOKEN_SECRETO = "APIchatadogov123@" # A mesma que você colocou no .env da Oracle

# --- CONFIGURAÇÕES DA BUSCA NO PJE ---
OAB_NUMERO = "143956"
HOJE = datetime.now().strftime("%Y-%m-%d")

def buscar_e_enviar():
    print(f"[{datetime.now()}] Iniciando busca de intimações para OAB {OAB_NUMERO}...")
    
    # 1. Bate na porta do PJE usando sua internet de casa
    url_pje = f"https://comunicaapi.pje.jus.br/api/v1/comunicacao?dataDisponibilizacaoInicio={HOJE}&dataDisponibilizacaoFim={HOJE}&numeroOab={OAB_NUMERO}"
    
    headers_pje = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response_pje = requests.get(url_pje, headers=headers_pje)
        
        if response_pje.status_code == 200:
            dados_pje = response_pje.json()
            items = dados_pje.get('items', [])
            print(f"Encontradas {len(items)} comunicações.")

            # 2. Para cada comunicação encontrada, manda via "Sedex" para a Oracle
            for item in items:
                # Preparamos o pacote para a sua API
                pacote = {
                    "numero": item.get('numero_processo', 'Número não informado'),
                    "texto": item.get('texto_comunicacao', 'Conteúdo não disponível'),
                    "orgao": item.get('siglaTribunal', item.get('nomeOrgao', 'Não informado')),
                    "classe": item.get('classe_processual', item.get('classeProcessual', 'Não informado')),
                    "tipo": item.get('tipoComunicacao', item.get('tipo_comunicacao', 'Não informado'))
                }
                
                headers_oracle = {
                    "Authorization": f"Bearer {TOKEN_SECRETO}",
                    "Content-Type": "application/json"
                }

                envio = requests.post(URL_ORACLE, json=pacote, headers=headers_oracle)
                
                if envio.status_code == 200:
                    print(f"Processo {pacote['numero']} enviado com sucesso para a nuvem!")
                else:
                    print(f"Erro ao enviar para a Oracle: {envio.status_code} - {envio.text}")
        
        else:
            print(f"Erro ao acessar PJE: {response_pje.status_code}")

    except Exception as e:
        print(f"Falha crítica no robô: {e}")

if __name__ == "__main__":
    buscar_e_enviar()