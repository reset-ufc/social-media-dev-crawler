import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_logger, ensure_parent_dir
from paths import *
import csv
import re
import html
from tqdm import tqdm
import pandas as pd
from typing import Tuple, List
from collections import Counter

logger = get_logger(__name__)


def get_code_validity_reason(block: str) -> str:
    """
    Analisa um bloco de texto e retorna uma string indicando por que ele é considerado
    código válido ou inválido.
    """
    block = (block or "").strip()
    if not block:
        return "rejeitado_bloco_vazio"

    # 1. Filtra comandos de terminal e outputs das ferramentas
    if re.match(r"^(\$|#|>>>|\.\.\.|~|sudo|pip|gpg|openssl|make|rm|cd|ls|echo|exit|touch|mv|cp|service|systemctl|kill)\b", block):
        return "rejeitado_comando_terminal"
    if re.search(r"(?:Cipher:|Ciphers:|Version:|usage:|Usage:|Traceback|Exception|Error:|stack traceback|installing|compiling|loading plugin|Copyright|License|Available)", block, re.IGNORECASE):
        return "rejeitado_output_ferramenta"

    # 2. Evitar outputs ou logs
    if re.search(r"(?:INFO:|DEBUG:|WARN:|WARNING:|ERROR:|failed|successfully|bytes|MB/s|progress|Loading|Saving)", block, re.IGNORECASE):
        return "rejeitado_output_log"

    # 3. Ignorar fórmulas matemáticas e pseudo código
    if re.search(r"[⊕±Σ∑√∫≈≤≥∞≠→←⇔×÷∂∇µλφπΩωβθδγψηρ]", block):
        return "rejeitado_formula_matematica"

    # 4. Muito curtos, sem estrutura para códigos
    if len(block) < 8 and not re.search(r"[;{}()[\]=#.:<>/]", block):
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
        # Java
        r"\b(public|private|static|void|class|extends|implements|throws|System\.out)\b",
        # JavaScript
        r"\b(var|let|const|function|async|await|=>|console\.log)\b",
        # PHP
        r"<\?php|\?>", r"function\s+[a-zA-Z_]\w*", r"\$[a-zA-Z_]\w*",
        r"base64_(encode|decode)", r"openssl_random_pseudo_bytes", r"mt_rand",
        # Segurança e Criptografia
        r"\bAES|RSA|SHA256|sha512|Cipher|getInstance|encrypt|decrypt|Key|Spec|seed|nonce|salt\b",
        # Símbolos de estrutura
        r"[{}();=\[\]]",
        r"//|#|/\*|\*/|<!--|-->"
    ]

    if any(re.search(p, block) for p in code_indicators):
        return "aceito_por_indicador"

    # === 6. Blocos com indentação ou múltiplas linhas ===
    if "\n" in block and re.search(r"^\s{2,}", block, re.MULTILINE):
        return "aceito_por_indentacao"

    # === 7. Funções ou atribuições ===
    if re.search(r"\w+\s*\([^)]*\)\s*{?" , block) or re.search(r"\b(var|let|const)\s+\w+\s*=", block):
        return "aceito_por_funcao_ou_atribuicao"

    return "rejeitado_por_padrao"


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

    # restaurar blocos
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
        
        # Extrai o conteúdo para validação, mas preserva o bloco inteiro
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


def main():
    logger.info(f"Carregando posts de: {FILTRED_POSTS}")
    try:
        df = pd.read_csv(FILTRED_POSTS, dtype=str)
    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {FILTRED_POSTS}")
        return

    ensure_parent_dir(PREPROCESSED_POSTS)
    ensure_parent_dir(INVALID_CODES)

    cleaned_bodies, extracted_codes, all_invalid_blocks = [], [], []
    all_reasons = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Pré-processando posts (s7)"):
        body = str(row.get('body', ''))
        cleaned_body, extracted_code, invalid_blocks, flags, reasons = clean_text_and_extract_code(body)
        
        cleaned_bodies.append(cleaned_body)
        extracted_codes.append(extracted_code)
        all_invalid_blocks.append(invalid_blocks)
        all_reasons.extend(reasons)

    df['body'] = cleaned_bodies
    df['code'] = extracted_codes
    df['invalid_blocks'] = all_invalid_blocks

    # --- ETAPA FINAL: SEPARAR AMOSTRAS COM E SEM CÓDIGO VÁLIDO ---
    initial_count = len(df)
    valid_mask = df['code'].notna() & (df['code'] != '')
    
    valid_df = df[valid_mask].copy()
    invalid_df = df[~valid_mask].copy()

    # Salva posts com código válido
    valid_df = valid_df.drop(columns=['invalid_blocks'])
    valid_df.to_csv(PREPROCESSED_POSTS, index=False)

    # Processa e salva posts com código inválido
    removed_count = len(invalid_df)
    if removed_count > 0:
        logger.info(f"{removed_count} posts sem blocos de código válidos foram movidos para {INVALID_CODES}")
        
        # Concatena blocos de código inválidos na coluna 'code'
        invalid_df['code'] = invalid_df['invalid_blocks'].apply(
            lambda blocks: "\n\n".join(b for b in blocks if b)
        )
        invalid_df = invalid_df.drop(columns=['invalid_blocks'])
        
        # Garante que o arquivo de códigos inválidos seja salvo
        invalid_path = str(INVALID_CODES)
        if not invalid_path.lower().endswith(".csv"):
            invalid_path += ".csv"
        invalid_df.to_csv(invalid_path, index=False)

    final_sample_count = len(valid_df)

    # --- LOGGING DE ESTATÍSTICAS ---
    stats = Counter(all_reasons)
    total_blocks = len(all_reasons)
    total_valid_blocks = sum(count for reason, count in stats.items() if reason.startswith('aceito'))

    logger.info("--- Relatório de Filtros de Bloco de Código ---")
    logger.info(f"Total de blocos de código processados: {total_blocks}")

    logger.info("\n--- Blocos Rejeitados ---")
    rejection_reasons = {r: c for r, c in stats.items() if r.startswith('rejeitado')}
    sorted_rejections = sorted(rejection_reasons.items(), key=lambda item: item[1], reverse=True)
    
    for reason, count in sorted_rejections:
        percentage = (count / total_blocks) * 100 if total_blocks > 0 else 0
        logger.info(f"{reason.replace('rejeitado_', '').replace('_', ' ').capitalize():<30}: {count:<7} ({percentage:.2f}%)")

    logger.info("\n--- Blocos Aceitos ---")
    acceptance_reasons = {r: c for r, c in stats.items() if r.startswith('aceito')}
    sorted_acceptances = sorted(acceptance_reasons.items(), key=lambda item: item[1], reverse=True)

    for reason, count in sorted_acceptances:
        percentage = (count / total_blocks) * 100 if total_blocks > 0 else 0
        logger.info(f"{reason.replace('aceito_por_', '').replace('_', ' ').capitalize():<30}: {count:<7} ({percentage:.2f}%)")

    logger.info("\n--- Resumo Final ---")
    logger.info(f"Total de BLOCOS de código válidos encontrados: {total_valid_blocks}")
    logger.info(f"Total de posts com código válido: {final_sample_count}")
    logger.info(f"Arquivo final com {final_sample_count} posts salvo em: {PREPROCESSED_POSTS}")

if __name__ == "__main__":
    main()
