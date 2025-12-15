from pathlib import Path
import os
import re
import pandas as pd
from datetime import datetime

import logging
from paths import DATA_MINING_S2, DUMP_MINING_LOG_FILE, LLM_CLASSIFICATION, LLM_SUMMARIZATION, RELEATED_TAGS_DIR, DUMP, SITES
import io
import subprocess
import xml.etree.ElementTree as ET

import math
import pandas as pd
import scipy.stats as st
import numpy as np
from paths import *

def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def extract_tag_list(tags_field):
    """
    Recebe o valor bruto da coluna tags e retorna lista de tags.
    Suporta formatos comuns:
      - "python;cryptography"
    """
    if pd.isna(tags_field) or tags_field == "":
        return []
    if '<' in tags_field and '>' in tags_field:
        return re.findall(r'<(.+?)>', tags_field)
    if ';' in tags_field:
        return [t.strip() for t in tags_field.split(';') if t.strip()]
    if '|' in tags_field:
        return [t.strip() for t in tags_field.split('|') if t.strip()]
    return [t.strip() for t in re.split(r'[\s,;|]+', tags_field) if t.strip()]


def safe_date(ts):
    """Padroniza o formato de data, ignorando erros."""
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.strftime('%Y/%m/%d, %H:%M:%S')
    except Exception:
        return ts


def get_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    Configura e retorna um logger que escreve para o console e para um arquivo.
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger  # Evita adicionar handlers duplicados

    logger.setLevel(level)
    formatter = logging.Formatter(
        '%(levelname)s - %(message)s')

    # Handler para o console
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Handler para o arquivo
    ensure_parent_dir(DUMP_MINING_LOG_FILE)
    fh = logging.FileHandler(DUMP_MINING_LOG_FILE, encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

def make_data():
    """Creates the data directory structure."""
    os.makedirs(RELEATED_TAGS_DIR, exist_ok=True)
    os.makedirs(DATA_MINING_S2, exist_ok=True)
    os.makedirs(LLM_CLASSIFICATION, exist_ok=True)
    os.makedirs(LLM_SUMMARIZATION, exist_ok=True)


def calc_sample_size(population, error_margin=0.05, confidence=0.95, p=0.5):
    """Cochran + Finite Population Correction"""
    Z = st.norm.ppf((1 + confidence) / 2)
    
    numerator = population * (Z**2) * p * (1 - p)
    denominator = (population - 1) * (error_margin**2) + (Z**2) * p * (1 - p)
    n = numerator / denominator

    return math.ceil(n)


def neyman_allocation(n, Nh_list, Sh_list):
    Nh = np.array(Nh_list)
    Sh = np.array(Sh_list)
    weights = Nh * Sh
    nh = n * (weights / weights.sum())
    return nh

def count_posts_comments_in_dumps(dump_dir: str = None, sites_mapping: dict = None):
    """Count questions (PostTypeId=1), answers (PostTypeId=2) and comments
    for each site dump. Reads Posts.xml and Comments.xml files using iterparse.

    Returns a pandas DataFrame with columns: `site`, `questions`, `answers`, `comments`.
    """

    dump_dir = DUMP if dump_dir is None else Path(dump_dir)
    sites_mapping = SITES if sites_mapping is None else sites_mapping

    # Try to import py7zr
    try:
        import py7zr
        has_py7zr = True
    except Exception:
        has_py7zr = False

    def get_file_stream(archive_path: Path, filename: str):
        """
        Get a streaming file object from .7z archive or uncompressed directory.
        Returns a file-like object that can be read incrementally.
        """
        archive_path = Path(archive_path)

        print(f"    Trying to get {filename} from {archive_path.name}...")

        # First try uncompressed directory
        uncompressed_dir = archive_path.with_suffix('')
        uncompressed_file = uncompressed_dir / filename
        if uncompressed_file.exists():
            print(f"      Found uncompressed {filename}")
            return open(uncompressed_file, 'rb')

        # Try .7z archive
        if not archive_path.exists():
            print(f"      Archive not found: {archive_path}")
            return None

        print(f"      Archive exists, trying to extract {filename}...")

        # Try system 7z command with pipe (streaming)
        try:
            cmd = ['7z', 'e', '-so', str(archive_path), filename]
            print(f"      Trying: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                bufsize=1024*1024  # 1MB buffer
            )
            print(f"      Success with system 7z command (streaming)")
            return process.stdout
        except FileNotFoundError:
            print(f"      7z command not found in PATH")
        except Exception as e:
            print(f"      7z error: {e}")

        # Try py7zr with extraction to temp file (avoid loading all in memory)
        if has_py7zr:
            try:
                print(f"      Trying py7zr with temp extraction...")
                import tempfile
                
                with py7zr.SevenZipFile(str(archive_path), mode='r') as z:
                    names = z.getnames()
                    print(f"      Files in archive: {len(names)}")
                    target = None
                    for n in names:
                        if n.lower().endswith(filename.lower()):
                            target = n
                            print(f"      Found {target}")
                            break
                    if not target:
                        print(f"      {filename} not found in archive")
                        return None
                    
                    # Extract to temporary file instead of memory
                    tmpdir = tempfile.mkdtemp()
                    try:
                        # Try extract method
                        z.extract(targets=[target], path=tmpdir)
                    except TypeError:
                        # Fallback for older py7zr versions
                        z.extractall(path=tmpdir)
                    
                    extracted_file = Path(tmpdir) / target
                    if extracted_file.exists():
                        print(f"      Extracted to temp file")
                        # Return file handle that will be cleaned up later
                        # Note: caller is responsible for cleanup
                        return open(extracted_file, 'rb')
                    else:
                        print(f"      File not found after extraction")
                        return None
                        
            except Exception as e:
                print(f"      py7zr error: {type(e).__name__}: {e}")

        print(f"      Could not open {filename}")
        return None

    # Step 1: Count questions and answers per site, collect post IDs
    results = {}
    postid_sets = {}

    for site_alias, archive_name in sites_mapping.items():
        print(f"\nProcessing site: {site_alias}")
        archive_path = Path(dump_dir) / archive_name

        q_count = 0
        a_count = 0
        ids = set()

        posts_file = get_file_stream(archive_path, 'Posts.xml')

        if posts_file is None:
            print(f"  Could not open Posts.xml for {site_alias}")
            results[site_alias] = {'questions': 0, 'answers': 0, 'comments': 0}
            postid_sets[site_alias] = set()
            continue

        try:
            # iterparse processes the file incrementally without loading all into memory
            print(f"  Parsing Posts.xml (streaming)...")
            for event, elem in ET.iterparse(posts_file, events=('end',)):
                if elem.tag == 'row':
                    pt = elem.attrib.get('PostTypeId')
                    pid = elem.attrib.get('Id')
                    if pid is not None:
                        ids.add(pid)
                    if pt == '1':
                        q_count += 1
                    elif pt == '2':
                        a_count += 1
                    # Clear element to free memory immediately
                    elem.clear()
                    
                    # Print progress every 100k posts
                    if (q_count + a_count) % 100000 == 0 and (q_count + a_count) > 0:
                        print(f"    Progress: {q_count + a_count} posts processed...")
                        
            print(f"  Counted: {q_count} questions, {a_count} answers, {len(ids)} post IDs")
            results[site_alias] = {'questions': q_count, 'answers': a_count, 'comments': 0}
            postid_sets[site_alias] = ids
        except Exception as e:
            print(f"  Error parsing Posts.xml: {e}")
            import traceback
            traceback.print_exc()
            results[site_alias] = {'questions': 0, 'answers': 0, 'comments': 0}
            postid_sets[site_alias] = set()
        finally:
            try:
                posts_file.close()
            except Exception:
                pass

    # Step 2: Count comments per site
    print(f"\n\nProcessing comments...")

    for site_alias, archive_name in sites_mapping.items():
        archive_path = Path(dump_dir) / archive_name
        print(f"\nLooking for Comments.xml in {site_alias}...")

        comments_file = get_file_stream(archive_path, 'Comments.xml')

        if comments_file is None:
            print(f"  No Comments.xml found for {site_alias}")
            continue

        c_count = 0
        try:
            print(f"  Parsing Comments.xml (streaming)...")
            for event, elem in ET.iterparse(comments_file, events=('end',)):
                if elem.tag == 'row':
                    postid = elem.attrib.get('PostId')
                    # Check if this PostId belongs to this site
                    if postid and postid in postid_sets.get(site_alias, set()):
                        results[site_alias]['comments'] += 1
                        c_count += 1
                    # Clear element to free memory
                    elem.clear()
                    
                    # Print progress every 100k comments
                    if c_count % 100000 == 0 and c_count > 0:
                        print(f"    Progress: {c_count} comments processed...")
                        
            print(f"  Counted: {c_count} comments for {site_alias}")
        except Exception as e:
            print(f"  Error parsing Comments.xml for {site_alias}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                comments_file.close()
            except Exception:
                pass

    # Step 3: Build result dataframe
    df_data = []
    for site_alias in sites_mapping.keys():
        df_data.append({
            'site': site_alias,
            'questions': results[site_alias]['questions'],
            'answers': results[site_alias]['answers'],
            'comments': results[site_alias]['comments']
        })

    df = pd.DataFrame(df_data)

    # Add totals row
    totals = df[['questions', 'answers', 'comments']].sum()
    totals_row = {
        'site': 'TOTAL',
        'questions': int(totals['questions']),
        'answers': int(totals['answers']),
        'comments': int(totals['comments'])
    }
    df = pd.concat([df, pd.DataFrame([totals_row])], ignore_index=True)

    df.to_csv('posts_comments_count.csv', index=False)
    print(df.to_string(index=False))
    return df

