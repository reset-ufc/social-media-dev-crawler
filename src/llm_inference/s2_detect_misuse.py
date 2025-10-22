import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
import pandas as pd
import json
from tqdm import tqdm
from paths import *
from s1_make_llm_input import *
from s0_prompts import *
import re

load_dotenv()


def get_processed_ids(filepath: Path) -> set:
    """Lê um arquivo JSON e retorna um conjunto de IDs já processados."""
    if not filepath.exists():
        return set()

    processed = set()
    try:
        content = filepath.read_text(encoding='utf-8')
        if not content.strip():
            return processed

        # Tentativa direta: carregar como JSON completo
        try:
            data = json.loads(content)
            for item in data:
                # Tenta obter o ID do novo local 'meta.post_id' ou do antigo 'id' para retrocompatibilidade.
                item_id = item.get('meta', {}).get('post_id') or item.get('id')
                if isinstance(item, dict) and item_id:
                    processed.add(str(item_id))
            return processed
        except json.JSONDecodeError:
            # Fallback: extrair objetos JSON individuais usando um scanner
            # que procura chaves balanceadas, para lidar com objetos aninhados.
            s = content
            idx = 0
            length = len(s)
            while idx < length:
                # procura início de objeto
                start = s.find('{', idx)
                if start == -1:
                    break
                depth = 0
                i = start
                while i < length:
                    if s[i] == '{':
                        depth += 1
                    elif s[i] == '}':
                        depth -= 1
                        if depth == 0:
                            # extraimos o objeto completo
                            obj_str = s[start:i+1]
                            try:
                                obj = json.loads(obj_str)
                                item_id = obj.get('meta', {}).get('post_id') or obj.get('id')
                                if isinstance(obj, dict) and item_id:
                                    processed.add(str(item_id))
                            except Exception:
                                pass
                            idx = i + 1
                            break
                    i += 1
                else:
                    # objeto truncado no final do arquivo
                    break
            return processed
    except Exception:
        return processed


def extract_objects_from_file(filepath: Path) -> list:
    """Extrai todos os objetos JSON válidos do arquivo, mesmo que o arquivo esteja truncado
    ou não seja um array JSON válido. Retorna uma lista de dicts para os objetos parseáveis."""
    objs = []
    try:
        content = filepath.read_text(encoding='utf-8')
        if not content.strip():
            return objs

        # Tentativa direta
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        objs.append(item)
            return objs
        except json.JSONDecodeError:
            s = content
            idx = 0
            length = len(s)
            while idx < length:
                start = s.find('{', idx)
                if start == -1:
                    break
                depth = 0
                i = start
                while i < length:
                    if s[i] == '{':
                        depth += 1
                    elif s[i] == '}':
                        depth -= 1
                        if depth == 0:
                            obj_str = s[start:i+1]
                            try:
                                obj = json.loads(obj_str)
                                if isinstance(obj, dict):
                                    objs.append(obj)
                            except Exception:
                                pass
                            idx = i + 1
                            break
                    i += 1
                else:
                    break
            return objs
    except Exception:
        return objs


def detect_misuse_post(llm, limit=0):
    """
    Função principal para processar posts, detectar usos indevidos de criptografia
    e salvar os resultados.
    """

    print(f"Iniciando detecção de uso indevido [POSTS].")

    input_path = PREPROCESSED_POSTS
    if not input_path.exists():
        print(f"Erro: Arquivo de entrada não encontrado em '{input_path}'.")
        return

    print(f"Carregando posts de: {input_path}")
    df = pd.read_csv(input_path, dtype={'id': str, 'question_id': str})

    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        hier_v1()
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    output_path = MISUSE_CASES_POSTS
    questions_df = df[df['type'] == 'question'].copy()

    # Se existir um arquivo antigo, tentamos normalizá-lo (por exemplo, quando
    # o conteúdo é uma sequência de objetos sem um array envolvendo). Isso evita
    # que objetos válidos não sejam detectados como processados.
    if output_path.exists():
        objs = extract_objects_from_file(output_path)
        if objs:
            # deduplicamos por id e reescrevemos como um array JSON válido
            seen = set()
            unique = []
            for o in objs:
                oid = str(o.get('id')) if o.get('id') is not None else None
                if oid and oid not in seen:
                    seen.add(oid)
                    unique.append(o)
            try:
                output_path.write_text(json.dumps(
                    unique, ensure_ascii=False, indent=4), encoding='utf-8')
            except Exception:
                # Se falhar ao reescrever, seguimos sem normalizar
                pass

    processed_ids = get_processed_ids(output_path)

    if processed_ids:
        print(
            f"Retomando. {len(processed_ids)} posts já processados foram encontrados.")
        questions_df = questions_df[~questions_df['id'].astype(
            str).isin(processed_ids)]

    if limit > 0:
        questions_df = questions_df.head(limit)
        print(
            f"Aplicando limite: os próximos {limit} posts serão processados.")
    
    total = len(questions_df)
    print(
        f"Processando {total} posts com o LLM. Isso pode levar um tempo...")
    print(f"Os resultados serão salvos em tempo real em: {output_path}")

    processed_count = 0

    # Garantir que o arquivo exista; se não existir, criamos um array vazio
    if not output_path.exists():
        output_path.write_text('[\n]\n', encoding='utf-8')

    # Antes de anexar, removemos o ']' final e qualquer whitespace imediato para permitir append seguro
    try:
        with open(output_path, 'r+b') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            # Lemos até os últimos 2048 bytes para localizar o ']' final
            read_back = min(size, 2048)
            f.seek(size - read_back)
            tail = f.read().decode('utf-8', errors='ignore')
            # Procuramos a última ']' e truncamos a partir dela
            last_bracket = tail.rfind(']')
            if last_bracket != -1:
                trunc_pos = size - (read_back - last_bracket)
                f.truncate(trunc_pos)
            # Depois de truncar, determinamos se há já objetos presentes
            f.seek(0, os.SEEK_END)
            end_pos = f.tell()
            f.seek(max(0, end_pos - 1024))
            seg = f.read().decode('utf-8', errors='ignore')
            has_objects = '{' in seg and seg.strip()[-1] != '['
    except Exception as e:
        print(f"Aviso ao preparar arquivo de saída: {e}")
        has_objects = False

    # Agora abrimos em append para escrever novos objetos
    first_write = not has_objects
    with open(output_path, 'a', encoding='utf-8') as f:
        for _, row in tqdm(questions_df.iterrows(), total=total, desc="Analisando Posts"):
            try:
                post_id = str(row['id'])
                post_content = post_analyze_string(post_id)
                metadata_content = get_post_metadata(post_id)
                response = chain.invoke({
                    "metadata": metadata_content,
                    "post": post_content
                })

                # Adiciona metadados ao resultado
                response['id'] = post_id
                response.setdefault('meta', {})
                response['meta']['post_id'] = post_id
                response['meta']['site'] = str(row['site'])

                serialized = json.dumps(response, ensure_ascii=False, indent=4)

                if not first_write:
                    f.write(',\n')
                else:
                    first_write = False

                f.write(serialized)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    # fsync pode falhar em alguns ambientes; não é crítico
                    pass
                processed_count += 1

            except OutputParserException as e:
                print(
                    f"Erro de parsing na resposta do LLM para o post ID {row['id']}: {e}")
            except Exception as e:
                print(
                    f"Erro inesperado ao processar o post ID {row['id']}: {e}")

    # Finalmente, adicionamos o fechamento do array
    try:
        with open(output_path, 'a', encoding='utf-8') as f:
            f.write('\n]\n')
    except Exception:
        print('Aviso: não foi possível adicionar o fechamento final do arquivo JSON.')
    print(
        f"\nProcessamento concluído. {processed_count} resultados foram gerados e salvos.")


def detect_misuse_code(llm, limit=0):
    print(f"Iniciando detecção de uso indevido [CODIGOS].")

    input_path = PREPROCESSED_POSTS
    if not input_path.exists():
        print(f"Erro: Arquivo de entrada não encontrado em '{input_path}'.")
        return

    print(f"Carregando posts de: {input_path}")
    df = pd.read_csv(input_path, dtype={'id': str, 'question_id': str})

    parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_template(
        hierarquical_in_code_v1()
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt_template | llm | parser

    output_path = MISUSE_CASES_CODES
    questions_df = df[df['type'] == 'question'].copy()

    # Se existir um arquivo antigo, tentamos normalizá-lo (por exemplo, quando
    # o conteúdo é uma sequência de objetos sem um array envolvendo). Isso evita
    # que objetos válidos não sejam detectados como processados.
    if output_path.exists():
        objs = extract_objects_from_file(output_path)
        if objs:
            # deduplicamos por id e reescrevemos como um array JSON válido
            seen = set()
            unique = []
            for o in objs:
                oid = str(o.get('id')) if o.get('id') is not None else None
                if oid and oid not in seen:
                    seen.add(oid)
                    unique.append(o)
            try:
                output_path.write_text(json.dumps(
                    unique, ensure_ascii=False, indent=4), encoding='utf-8')
            except Exception:
                # Se falhar ao reescrever, seguimos sem normalizar
                pass

    processed_ids = get_processed_ids(output_path)

    if processed_ids:
        print(
            f"Retomando. {len(processed_ids)} posts já processados foram encontrados.")
        questions_df = questions_df[~questions_df['id'].astype(
            str).isin(processed_ids)]

    if limit > 0:
        questions_df = questions_df.head(limit)
        print(
            f"Aplicando limite: os próximos {limit} posts serão processados.")

    total = len(questions_df)
    print(
        f"Processando {total} posts com o LLM. Isso pode levar um tempo...")
    print(f"Os resultados serão salvos em tempo real em: {output_path}")

    processed_count = 0

    # Garantir que o arquivo exista; se não existir, criamos um array vazio
    if not output_path.exists():
        output_path.write_text('[\n]\n', encoding='utf-8')

    # Antes de anexar, removemos o ']' final e qualquer whitespace imediato para permitir append seguro
    try:
        with open(output_path, 'r+b') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            # Lemos até os últimos 2048 bytes para localizar o ']' final
            read_back = min(size, 2048)
            f.seek(size - read_back)
            tail = f.read().decode('utf-8', errors='ignore')
            # Procuramos a última ']' e truncamos a partir dela
            last_bracket = tail.rfind(']')
            if last_bracket != -1:
                trunc_pos = size - (read_back - last_bracket)
                f.truncate(trunc_pos)
            # Depois de truncar, determinamos se há já objetos presentes
            f.seek(0, os.SEEK_END)
            end_pos = f.tell()
            f.seek(max(0, end_pos - 1024))
            seg = f.read().decode('utf-8', errors='ignore')
            has_objects = '{' in seg and seg.strip()[-1] != '['
    except Exception as e:
        print(f"Aviso ao preparar arquivo de saída: {e}")
        has_objects = False

    # Agora abrimos em append para escrever novos objetos
    first_write = not has_objects
    with open(output_path, 'a', encoding='utf-8') as f:
        for _, row in tqdm(questions_df.iterrows(), total=total, desc="Analisando Codigos"):
            try:
                post_id = str(row['id'])
                codes = code_analyze_string(post_id)
                metadata_content = get_post_metadata(post_id)
                response = chain.invoke({
                    "post_metadata": metadata_content,
                    "codes": codes
                })
                # Adiciona metadados ao resultado
                response['id'] = post_id
                response.setdefault('meta', {})
                response['meta']['post_id'] = post_id
                response['meta']['site'] = str(row['site'])

                serialized = json.dumps(response, ensure_ascii=False, indent=4)

                if not first_write:
                    f.write(',\n')
                else:
                    first_write = False

                f.write(serialized)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    # fsync pode falhar em alguns ambientes; não é crítico
                    pass
                processed_count += 1

            except OutputParserException as e:
                print(
                    f"Erro de parsing na resposta do LLM para o post ID {row['id']}: {e}")
            except Exception as e:
                print(
                    f"Erro inesperado ao processar o post ID {row['id']}: {e}")

    # Finalmente, adicionamos o fechamento do array
    try:
        with open(output_path, 'a', encoding='utf-8') as f:
            f.write('\n]\n')
    except Exception:
        print('Aviso: não foi possível adicionar o fechamento final do arquivo JSON.')
    print(
        f"\nProcessamento concluído. {processed_count} resultados foram gerados e salvos.")


def ol(n):
    detect_misuse_code(
        ChatOllama(model="llama3.1:8b", temperature=0, format="json"),
        n
    )

def gp(n):    
    detect_misuse_code(
        ChatOpenAI(model='gpt-4.1-mini',
            temperature=0,
            model_kwargs={"response_format": {"type": "json_object"}}),
        n
    )

if __name__ == "__main__":
    ol(3)
