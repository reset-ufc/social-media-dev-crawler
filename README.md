# Social Media Dev Crawler

## Descrição

Projeto para extrair, processar e analisar posts de plataformas Q&A (por exemplo, Stack Exchange). O pipeline extrai dados brutos, filtra e pré-processa posts relevantes e, em seguida, aplica modelagem de tópicos (LDA) para identificar temas predominantes nas discussões.

O fluxo principal é composto por duas etapas:

- **Mineração de dados (`s1_dump_mining`)**: extração e limpeza dos dumps brutos.
- **Modelagem de tópicos (`s2_Lda`)**: pré-processamento e treinamento/avaliação de modelos LDA.

## Estrutura do repositório

- `src/` — código-fonte e scripts (inclui `paths.py` e `utils_global.py`).
  - `s1_dump_mining/` — pipeline de extração e preparação de dados.
  - `s2_Lda/` — scripts para normalização, treinamento e inferência LDA.
- `data/` — dados gerados pelo pipeline:
  - `data_mining/` — saídas da mineração (s1 e s2).
  - `Lda/` — modelos, CSVs e plots relacionados ao LDA.
- `prompts/` — templates de prompts usados com LLMs para rotular tópicos.
- `notebooks/` — notebooks para análise, validação e visualização.
- `Extraidos dump/` — local para colocar os arquivos .7z dos dumps fornecidos pelo Archive.org.

## Requisitos

- Python (recomenda-se gerenciar versões com `pyenv` ou virtualenv).
- Dependências listadas em `requirements.txt` e `requirements_lda.txt`.

Observação: algumas etapas (por exemplo, avaliação do Mallet) podem exigir Java e dependências específicas.

## Instalação rápida (exemplo com pyenv)

1. Instale e configure `pyenv` (ou use `venv`/`virtualenv`).
2. Crie os ambientes recomendados:

```bash
pyenv virtualenv 3.12.3 venv-main
pyenv virtualenv 3.8.10 venv-lda
```

3. Instale dependências:

```bash
pyenv activate venv-main
pip install --upgrade pip
pip install -r requirements.txt
pyenv deactivate

pyenv activate venv-lda
pip install --upgrade pip
pip install -r requirements_lda.txt
pyenv deactivate
```

Se você não usa `pyenv`, crie um `venv` e instale os requerimentos com `pip`.

Adicione sua chave de API do Chat-GPT 5.1 em um arquivo .env, que deverá ser criado em src\s2_Lda

## Execução

1. Gere a estrutura de diretórios (script utilitário):

```bash
pyenv activate venv-main
python src/utils_global.py
```

2. Coloque os dumps baixados de https://archive.org/details/stackexchange_20250930 em `Extraidos dump/` (arquivos `.7z`).

3. Execute a pipeline de mineração:

```bash
python src/s1_dump_mining/pipeline.py
```
Todos os resultados serão salvos em data/data_mining

4. Normalize os dados para LDA:

```bash
python src/s2_Lda/s0_normalisation.py
```

5. Para treinar modelos Mallet use `venv-lda`

```bash
pyenv activate venv-lda
python src/s2_Lda/s1_evaluate_mallet.py
```

6. Troque novamente para o venv-main e execute os passos 2 e 3, para inferir o nome dos tópicos por meio do Chat-GPT 5.1 e classificar os posts por meio do modelo treinado e das labels geradas pelo LLM.

```bash
pyenv activate venv-main
python src/s2_Lda/s2_infer_topics.py
python src/s2_Lda/s3_classify_posts.py
```

7. Com os posts classificados em seus tópicos treino os modelos referentes aos subtópicos. Edite o arquivo src/s2_Lda/s1_evaluate_mallet.py, para iniciar o treinamento dos submodelos.

Comente a linha
```python
run('main1')
```

e descomente a linha
```python
#run_submodels(MODELS / 'main1')
```

8. Realize as seguintes edições ao final dos arquivos:

**src/s2_Lda/s2_infer_topics.py**

Comente
```python
main_topic_inference(
    MODELS / 'main1',
    llm=ChatOpenAI(model_name="gpt-5.1", temperature=0.7),
)
```

E descomente 
```python
"""subtopics_inference(
    MODELS / 'main1',
    llm=ChatOpenAI(model_name="gpt-5.1", temperature=0.7),
)"""
```

**src/s2_Lda/s3_classify_posts.py**

Comente
```python
classify_main_topics(MODELS / 'main1')
```

E descomente 
```python
#classify_all_subtopics(MODELS / 'main1')
```

9. Execute ambos usando o venv-main
```bash
python src/s2_Lda/s2_infer_topics.py
python src/s2_Lda/s3_classify_posts.py
```

10. Opcionalmente, execute ```src/s2_Lda/s4_model_visualizations.py```, para gerar um arquivo topics.txt dentro da pasta de cada modelo, com as palavras agrupadas pelo LDA pertencentes a cada tópico.

11. Execute ```src/s2_Lda/s5_sampling.py```e gere a tabela de validação manual, que será salva em `data/Lda/validation_sample.xlsx`. Esta tabela deverá ser devidamente preenchida conforme foi descrito no artigo, na seção de validação manual. Tendo realizado a validação, mantenha o arquivo no mesmo local em que ele foi criado.

12. Na pasta notebooks, execute por completo os três arquivos presentes. Após isso toda a pipeline estará concluída.