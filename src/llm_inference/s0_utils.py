import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from functools import lru_cache
from paths import PROMPTS_DIR
import json
import pandas as pd


@lru_cache(maxsize=None)
def load_prompt(filename: str, type) -> str:
    """
    Carrega o conteúdo de um prompt de um arquivo de texto.

    Args:
        filename: O nome do arquivo na pasta de prompts (ex: 'anderson_v1.txt').

    Returns:
        O conteúdo do arquivo como uma string.
    """
    try:
        if type == "h":
            from paths import HIERARCHICAL_PROMPTS_DIR
            file_path = HIERARCHICAL_PROMPTS_DIR / filename
        elif type == "f":
            from paths import FLAT_PROMPTS_DIR
            file_path = FLAT_PROMPTS_DIR / filename
        else:
            file_path = PROMPTS_DIR / filename
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(
            f"Erro: O arquivo de prompt '{filename}' não foi encontrado em '{PROMPTS_DIR}'.")
        raise


def load_json_data(filepath):
    """Loads data from a JSON file, supporting both standard and JSONL formats."""
    if not os.path.exists(filepath):
        print(f"Error: The file {filepath} was not found.")
        return []

    try:
        df = pd.read_json(filepath, lines=False)
    except (ValueError, TypeError):
        df = pd.read_json(filepath, lines=True)

    return df.to_dict('records')


def combine_hier_codes(detection_path, code_type_path, output_path):
    """
    Combina os resultados de 'detection' e 'code_type' e salva em um arquivo,
    fazendo o match das linhas por 'site' e 'question_id'.

    Lê dois arquivos JSON Lines, um contendo detecções de misuse (`detection`) e outro
    contendo a classificação desses misuses (`code_type`). Ele faz o merge das informações
    com base no `code_index` para as linhas que possuem o mesmo `site` e `question_id`,
    e salva o resultado em um novo arquivo JSON Lines.
    """
    # Carrega os dados de code_type em um dicionário para busca eficiente
    code_type_map = {}
    with open(code_type_path, 'r', encoding='utf-8') as f_type:
        for line_str in f_type:
            try:
                line_data = json.loads(line_str)
                # Lida com JSON aninhado que foi salvo como string
                if isinstance(line_data, str):
                    line_data = json.loads(line_data)
                
                site = line_data.get('site')
                question_id = line_data.get('question_id')
                if site and question_id:
                    code_type_map[(site, question_id)] = line_data
            except (json.JSONDecodeError, TypeError):
                # Pula linhas que não são JSON válido
                continue

    # Processa o arquivo de detecção e faz o merge com os dados de code_type
    with open(detection_path, 'r', encoding='utf-8') as f_det, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        for det_line_str in f_det:
            try:
                det_line = json.loads(det_line_str)
                # Lida com JSON aninhado que foi salvo como string
                if isinstance(det_line, str):
                    det_line = json.loads(det_line)

                det_site = det_line.get('site')
                det_question_id = det_line.get('question_id')
                
                # Encontra a linha correspondente em code_type
                type_line = code_type_map.get((det_site, det_question_id))

                if type_line:
                    type_misuses = type_line.get('misuses', [])
                    type_misuses_map = {}
                    if isinstance(type_misuses, list):
                        type_misuses_map = {
                            misuse['code_index']: misuse 
                            for misuse in type_misuses 
                            if isinstance(misuse, dict) and 'code_index' in misuse
                        }

                    det_misuses = det_line.get('misuses')
                    if isinstance(det_misuses, list):
                        for det_misuse in det_misuses:
                            if not isinstance(det_misuse, dict):
                                continue
                            
                            code_index = det_misuse.get('code_index')
                            if code_index in type_misuses_map:
                                type_misuse = type_misuses_map[code_index]

                                # Adiciona 'categories' e 'subtypes'
                                det_misuse['categories'] = type_misuse.get('categories')
                                det_misuse['subtypes'] = type_misuse.get('subtypes')

                                # Calcula a média da 'confidence'
                                det_confidence = det_misuse.get('confidence', 0)
                                type_confidence = type_misuse.get('confidence', 0)
                                det_misuse['confidence'] = (det_confidence + type_confidence) / 2
                
                # Escreve a linha de detecção (modificada ou não) no arquivo de saída
                f_out.write(json.dumps(det_line) + '\n')
            except (json.JSONDecodeError, TypeError):
                # Se a linha de detecção for inválida, pula para a próxima
                continue
