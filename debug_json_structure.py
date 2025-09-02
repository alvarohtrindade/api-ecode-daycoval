import json
import pprint

def analyze_json_structure(json_file_path: str):
    """Analisa a estrutura do JSON para identificar o problema"""
    
    print(f"Analisando arquivo: {json_file_path}")
    print("="*60)
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            json_data = json.load(file)
        
        print(f"Tipo do objeto raiz: {type(json_data)}")
        
        if isinstance(json_data, dict):
            print(f"Chaves do objeto raiz: {list(json_data.keys())}")
            
            # Analisa campo 'data' se existir
            if 'data' in json_data:
                data = json_data['data']
                print(f"\nTipo do campo 'data': {type(data)}")
                
                if isinstance(data, list):
                    print(f"Tamanho da lista 'data': {len(data)}")
                    if len(data) > 0:
                        print(f"Tipo do primeiro item: {type(data[0])}")
                        if isinstance(data[0], dict):
                            print(f"Chaves do primeiro item: {list(data[0].keys())}")
                        else:
                            print(f"Primeiro item: {data[0]}")
                elif isinstance(data, dict):
                    print(f"Chaves do objeto 'data': {list(data.keys())}")
            
            # Mostra estrutura completa (limitada)
            print("\nEstrutura completa (primeiros 2 níveis):")
            pprint.pprint(json_data, depth=2)
            
        elif isinstance(json_data, list):
            print(f"JSON é uma lista com {len(json_data)} itens")
            if len(json_data) > 0:
                print(f"Tipo do primeiro item: {type(json_data[0])}")
                if isinstance(json_data[0], dict):
                    print(f"Chaves do primeiro item: {list(json_data[0].keys())}")
        
        else:
            print(f"Tipo inesperado: {type(json_data)}")
            print(f"Conteúdo: {json_data}")
    
    except Exception as e:
        print(f"Erro ao analisar JSON: {e}")

if __name__ == "__main__":
    json_file = r'C:\Users\atrindade\catalise\DataAnalytics\backend\apis\daycoval\output\EXTRATO_DAYCOVAL_JULHO.json'
    analyze_json_structure(json_file)