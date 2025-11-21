# Social Media Dev Crawler

## Descrição

Este projeto é um pipeline de mineração e análise de dados projetado para processar dumps de plataformas de Q&A (como o Stack Exchange). O objetivo é extrair, filtrar e analisar posts para identificar potenciais maus usos de APIs criptográficas e outras práticas de segurança em trechos de código-fonte.

O processo é dividido em duas grandes etapas:

1.  **Mineração de Dados (`dump_mining`)**: Extrai e prepara os dados a partir de dumps brutos, filtrando posts relevantes e limpando seu conteúdo.
2.  **Análise com LLM (`llm_inference`)**: Utiliza um Modelo de Linguagem Grande (LLM) para analisar os trechos de código extraídos, identificar e classificar os maus usos.

## Estrutura de Diretórios

-   **`src/`**: Contém todo o código-fonte do projeto.
    -   `dump_mining/`: Scripts para o pipeline de extração e processamento de dados.
    -   `llm_inference/`: Scripts para o pipeline de análise com LLM.
    -   `paths.py`: Define todos os caminhos de arquivos e constantes importantes do projeto.
    -   `utils_global.py`: Funções utilitárias usadas em múltiplos scripts.

-   **`data/`**: Armazena todos os dados gerados e intermediários. A estrutura é fundamental para o funcionamento do pipeline.
    -   `data_mining/`: Saídas do pipeline de mineração.
        -   `data_mining.log`: Arquivo de log para esta etapa.
        -   `s1/questions_dump.csv`: Perguntas brutas extraídas do dump com a tag principal.
        -   `s1/releated_tags/`: Arquivos CSV com heurísticas de tags correlacionadas.
        -   `s1/releated_posts.csv`: Posts que contêm as tags de interesse.
        -   `s2/connected_posts.csv`: Posts conectados com suas respostas e comentários.
        -   `s2/filtred_posts.csv`: Posts filtrados por métricas de popularidade.
        -   `s2/preprocessed_full_posts.csv`: Versão final dos posts, com texto limpo e blocos de código extraídos e validados.
        -   `s2/invalid_codes.csv`: Posts descartados por não conterem código válido.
    -   `llm_inference/`: Saídas do pipeline de análise com LLM.
        -   `classification/`: Resultados da classificação do LLM.
            -   `flat/`: Saídas do pipeline "plano", que analisa e julga em duas etapas.
            -   `hierarquical/`: Saídas do pipeline "hierárquico", que primeiro detecta e depois classifica os maus usos.
        -   `summarization/`: Logs e resumos gerados a partir dos resultados do LLM.

-   **`prompts/`**: Contém os templates de prompts usados para consultar o LLM.
    -   `flat/`: Prompts para o pipeline plano.
    -   `hierarquical/`: Prompts para o pipeline hierárquico.

-   **`notebooks/`**: Jupyter Notebooks para análise, validação e visualização de dados.

-   **`Extraidos dump/`**: Local onde os dumps de dados brutos (arquivos `.7z`) devem ser colocados.

## Pipelines de Execução

### 1. Mineração de Dados (`src/dump_mining`)

Este pipeline é orquestrado pelo script `src/dump_mining/pipeline.py` e executa as seguintes etapas em sequência:

-   **`s1_get_main_tag.py`**: Lê os dumps (`.7z`) e extrai as perguntas que contêm a `QUESTION_TAG` principal (ex: "encryption").
-   **`s2_calculate_tag_heuristics.py`**: Analisa todas as tags dos dumps para calcular heurísticas (H1, H2) e encontrar tags que são fortemente correlacionadas com a tag principal.
-   **`s4_get_posts.py`**: Usa as tags correlacionadas para buscar e salvar todos os posts (perguntas) relevantes dos dumps.
-   **`s5_get_connected_posts.py`**: Expande os posts encontrados, buscando e conectando suas respectivas respostas e comentários.
-   **`s6_filter_posts.py`**: Filtra os posts com base em métricas de popularidade (score, visualizações, etc.) e remove auto-respostas para focar nos conteúdos mais relevantes.
-   **`s7_preprocess_body.py`**: Limpa o corpo HTML dos posts, extrai os blocos de código (`<code>...</code>`) e aplica uma primeira camada de validação baseada em heurísticas para separar código real de logs, comandos de terminal, etc.
-   **`s8_validate_code.py`**: (Disponível, mas não integrado ao pipeline principal) Realiza uma validação de código mais robusta usando `tree-sitter` para analisar a estrutura sintática do código em várias linguagens.

### 2. Análise com LLM (`src/llm_inference`)

Orquestrado por `src/llm_inference/pipeline.py`, este pipeline pode ser executado em duas variantes: `flat_pipeline` ou `hier_pipeline`.

-   **`s1_make_llm_input.py`**: Prepara as entradas para o LLM, formatando os dados do post e os blocos de código em um prompt estruturado.
-   **`s2_llm_chain.py`**: Gerencia a comunicação com o LLM. Ele itera sobre os dados, formata o prompt final com as instruções do arquivo de prompt, envia para o modelo e salva a resposta JSON.
-   **`s3_summarization.py`**: Gera um resumo estatístico a partir dos resultados da análise do LLM, contando o número de maus usos, categorias e distribuição por site.
-   **`s4_merge_llm_results.py`**: Compara e consolida os resultados de diferentes etapas do LLM (ex: análise vs. julgamento), gerando um arquivo final com os dados validados.

## Como Executar

1.  **Configuração Inicial**:
    -   Instale as dependências: `pip install -r requirements.txt`
    -   Coloque os arquivos de dump (`.7z`) na pasta `Extraidos dump/`.
    -   Verifique as constantes no arquivo `src/paths.py`, como `QUESTION_TAG`, `THRE1`, `THRE2`, e os nomes dos sites.

2.  **Executar o Pipeline de Mineração de Dados**:
    ```bash
    python src/dump_mining/pipeline.py
    ```

3.  **Executar o Pipeline de Análise com LLM**:
    -   Abra o arquivo `src/llm_inference/pipeline.py`.
    -   No final do arquivo (`if __name__ == '__main__':`), escolha qual pipeline executar (ex: `hier_pipeline(limit=3)` para um teste em 3 posts).
    -   Execute o script:
    ```bash
    python src/llm_inference/pipeline.py
    ```