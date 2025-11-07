import sys
import os
import re
import html
import csv
import pandas as pd
from collections import Counter
from tqdm import tqdm
from typing import List, Tuple, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tree_sitter import Parser
from tree_sitter_languages import get_language
from utils_global import get_logger, ensure_parent_dir
from paths import *

logger = get_logger(__name__)

# ==========================================================
# === CONFIGURAÇÃO DO VALIDADOR DE CÓDIGO ===================
# ==========================================================

COMMON_LANGUAGES: List[str] = [
    # Principais & Comuns
    'python', 'javascript', 'java', 'c', 'cpp', 'c_sharp', 'go', 'rust', 'ruby', 'php', 'typescript',
]


# Palavras comuns para filtro de linguagem natural
PORTUGUESE_COMMON_WORDS = {
    "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não", "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu", "sua", "ou", "ser", "quando", "muito", "há", "nos", "já", "está", "eu", "também", "só", "pelo", "pela", "até", "isso", "ela", "entre", "era", "depois", "sem", "mesmo", "aos", "ter", "seus", "quem", "nas", "me", "esse", "eles", "estão", "você", "tinha", "foram", "essa", "num", "nem", "suas", "meu", "às", "minha", "numa", "pelos", "elas", "havia", "seja", "qual", "será", "nós", "tenho", "lhe", "deles", "essas", "esses", "pelas", "este", "fosse", "dele", "tu", "te", "vocês", "vos", "lhes", "meus", "minhas", "teu", "tua", "teus", "tuas", "nosso", "nossa", "nossos", "nossas", "dela", "delas", "esta", "estes", "estas", "aquele", "aquela", "aqueles", "aquelas", "isto", "aquilo", "estou", "estamos", "estive", "esteve", "estivemos", "estiveram", "estava", "estávamos", "estavam", "estivera", "estivéramos", "esteja", "estejamos", "estejam", "estivesse", "estivéssemos", "estivessem", "estiver", "estivermos", "estiverem", "hei", "há", "havemos", "hão", "houve", "houvemos", "houveram", "houvera", "houvéramos", "haja", "hajamos", "hajam", "houvesse", "houvéssemos", "houvessem", "houver", "houvermos", "houverem", "sou", "somos", "são", "éramos", "eram", "fui", "fomos", "foram", "fora", "fôramos", "seja", "sejamos", "sejam", "fosse", "fôssemos", "fossem", "for", "formos", "forem"
}
ENGLISH_COMMON_WORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know", "take", "people", "into", "year", "your", "good", "some", "could", "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over", "think", "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us"
}
ALL_COMMON_WORDS = PORTUGUESE_COMMON_WORDS.union(ENGLISH_COMMON_WORDS)

# ==========================================================
# === LÓGICA DE VALIDAÇÃO ==================================
# ==========================================================

def _tree_has_errors(node) -> bool:
    """Percorre recursivamente a árvore para encontrar nós de erro."""
    if node.type == "ERROR":
        return True
    return any(_tree_has_errors(child) for child in node.children)

def _has_meaningful_structure(root) -> bool:
    """Verifica se a árvore contém nós que indicam código real."""
    meaningful_nodes = {
        "function_definition", "method_definition", "class_definition",
        "assignment", "variable_declaration", "call_expression",
        "if_statement", "for_statement", "while_statement",
        "return_statement", "block", "statement"
    }
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type in meaningful_nodes:
            return True
        stack.extend(node.children)
    return False

def validate_code_block(code_text: str) -> Dict[str, Any]:
    """
    Analisa um bloco de texto e o valida como código de programação real.
    Retorna um dicionário com 'classification', 'language' e 'reason'.
    """
    # 1) Pré-processamento
    text = html.unescape(code_text).strip()
    if not text:
        return {"classification": "invalid", "language": None, "reason": "empty or whitespace block"}

    # 2) Filtro de Linguagem Natural
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    if words:
        natural_word_count = sum(1 for word in words if word in ALL_COMMON_WORDS)
        natural_ratio = natural_word_count / len(words)
        if natural_ratio > 0.55:
            return {"classification": "invalid", "language": None, "reason": "predominance of natural language"}

    # 3) Verificação Sintática com Tree-Sitter
    code_bytes = text.encode('utf-8')
    for lang_name in COMMON_LANGUAGES:
        try:
            language = get_language(lang_name)
            parser = Parser()
            parser.set_language(language)
            tree = parser.parse(code_bytes)
            root = tree.root_node

            # Regra: Parse sem nós de ERRO
            if _tree_has_errors(root):
                continue

            # Regra: Parse deve cobrir 100% do input
            if not (root.start_byte == 0 and root.end_byte == len(code_bytes)):
                continue

            # 4) Verificação de Estrutura de Código Real
            if _has_meaningful_structure(root):
                return {
                    "classification": "valid",
                    "language": lang_name,
                    "reason": "parse complete and structural nodes present"
                }
        except Exception:
            continue  # Ignora erros na configuração do parser

    # 5) Resultado Final (se nenhuma linguagem corresponder)
    return {"classification": "invalid", "language": None, "reason": "parse partial or absence of structural nodes"}

# ==========================================================
# === FUNÇÕES DE LIMPEZA E EXTRAÇÃO ========================
# ==========================================================

def clean_text(text: str) -> str:
    """Limpa HTML, preservando blocos <code>."""
    if not isinstance(text, str):
        return ""
    text = html.unescape(text)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p\s*>', '', text, flags=re.IGNORECASE)
    text = text.replace("\n", "\n")
    code_blocks = []
    def _preserve_code(match):
        code_blocks.append(match.group(0))
        return f"\n[[CODE_BLOCK_{len(code_blocks)-1}]]\n"
    text = re.sub(r'<code.*?>.*?</code>', _preserve_code, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    for i, block in enumerate(code_blocks):
        text = text.replace(f"[[CODE_BLOCK_{i}]]", block)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()

def extract_code_blocks(text: str) -> List[str]:
    """Extrai blocos <code> completos, incluindo as tags."""
    blocks = re.findall(r'(<code.*?>.*?</code>)', text, flags=re.DOTALL | re.IGNORECASE)
    return [re.sub(r'\r\n?', '\n', b).strip() for b in blocks]

def process_body_and_validate_code(text: str) -> Tuple[str, str, List[str], List[Dict[str, Any]]]:
    """
    Limpa o corpo do post, extrai blocos de código e os valida.
    Retorna o corpo limpo, código válido concatenado, blocos inválidos e os resultados da validação.
    """
    if not isinstance(text, str):
        return "", "", [], []

    cleaned_body = clean_text(text)
    full_blocks = extract_code_blocks(text)
    
    valid_code_parts = []
    invalid_blocks = []
    validation_results = []

    for block in full_blocks:
        content_match = re.search(r'<code.*?>(.*?)</code>', block, flags=re.DOTALL | re.IGNORECASE)
        content = content_match.group(1) if content_match else ""
        
        result = validate_code_block(content)
        validation_results.append(result)
        
        if result["classification"] == "valid":
            valid_code_parts.append(block)
        else:
            invalid_blocks.append(block)
            
    concatenated_valid_code = "\n\n".join(valid_code_parts)
    return cleaned_body, concatenated_valid_code, invalid_blocks, validation_results

# ==========================================================
# === PIPELINE PRINCIPAL ===================================
# ==========================================================

def main():
    logger.info(f"Carregando posts de: {FILTRED_POSTS}")
    try:
        df = pd.read_csv(FILTRED_POSTS, dtype=str)
    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {FILTRED_POSTS}")
        return

    is_question_mask = df['id'] == df['question_id']
    total_questions = len(df[is_question_mask])
    logger.info(f"Arquivo carregado. Total de perguntas (questions): {total_questions}")

    ensure_parent_dir(PREPROCESSED_POSTS)
    ensure_parent_dir(INVALID_CODES)
    invalid_path = str(INVALID_CODES)
    if not invalid_path.lower().endswith(".csv"):
        invalid_path += ".csv"

    valid_rows, invalid_rows = [], []
    all_results = []
    invalid_question_ids = set()

    logger.info("Iniciando pré-processamento e validação de código (S8)...")

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Validando blocos de código (s8)"):
        body = str(row.get('body', ''))
        cleaned_body, extracted_code, invalid_blocks, results = process_body_and_validate_code(body)
        all_results.extend(results)

        row_copy = row.copy()
        row_copy['body'] = cleaned_body
        row_copy['code'] = extracted_code

        # Create a summary of detected languages
        valid_languages = [res['language'] for res in results if res['classification'] == 'valid']
        if valid_languages:
            lang_counts = Counter(valid_languages)
            row_copy['languages'] = str(dict(lang_counts))
        else:
            row_copy['languages'] = None

        # A post is invalid ONLY if it contains code blocks, but NONE are valid.
        # Otherwise, it's considered valid, and its 'code' column will contain only the valid blocks.
        has_valid_blocks = extracted_code.strip() != ""
        has_invalid_blocks = len(invalid_blocks) > 0

        if has_invalid_blocks and not has_valid_blocks:
            invalid_question_ids.add(row.get("question_id", ""))
            preview = invalid_blocks[0]
            row_copy["invalid_block_preview"] = (preview[:1000] + "..." if len(preview) > 1000 else preview)
            invalid_rows.append(row_copy)
        else:
            # Post is valid if it has no code, only valid code, or a mix of valid and invalid code.
            valid_rows.append(row_copy)

    # --- Log de Estatísticas ---
    total_blocks = len(all_results)
    valid_blocks = [r for r in all_results if r['classification'] == 'valid']
    invalid_blocks_results = [r for r in all_results if r['classification'] == 'invalid']
    
    logger.info(f"\nTotal de blocos de código encontrados: {total_blocks}")
    logger.info(f"Total de blocos VÁLIDOS: {len(valid_blocks)}")
    logger.info(f"Total de blocos INVÁLIDOS: {len(invalid_blocks_results)}")

    if valid_blocks:
        lang_stats = Counter(r['language'] for r in valid_blocks)
        logger.info("\n--- Estatísticas de Linguagens Válidas ---")
        for lang, count in sorted(lang_stats.items(), key=lambda item: item[1], reverse=True):
            percentage = (count / len(valid_blocks)) * 100
            logger.info(f"{lang:<20} {count:<6} ({percentage:.2f}%)")

    if invalid_blocks_results:
        reason_stats = Counter(r['reason'] for r in invalid_blocks_results)
        logger.info("\n--- Motivos de Rejeição de Blocos Inválidos ---")
        for reason, count in sorted(reason_stats.items(), key=lambda item: item[1], reverse=True):
            percentage = (count / total_blocks) * 100
            logger.info(f"{reason:<45} {count:<6} ({percentage:.2f}%)")

    # --- Separação Final de Posts Válidos e Inválidos ---
    df_valid = pd.DataFrame(valid_rows)
    df_invalid = pd.DataFrame(invalid_rows)

    # --- Log do Resumo Final ---
    logger.info("\n--- Resumo do Salvamento ---")

    # Contagem para posts válidos
    if not df_valid.empty and 'id' in df_valid.columns and 'question_id' in df_valid.columns:
        valid_questions = len(df_valid[df_valid['id'] == df_valid['question_id']])
        valid_answers_comments = len(df_valid) - valid_questions
        logger.info(f"Arquivo de VÁLIDOS ({PREPROCESSED_POSTS}):")
        logger.info(f"  - Perguntas salvas: {valid_questions}")
        logger.info(f"  - Respostas/Comentários salvos: {valid_answers_comments}")
    else:
        logger.info(f"Total de posts salvos em {PREPROCESSED_POSTS} (válidos): {len(df_valid)}")

    # Contagem para posts inválidos
    if not df_invalid.empty and 'id' in df_invalid.columns and 'question_id' in df_invalid.columns:
        invalid_questions = len(df_invalid[df_invalid['id'] == df_invalid['question_id']])
        invalid_answers_comments = len(df_invalid) - invalid_questions
        logger.info(f"Arquivo de INVÁLIDOS ({invalid_path}):")
        logger.info(f"  - Perguntas movidas: {invalid_questions}")
        logger.info(f"  - Respostas/Comentários movidos: {invalid_answers_comments}")
    else:
        logger.info(f"Total de posts salvos em {invalid_path} (inválidos): {len(df_invalid)}")

    # --- Salvamento dos Arquivos ---
    df_valid.to_csv(PREPROCESSED_POSTS, index=False, quoting=csv.QUOTE_ALL)
    df_invalid.to_csv(invalid_path, index=False, quoting=csv.QUOTE_ALL)

    logger.info("\nProcessamento do S8 concluído com sucesso!")

if __name__ == "__main__":
    main()
    