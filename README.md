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

## Instalação rápida (exemplo com pyenv)

1. Instale e configure `pyenv` (ou use `venv`/`virtualenv`).

2. Crie os ambientes virtuais:

```bash
pyenv virtualenv 3.12.3 venv-main
pyenv virtualenv 3.8.10 venv-lda
```

3. Instale dependências:

```bash
pyenv activate venv-main
pip install --upgrade pip
pip install -r requirements_main.txt
pyenv deactivate

pyenv activate venv-lda
pip install --upgrade pip
pip install -r requirements_lda.txt
pyenv deactivate
```

4. Instale o Mallet 2.0.8

```bash
cd /tmp
wget http://mallet.cs.umass.edu/dist/mallet-2.0.8.tar.gz
sudo mkdir -p /opt/mallet
sudo tar -xzf mallet-2.0.8.tar.gz -C /opt/mallet --strip-components=1
sudo chmod -R 755 /opt/mallet
sudo chown -R $USER:$USER /opt/mallet
```
Ou instale o modelo na pasta `C:\mallet` caso use Windows

Adicione sua chave de API do Chat-GPT 5.1 em um arquivo `.env`, que deverá ser criado em `src\s2_Lda`

## Execução

1. Gere a estrutura de diretórios:

```bash
pyenv activate venv-main
python src/utils_global.py
```

2. Realize o download dos dumps completos dos sites: StackOverflow, Crypto e Security por meio do site https://archive.org/details/stackexchange_20251231 e adicione-os na pasta `Extraidos dump/` (arquivos `.7z`).

3. Execute a pipeline de mineração

Na pasta scr/s1_dump_mining execute os arquivos s1 e s2. Em seguida crie o arquivo merged_tags.csv em data/data_mining/s1. Esse arquivo deve conter o merge entre os arquivos releated_tags.csv e releated_tags_crypto.csv. Não devem entrar no arquivo criado quaisquer tags que não tenham sido validadas manualmente como relacionadas a criptografia.

o csv deve seguir a estrutura: (Exemplo)

```
tag,b,a,h1,h2
cryptography,1500,1200,0.8,0.15
encryption,2000,1800,0.9,0.20
```

Em seguida prossiga executando os arquivos s3 e s4 para montagem do dataset de posts.

4. Normalize os dados para o LDA
```bash
python src/s2_Lda/s0_normalisation.py
```

5. Para treinar modelos Mallet use `venv-lda`

```bash
pyenv activate venv-lda
python src/s2_Lda/s1_evaluate_mallet.py
```

6. Troque novamente para o venv-main e execute os passos 2 e 3, para gerar o nome dos tópicos por meio do Chat-GPT, e classificar os posts com o modelo treinado usando as labels geradas pelo LLM. 

```bash
pyenv activate venv-main
python src/s2_Lda/s2_infer_topics.py
python src/s2_Lda/s3_classify_posts.py
```

7. Com os posts classificados em seus tópicos, treine os modelos referentes aos subtópicos. 

Edite o arquivo `src/s2_Lda/s1_evaluate_mallet.py`, para iniciar o treinamento dos submodelos:

Comente a linha
```python
run('main1')
```

e descomente a linha
```python
#run_submodels(MODELS / 'main1')
```
Em seguida execute-o usando o `venv-lda`

8. Realize as seguintes edições ao final dos arquivos:

 - **src/s2_Lda/s2_infer_topics.py**

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

- **src/s2_Lda/s3_classify_posts.py**

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

10. Execute ```src/s2_Lda/s5_sampling.py```e gere a tabela de validação manual, que será salva em `data/Lda/validation_sample.xlsx`. A planilha deverá ser devidamente preenchida conforme foi descrito no artigo, na seção de validação manual. Tendo realizado a validação, mantenha o arquivo no mesmo local em que ele foi criado.

11. Na pasta notebooks, execute por completo os três arquivos presentes. Esses arquivos geram levantamentos sobre a validação manual, gráficos e tabelas para responder as questões de pesquisa. Após isso toda a pipeline estará concluída.