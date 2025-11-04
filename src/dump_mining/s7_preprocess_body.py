import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import get_logger, ensure_parent_dir
from paths import *
import csv
import re
import html
from tqdm import tqdm
import pandas as pd
from typing import Tuple, List
from collections import Counter

logger = get_logger(__name__)

# ==========================================================
# === FUNÇÃO DE VALIDAÇÃO DE CÓDIGO ========================
# ==========================================================

def get_code_validity_reason(block: str) -> str:
    """
    Analisa um bloco de texto e retorna uma string indicando por que ele é considerado
    código válido ou inválido.
    (C, C++, Python, PHP, Java, etc.).
    """
    block = (block or "").strip()
    if not block:
        return "rejeitado_bloco_vazio"

    # 1. Filtrar comandos de terminal e outputs de ferramentas
    if re.match(r"^(\$|#|>>>|\.\.\.|~|sudo|pip|gpg|openssl|make|rm|cd|ls|echo|exit|touch|mv|cp|service|systemctl|kill)\b", block):
        return "rejeitado_comando_terminal"
    if re.search(r"(?:Cipher:|Ciphers:|Version:|Usage:|Traceback|Exception|Error:|stack traceback|installing|compiling|loading plugin|Copyright|License|Available)", block, re.IGNORECASE):
        return "rejeitado_output_ferramenta"

    # 2. Evitar outputs ou logs
    if re.search(r"(?:INFO:|DEBUG:|WARN:|WARNING:|ERROR:|failed|successfully|bytes|MB/s|progress|Loading|Saving)", block, re.IGNORECASE):
        return "rejeitado_output_log"

    # 3. Ignorar fórmulas matemáticas e pseudo código
    if re.search(r"[⊕±Σ∑√∫≈≤≥∞≠→←⇔×÷∂∇µλφπΩωβθδγψηρ]", block):
        return "rejeitado_formula_matematica"

    # 4. Muito curto e sem estrutura de código
    if len(block) < 8 and not re.search(r"[;{}()\[\]=#.:<>/]", block):
        return "rejeitado_muito_curto"

    # 5. Padrões de linguagens de programação
    code_indicators = [
        # Python
        r"\b(def|class|import|from|for|if|elif|else|return|try|except|with|while|break|continue|assert)\b",
        r"print\s*\(",
        # C / C++
        r"#include\s*[<\"]",
        r"\b(int|include &lt|stdio.h&gt|char|float|double|long|uint32_t|uint64_t|struct|typedef|void|printf|snprintf|memcpy|return)\b",
        r"using\s+namespace",
        r"std::", r"::[a-zA-Z_]",
        r"\b(int|char|float|double|long|uint32_t|uint64_t|struct|typedef|void|printf|snprintf|memcpy|return)\b",
        r"using\s+namespace", r"std::", r"::[a-zA-Z_]",
        # Java
        r"\b(public|private|static|void|class|extends|implements|throws|System\.out)\b",
        # JavaScript
        r"\b(var|let|const|function|async|await|=>|console\.log)\b",
        # PHP
        r"<\?php|\?>", r"function\s+[a-zA-Z_]\w*", r"\$[a-zA-Z_]\w*", 
        r"base64_(encode|decode)", r"openssl_random_pseudo_bytes", r"mt_rand",
        # Criptografia
        r"\bAES|RSA|SHA256|sha512|Cipher|getInstance|encrypt|decrypt|Key|Spec|seed|nonce|salt\b",
        # Estrutura genérica
        r"[{}();=\[\]]", r"//|#|/\*|\*/|<!--|-->"
    ]

    if any(re.search(p, block) for p in code_indicators):
        return "aceito_por_indicador"

    # === 6. Blocos com indentação ou múltiplas linhas ===
    if "\n" in block and re.search(r"^\s{2,}", block, re.MULTILINE):
        return "aceito_por_indentacao"

    # === 7. Funções ou atribuições ===
    if re.search(r"\w+\s*\([^)]*\)\s*{?", block) or re.search(r"\b(var|let|const)\s+\w+\s*=", block):
        return "aceito_por_funcao_ou_atribuicao"

    return "rejeitado_padrao"


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
    text = text.replace("\\n", "\n")

    # preservar blocos <code> temporariamente
    code_blocks = []

    def _preserve_code(match):
        original_block = match.group(0)
        code_blocks.append(original_block)
        return f"\n[[CODE_BLOCK_{len(code_blocks)-1}]]\n"

    text = re.sub(r'<code.*?>.*?</code>', _preserve_code, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)  # remove tags restantes

    for i, block in enumerate(code_blocks):
        text = text.replace(f"[[CODE_BLOCK_{i}]]", block)

    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def extract_code_blocks(text: str) -> List[str]:
    """Extrai blocos <code> completos, incluindo as tags."""
    blocks = re.findall(r'(<code.*?>.*?</code>)', text, flags=re.DOTALL | re.IGNORECASE)
    return [re.sub(r'\r\n?', '\n', b).strip() for b in blocks]

def clean_text_and_extract_code(text: str) -> Tuple[str, str, List[str], List[bool], List[str]]:
    """Limpa texto, valida o conteúdo dos blocos de código, e retorna os blocos completos com tags."""
    if not isinstance(text, str):
        return "", "", [], [], []

    cleaned_body = clean_text(text)
    full_blocks = extract_code_blocks(text)

    valid_blocks = []
    invalid_blocks = []
    flags = []
    reasons = []

    for full_block in full_blocks:
        full_block_s = full_block.strip()
        
        match = re.search(r'<code.*?>(.*?)</code>', full_block_s, flags=re.DOTALL | re.IGNORECASE)
        content = match.group(1) if match else ""
        
        reason = get_code_validity_reason(content.strip())
        reasons.append(reason)
        
        is_valid = reason.startswith("aceito")
        flags.append(is_valid)

        if is_valid:
            valid_blocks.append(full_block_s)
        else:
            invalid_blocks.append(full_block_s)

    extracted_code = "".join(valid_blocks)
    return cleaned_body, extracted_code, invalid_blocks, flags, reasons


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

    # --- Initial stats ---
    total_posts = len(df)
    total_questions = df['question_id'].nunique()
    logger.info(f"Arquivo carregado. Total de perguntas: {total_questions}")

    ensure_parent_dir(PREPROCESSED_POSTS)
    ensure_parent_dir(INVALID_CODES)

    invalid_path = str(INVALID_CODES)
    if not invalid_path.lower().endswith(".csv"):
        invalid_path += ".csv"

    valid_rows = []
    invalid_rows = []
    all_reasons = []
    invalid_question_ids = set()

    logger.info("Iniciando pré-processamento de posts (S7)...")

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Pré-processando posts (s7)"):
        body = str(row.get('body', ''))
        cleaned_body, extracted_code, invalid_blocks, flags, reasons = clean_text_and_extract_code(body)
        all_reasons.extend(reasons)

        row_copy = row.copy()
        row_copy['body'] = cleaned_body
        row_copy['code'] = extracted_code

        if invalid_blocks:
            invalid_question_ids.add(row.get("question_id", ""))
            row_copy["invalid_block_preview"] = (
                invalid_blocks[0][:1000] + " ...[truncated]" if len(invalid_blocks[0]) > 1000 else invalid_blocks[0]
            )
            invalid_rows.append(row_copy)
        else:
            valid_rows.append(row_copy)

    # --- Log rejected blocks ---
    stats = Counter(all_reasons)
    total_blocks = len(all_reasons)
    total_valid_blocks = sum(c for r, c in stats.items() if r.startswith('aceito'))
    logger.info(f"Total de blocos de código encontrados: {total_blocks}")
    logger.info(f"Total de blocos de código que passaram pelo filtro: {total_valid_blocks}")
    rejected_stats = {r: c for r, c in stats.items() if r.startswith('rejeitado')}

    logger.info("\n--- Relatório de Blocos de Código Rejeitados ---")
    if rejected_stats:
        for reason, count in sorted(rejected_stats.items(), key=lambda item: item[1], reverse=True):
            percentage = (count / total_blocks) * 100 if total_blocks > 0 else 0
            logger.info(f"{reason:<35} {count:<6} ({percentage:.2f}%)")
    else:
        logger.info("Nenhum bloco de código foi rejeitado.")

    df_valid_intermediate = pd.DataFrame(valid_rows)
    df_invalid = pd.DataFrame(invalid_rows)

    # Move all posts related to an invalid question to df_invalid
    if invalid_question_ids:
        related_invalids = df_valid_intermediate[df_valid_intermediate["question_id"].isin(invalid_question_ids)].copy()
        df_invalid = pd.concat([df_invalid, related_invalids], ignore_index=True)
        df_valid = df_valid_intermediate[~df_valid_intermediate["question_id"].isin(invalid_question_ids)].copy()
    else:
        df_valid = df_valid_intermediate.copy()

    # --- Calculate final counts for logging ---
    if "" in invalid_question_ids:
        invalid_question_ids.remove("")
    
    num_invalid_questions = len(invalid_question_ids)
    
    if 'id' in df_valid.columns and 'question_id' in df_valid.columns:
        is_question_mask = df_valid['id'] == df_valid['question_id']
        num_valid_questions = len(df_valid[is_question_mask])
        num_valid_answers_comments = len(df_valid[~is_question_mask])
    else:
        logger.warning("Colunas 'id' ou 'question_id' não encontradas. A contagem de perguntas/respostas pode estar incorreta.")
        num_valid_questions = 0
        num_valid_answers_comments = len(df_valid)

    # --- Log final summary ---
    logger.info("\n--- Resumo do Processamento ---")
    logger.info(f"Perguntas Válidas: {num_valid_questions}")
    logger.info(f"Perguntas Inválidas: {num_invalid_questions}")
    
    logger.info(f"\n--- Arquivo Final ({PREPROCESSED_POSTS}) ---")
    logger.info(f"Perguntas salvas: {num_valid_questions}")
    logger.info(f"Respostas e Comentários salvos: {num_valid_answers_comments}")
    logger.info(f"Total de posts salvos: {len(df_valid)}")

    # --- Save files ---
    df_valid.to_csv(PREPROCESSED_POSTS, index=False)
    df_invalid.to_csv(invalid_path, index=False)

    logger.info("\nProcessamento concluído com sucesso!")


if __name__ == "__main__":
    main()
