import pandas as pd
from bs4 import BeautifulSoup
import os
from tqdm import tqdm

# Importa as configurações para obter os caminhos dos arquivos
import paths


def clean_html_body(html_text: str) -> str:
    """
    Remove tags HTML de uma string, preservando o texto.

    Args:
        html_text: Uma string contendo o corpo do post em formato HTML.

    Returns:
        O texto limpo, sem tags HTML. Retorna uma string vazia se a entrada
        não for uma string.
    """
    if not isinstance(html_text, str):
        return ""

    # Usa BeautifulSoup para parsear o HTML
    soup = BeautifulSoup(html_text, 'html.parser')

    # O método get_text() extrai todo o texto e remove as tags,
    # preservando o conteúdo textual de hyperlinks (<a>) e ignorando
    # tags sem texto como <img>.
    return soup.get_text()


def main():
    """
    Função principal para carregar, processar e salvar os dados.
    """
    print(f"Carregando posts de: {paths.RELEATED_POSTS}")
    df = pd.read_csv(paths.RELEATED_POSTS)

    print("Pré-processando a coluna 'Body'...")
    # Garante que a coluna 'Body' seja do tipo string
    df['Body'] = df['Body'].astype(str)
    df['Cleaned_Body'] = [clean_html_body(
        body) for body in tqdm(df['Body'], desc="Limpando HTML")]

    # Salva o resultado em um novo arquivo para não sobrescrever o original
    output_path = paths.FILTERED_POSTS
    df.to_csv(output_path, index=False)
    print(f"Processamento concluído. Arquivo salvo em: {output_path}")


if __name__ == "__main__":
    main()
