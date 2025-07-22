from pathlib import Path
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
from flatten_json import flatten
import time

# Credenciais
API_KEY = 'dPGwWbogKDfTche9BPr8qkJyFbX3iJmBMjtc'
APP_ID = '7de50ff0-0ffc-4677-ba20-29105fddecc1'

data_inicial = "2025-07-15"
data_fim = '2025-07-18'

pasta_producao = Path(r'C:\Users\campe\OneDrive\Documentos\dsa\dados\bases')
pasta_bases = pasta_producao / 'bases'
pasta_bases.mkdir(parents=True, exist_ok=True)

# Endpoint específico para ads
endpoint = {
    "base_url": "https://api-retail-media.newtail.com.br/ad/results/v2",
    "filename": "ads.csv",
    "name": "ads"
}

# Cabeçalho da API
headers = {
    'accept': 'application/json',
    'content-type': 'application/json',
    'x-api-key': API_KEY,
    'x-app-id': APP_ID
}

# Parâmetros de colunas desejadas para ads
colunas_ads = [
    "id", "campaign_id", "url", "settings_media_url", "settings_type", 
    "start_at", "created_at", "updated_at", "asset_type", "name", 
    "image_url", "campaign_name", "ad_type", "publisher_id", "publisher_name",
    "conversions_quantity", "advertiser_tags_0_label", "metrics_impressions", 
    "metrics_views", "metrics_clicks", "metrics_conversions", "metrics_income", 
    "metrics_adcost", "metrics_total_conversions_items_quantity", "categories_0",
    "reference_date"  # Nova coluna para data de referência
]

# Lista para armazenar todos os dados
all_data = []

# Converter datas para objetos datetime
start_date = datetime.strptime(data_inicial, "%Y-%m-%d")
end_date = datetime.strptime(data_fim, "%Y-%m-%d")

print(f"🚀 Iniciando extração diária de ads de {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")

# Loop por cada dia no intervalo
current_date = start_date
while current_date <= end_date:
    day_str = current_date.strftime("%Y-%m-%d")
    print(f"\n📅 Processando dia: {day_str}")
    
    page = 1
    quantity = 100
    has_more = True
    
    # Obter total de registros para o dia
    count_url = f"{endpoint['base_url']}?start_date={day_str}&end_date={day_str}&page=1&quantity=1&count=true"
    try:
        count_resp = requests.get(count_url, headers=headers)
        count_resp.raise_for_status()
        count_data = count_resp.json()
        
        # Capturar total_count
        total_count = count_data.get("total_count")
        if not total_count:
            total_count = next((v for k, v in count_data.items() if "total" in k.lower() and isinstance(v, int)), 0)
        
        if total_count == 0:
            print(f"  ⏩ Nenhum registro encontrado para {day_str}")
            current_date += timedelta(days=1)
            continue
            
        total_pages = (total_count // quantity) + (1 if total_count % quantity else 0)
        print(f"  🔢 Total de registros: {total_count} | Páginas: {total_pages}")
        
    except Exception as e:
        print(f"  ❌ Erro ao obter contagem para {day_str}: {e}")
        current_date += timedelta(days=1)
        continue
    
    # Coletar dados paginados para o dia
    day_data = []
    while page <= total_pages and has_more:
        url = f"{endpoint['base_url']}?start_date={day_str}&end_date={day_str}&page={page}&quantity={quantity}"
        
        try:
            resp = requests.get(url, headers=headers)
            
            # Tratar rate limit
            if resp.status_code == 429:
                retry_after = int(resp.headers.get('Retry-After', 60))
                print(f"  ⚠️ Rate limit atingido. Aguardando {retry_after} segundos...")
                time.sleep(retry_after)
                continue
                
            resp.raise_for_status()
            data = resp.json()
            
            # Identificar lista de dados
            data_values = None
            if isinstance(data, dict):
                # Tentar encontrar a lista de resultados
                data_values = next((v for v in data.values() if isinstance(v, list)), None)
            elif isinstance(data, list):
                data_values = data
                
            if not data_values:
                print(f"  ⚠️ Página {page} não retornou dados.")
                has_more = False
                break
                
            # Adicionar data de referência a cada item
            for item in data_values:
                item['reference_date'] = day_str
            
            day_data.extend(data_values)
            print(f"  ✅ Página {page}/{total_pages} carregada ({len(data_values)} itens)")
            page += 1
            
            # Delay para evitar rate limit
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ❌ Erro na página {page}: {e}")
            has_more = False
            break
    
    all_data.extend(day_data)
    print(f"  📊 Total do dia: {len(day_data)} registros")
    
    # Avançar para o próximo dia
    current_date += timedelta(days=1)

# Salvar dados completos
if all_data:
    # Salvar JSON
    json_path = pasta_bases / endpoint["filename"].replace(".csv", ".json")
    with open(json_path, 'w', encoding='utf-8') as f_json:
        json.dump(all_data, f_json, ensure_ascii=False, indent=2)
    
    # Salvar CSV
    flattened = [flatten(item) for item in all_data]
    df = pd.DataFrame(flattened)
    
    # Filtrar colunas desejadas
    df = df[[c for c in colunas_ads if c in df.columns]]
    
    csv_path = pasta_bases / endpoint["filename"]
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    
    print(f"\n Extração concluída com sucesso!")
    print(f"   - Total de registros: {len(all_data)}")
    print(f"   - JSON salvo em: {json_path}")
    print(f"   - CSV salvo em: {csv_path}")
else:
    print("\n Nenhum dado foi coletado no período especificado")