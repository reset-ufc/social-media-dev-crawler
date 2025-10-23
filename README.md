# Social Media Dev Crawler

## Descrição

Este projeto é um pipeline de mineração e análise de dados de plataformas de Q&A (como Stack Overflow) para identificar o uso indevido de práticas de segurança em trechos de código-fonte. O processo é dividido em duas etapas principais:

1.  **Mineração de Dados**: Extração e filtragem de posts relevantes a partir de dumps de dados de sites como o Stack Exchange.
2.  **Análise com LLM**: Utilização de um Modelo de Linguagem Grande (LLM) para analisar os trechos de código e identificar potenciais maus usos de segurança.

## Estrutura de Pastas

A pasta `data` é organizada da seguinte forma:

-   `data/data_mining`: Contém os resultados intermediários e finais da etapa de mineração de dados.
    -   `coarse_questions.csv`: Perguntas iniciais extraídas dos dumps.
    -   `releated_tags`: Tags relacionadas à tag principal de interesse.
    -   `releated_posts.csv`: Posts que contêm as tags relacionadas.
    -   `connected_posts.csv`: Posts com suas respectivas respostas e comentários.
    -   `filtred_posts.csv`: Posts filtrados por popularidade.
    -   `preprocessed_posts.csv`: Posts pré-processados e limpos.
-   `data/llm_inference`: Armazena os resultados da análise do LLM.
    -   `misuse_cases_codes.json`: Casos de mau uso identificados pelo LLM.
    -   `judgement_codes.json`: Julgamento dos casos de mau uso identificados.
-   `data/logs`: Arquivos de log gerados durante a execução do pipeline.

## Pipeline de Execução

O pipeline é orquestrado em duas fases principais, compostas pelos scripts localizados em `src/`.

### 1. Data Mining (`dump_mining`)

Esta fase é responsável por extrair e preparar os dados para a análise.

-   **`s1_get_main_tag.py`**: Inicia o processo lendo os dumps de dados (arquivos `.7z`) e extrai todas as perguntas que contêm uma tag principal de interesse (ex: `python`). As perguntas são salvas em `coarse_questions.csv`.

-   **`s2_calculate_tag_heuristics.py`**: Calcula heurísticas para identificar tags que frequentemente aparecem junto com a tag principal. O objetivo é encontrar tags relacionadas que possam indicar um contexto de segurança (ex: `crypto`, `ssl`). As tags filtradas são salvas em `data/releated_tags`.

-   **`s4_get_posts.py`**: Com base nas tags relacionadas, este script busca nos dumps por posts que contenham essas tags e que também tenham atividade (respostas ou comentários). Os posts encontrados são salvos em `releated_posts.csv`.

-   **`s5_get_connected_posts.py`**: Conecta as perguntas encontradas na etapa anterior com suas respectivas respostas e comentários, consolidando tudo em `connected_posts.csv`.

-   **`s6_filter_posts.py`**: Filtra os posts com base em métricas de popularidade (número de respostas, visualizações, score) para focar a análise nos posts mais relevantes. O resultado é salvo em `filtred_posts.csv`.

-   **`s7_preprocess_body.py`**: Realiza a limpeza final dos posts, removendo HTML, extraindo e validando blocos de código, e separando os posts que contêm código válido. O resultado final é salvo em `preprocessed_posts.csv`.

### 2. Análise com LLM (`llm_inference`)

Esta fase utiliza um LLM para analisar os dados pré-processados e detectar maus usos de segurança.

-   **`s0_prompts.py`**: Carrega os prompts que serão usados para instruir o LLM.

-   **`s1_make_llm_input.py`**: Formata os dados de um post (título, corpo, respostas, comentários e código) em uma string estruturada para ser usada como entrada para o LLM.

-   **`s2_detect_misuse.py`**: Itera sobre os posts pré-processados, envia o conteúdo para o LLM com um prompt para análise hierárquica do código e salva as respostas do modelo (potenciais maus usos) em `misuse_cases_codes.json`.

-   **`s3_judge_model.py`**: (Opcional) Envia os maus usos detectados para um segundo "juiz" LLM, que avalia a validade da análise inicial. Os resultados do julgamento são salvos em `judgement_codes.json`.

## Como Executar

Para executar o pipeline completo, siga os passos abaixo:

1.  **Configuração**:
    -   Instale as dependências: `pip install -r requirements.txt`
    -   Coloque os dumps de dados (arquivos `.7z`) na pasta `Extraidos dump`.
    -   Configure as tags e sites de interesse no arquivo `src/paths.py`.

2.  **Executar o Pipeline de Mineração**:
    ```bash
    python src/dump_mining/dump_mining_pipeline.py
    ```

3.  **Executar a Análise com LLM**:
    ```bash
    python src/llm_inference/s2_detect_misuse.py
    ```

4.  **Executar o Julgamento**:
    ```bash
    python src/llm_inference/s3_judge_model.py
    ```
