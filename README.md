# Social Media Dev Crawler

## Description

A comprehensive project for extracting, processing, and analyzing posts from Q&A platforms (e.g., Stack Exchange). The pipeline extracts raw data, filters and preprocesses relevant posts, and then applies Latent Dirichlet Allocation (LDA) topic modeling to identify predominant themes in discussions.

The main workflow consists of two stages:

- **Data Mining (`s1_dump_mining`)**: Extraction and cleaning of raw dumps
- **Topic Modeling (`s2_Lda`)**: Preprocessing, training, and evaluation of LDA models

---

## Repository Structure

```
├── src/                          # Source code and scripts
│   ├── paths.py                  # Path configurations
│   ├── utils_global.py           # Global utilities
│   ├── s1_dump_mining/           # Data extraction and preparation pipeline
│   └── s2_Lda/                   # Normalization, training, and LDA inference scripts
├── data/                         # Pipeline-generated data
│   ├── data_mining/              # Mining outputs
│   └── Lda/                      # LDA models, CSVs, and plots
├── prompts/                      # Prompt templates for LLM-based topic labeling
├── notebooks/                    # Notebooks with research question results and manual validation visualization
├── topic-names/                  # All topic names selected in study
└── Extraidos dump/               # Directory for Archive.org dump files (.7z)
```

---

## Requirements

- **Python Versions**: 3.12.3 and 3.8.10 (version management with `pyenv` or `virtualenv` recommended)
- **Dependencies**: Listed in `requirements_main.txt` and `requirements_lda.txt`
- **Additional Software**:
  - Mallet 2.0.8
  - 7-Zip

---

## Quick Installation Guide

### 1. Install and Configure Python Environments

Install and configure `pyenv` (or use `venv`/`virtualenv`):

```bash
# Create virtual environments
pyenv virtualenv 3.12.3 venv-main
pyenv virtualenv 3.8.10 venv-lda
```

### 2. Install Dependencies

```bash
# Install dependencies for main environment
pyenv activate venv-main
pip install --upgrade pip
pip install -r requirements_main.txt
pyenv deactivate

# Install dependencies for LDA environment
pyenv activate venv-lda
pip install --upgrade pip
pip install -r requirements_lda.txt
pyenv deactivate
```

### 3. Install Mallet 2.0.8

**Linux/Mac:**

```bash
cd /tmp
wget http://mallet.cs.umass.edu/dist/mallet-2.0.8.tar.gz
sudo mkdir -p /opt/mallet
sudo tar -xzf mallet-2.0.8.tar.gz -C /opt/mallet --strip-components=1
sudo chmod -R 755 /opt/mallet
sudo chown -R $USER:$USER /opt/mallet
```

**Windows:**

Install Mallet in the `C:\mallet` directory.

### 4. Install 7-Zip

**Linux:**

```bash
sudo apt install p7zip-full
```

**Windows:**

Download and install 7-Zip, then add the executable to your PATH.

### 5. Configure API Key

Add your ChatGPT 5.2 API key to a `.env` file in the `src/s2_Lda` directory:

```
OPENAI_API_KEY=your_api_key_here
```

**Configure this only if you want to generate new topic names, don't need to do it to reproduce the study**

---

## Execution Pipeline

### Step 1: Generate Directory Structure

```bash
pyenv activate venv-main
python src/utils_global.py
```

### Step 2: Download Stack Exchange Dumps

Download the complete dumps for StackOverflow, Crypto, and Security from [Archive.org](https://archive.org/details/stackexchange_20251231) and place the `.7z` files in the `Extraidos dump/` directory.

### Step 3: Execute Mining Pipeline

Navigate to the `src/s1_dump_mining` directory and execute files `s0` through `s4` in order.

### Step 4: Normalize Data for LDA

```bash
python src/s2_Lda/s0_normalisation.py
```

### Step 5: Train Mallet Models

Switch to the `venv-lda` environment:

```bash
pyenv activate venv-lda
python src/s2_Lda/s1_evaluate_mallet.py
```

### Step 6: Generate Topic Names and Classify Posts

**For reproducition pruposes, don't execute s2_infer_topics.py, all of the topic names are already present in the files. Jump this script and only execute the others.**

Switch back to `venv-main` and execute steps 2 and 3 to generate topic names via ChatGPT and classify posts using the trained model with LLM-generated labels:

```bash
pyenv activate venv-main
python src/s2_Lda/s2_infer_topics.py
python src/s2_Lda/s3_classify_posts.py
```

### Step 7: Train Subtopic Models

With posts classified into topics, train the subtopic models.

**Edit `src/s2_Lda/s1_evaluate_mallet.py`:**

Comment out:
```python
run('main')
```

Uncomment:
```python
run_submodels(MODELS / 'main')
```

Then execute using `venv-lda`:

```bash
pyenv activate venv-lda
python src/s2_Lda/s1_evaluate_mallet.py
```

### Step 8: Configure Subtopic Inference

Make the following edits:

**In `src/s2_Lda/s2_infer_topics.py`:**

Comment out:
```python
main_topic_inference(
    MODELS / 'main',
    llm=ChatOpenAI(model_name="gpt-5.2", temperature=0.7),
)
```

Uncomment:
```python
subtopics_inference(
    MODELS / 'main',
    llm=ChatOpenAI(model_name="gpt-5.2", temperature=0.7),
)
```

**In `src/s2_Lda/s3_classify_posts.py`:**

Comment out:
```python
classify_main_topics(MODELS / 'main')
```

Uncomment:
```python
classify_all_subtopics(MODELS / 'main')
```

### Step 9: Execute Subtopic Classification

Run both scripts using `venv-main`:

```bash
pyenv activate venv-main
python src/s2_Lda/s2_infer_topics.py
python src/s2_Lda/s3_classify_posts.py
```

### Step 10: Generate Manual Validation Table

Execute the sampling script:

```bash
python src/s2_Lda/s5_sampling.py
```

This generates a validation table saved at `data/Lda/validation_sample.xlsx`. Fill out the spreadsheet according to the manual validation procedure described. Keep the file in its original location after validation.

### Step 11: Execute Analysis Notebooks

In the `notebooks` directory, run all notebooks completely. These notebooks generate:
- Manual validation analysis
- Visualizations (graphs and charts)
- Tables to answer research questions

After completing this step, the entire pipeline is finished.
