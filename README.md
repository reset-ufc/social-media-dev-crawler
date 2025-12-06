# Social Media Dev Crawler

## Descrição

Este projeto é um pipeline de mineração e análise de dados projetado para processar dumps de plataformas de Q&A (como o Stack Exchange). O objetivo é extrair, filtrar e analisar posts para modelar e entender os tópicos de discussão dentro de comunidades de desenvolvedores.

O processo é dividido em duas grandes etapas:

1.  **Mineração de Dados (`s1_dump_mining`)**: Extrai e prepara os dados a partir de dumps brutos, filtrando posts relevantes e limpando seu conteúdo.
2.  **Modelagem de Tópicos com LDA (`s2_Lda`)**: Aplica a modelagem de tópicos Latent Dirichlet Allocation (LDA) sobre os dados processados para descobrir os principais temas discutidos nos posts.

## Estrutura de Diretórios

-   **`src/`**: Contém todo o código-fonte do projeto.
    -   `s1_dump_mining/`: Scripts para o pipeline de extração e processamento de dados.
    -   `s2_Lda/`: Scripts para o pipeline de modelagem de tópicos com LDA.
    -   `paths.py`: Define todos os caminhos de arquivos e constantes importantes do projeto.
    -   `utils_global.py`: Funções utilitárias usadas em múltiplos scripts.

-   **`data/`**: Armazena todos os dados gerados e intermediários.
    -   `data_mining/`: Saídas do pipeline de mineração.
    -   `Lda/`: Saídas do pipeline de LDA (modelos, visualizações, etc.).
    -   `llm_inference/`: Dados relacionados à inferência de nomes de tópicos via LLM.

-   **`prompts/`**: Contém os templates de prompts usados para consultar o LLM para nomear os tópicos do LDA.

-   **`notebooks/`**: Jupyter Notebooks para análise, validação e visualização de dados.

-   **`Extraidos dump/`**: Local onde os dumps de dados brutos (arquivos `.7z`) devem ser colocados.

## Pipelines de Execução

### 1. Mineração de Dados (`src/s1_dump_mining`)

Este pipeline é orquestrado pelo script `src/s1_dump_mining/pipeline.py` e executa as seguintes etapas em sequência:

-   **`s1_get_main_tag.py`**: Lê os dumps (`.7z`) e extrai as perguntas que contêm a `QUESTION_TAG` principal (ex: "python").
-   **`s2_calculate_tag_heuristics.py`**: Analisa todas as tags dos dumps para calcular heurísticas e encontrar tags que são fortemente correlacionadas com a tag principal.
-   **`s4_get_posts.py`**: Usa as tags correlacionadas para buscar e salvar todos os posts (perguntas) relevantes dos dumps.
-   **`s5_get_connected_posts.py`**: Expande os posts encontrados, buscando e conectando suas respectivas respostas e comentários.
-   **`s6_filter_posts.py`**: Filtra os posts com base em métricas de popularidade (score, visualizações, etc.).

### 2. Modelagem de Tópicos com LDA (`src/s2_Lda`)

Após a mineração, os scripts neste diretório devem ser executados em sequência para realizar a modelagem de tópicos.

-   **`s0_normalisation.py`**: Prepara e normaliza o texto dos posts (tokenização, lematização, etc.) para criar um córpus para o modelo LDA.
-   **`s1_evaluate_mallet.py`**: Treina e avalia múltiplos modelos LDA usando o wrapper Mallet para encontrar o número ótimo de tópicos.
-   **`s2_infer_topics.py`**: Utiliza um Modelo de Linguagem Grande (LLM) para analisar as palavras-chave de cada tópico gerado pelo LDA e inferir um nome legível e coeso para ele.
-   **`s2_model_visualizations.py`**: Gera visualizações interativas (como pyLDAvis) para ajudar na interpretação e análise dos tópicos.
-   **`s3_classify_posts.py`**: Classifica cada post, atribuindo a ele o tópico mais provável.
-   **`s3_fused_metrics.py`**: Calcula métricas de fusão para avaliar a qualidade e a distribuição dos tópicos.
-   **`s4_sampling.py`**: Realiza amostragem de posts dentro de cada tópico para análise qualitativa.

## Como Executar

1.  **Configuração Inicial**:
    -   Instale as dependências. Note que há dois arquivos de requisitos.
        ```bash
        pip install -r requirements.txt
        pip install -r requirements_lda.txt
        ```
    -   Coloque os arquivos de dump (`.7z`) na pasta `Extraidos dump/`.
    -   Verifique as constantes no arquivo `src/paths.py`, como `QUESTION_TAG` e os nomes dos sites.

2.  **Executar o Pipeline de Mineração de Dados**:
    ```bash
    python src/s1_dump_mining/pipeline.py
    ```

3.  **Executar o Pipeline de Modelagem de Tópicos**:
    -   Execute os scripts do diretório `src/s2_Lda/` na ordem numérica (de `s0` a `s4`).
    ```bash
    python src/s2_Lda/s0_normalisation.py
    python src/s2_Lda/s1_evaluate_mallet.py
    # ... e assim por diante
    ```
