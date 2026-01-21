import csv
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_global import get_logger
from paths import CONNECTED_POSTS, FILTRED_POSTS

logger = get_logger(__name__)


def filter_popular_posts(input_csv=CONNECTED_POSTS, output_csv=FILTRED_POSTS, percentile=0.75):
    """
    Filters popular posts based on percentile metrics per site.
    Removes questions where all answers are self-answers.
    """
    logger.info(f"Starting popular posts filtering from file: {input_csv}")

    try:
        df = pd.read_csv(input_csv, dtype=str)
        before = df.shape[0]
        df.drop_duplicates(inplace=True)
        after = df.shape[0]
        logger.info(f'{before - after} duplicates removed')
    except FileNotFoundError:
        logger.error(f"File {input_csv} not found.")
        return
    except Exception as e:
        logger.error(f"ERROR reading file {input_csv}: {e}", exc_info=True)
        return

    for col in ['answer_count', 'view_count', 'score', 'comment_count']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    logger.info("\n" + "="*80)
    logger.info("NULL OWNER_ID ANALYSIS")
    logger.info("="*80)
    
    null_owner_mask = df['owner_id'].isna()
    null_owner_count = null_owner_mask.sum()
    
    if null_owner_count > 0:
        logger.info(f"Total posts with null owner_id: {null_owner_count}")
        
        null_by_type = df[null_owner_mask].groupby('type').size()
        logger.info("\nNull owner_id by post type:")
        for post_type, count in null_by_type.items():
            logger.info(f"  {post_type}: {count}")
        
        if 'site_alias' in df.columns:
            null_by_site = df[null_owner_mask].groupby('site_alias').size().sort_values(ascending=False)
            logger.info("\nNull owner_id by site:")
            for site, count in null_by_site.items():
                logger.info(f"  {site}: {count}")
    else:
        logger.info("No posts with null owner_id found")
    
    logger.info("\n" + "="*80)
    logger.info("SELF-ANSWER REMOVAL ANALYSIS")
    logger.info("="*80)
    
    df['owner_id'] = df['owner_id'].astype(str)
    
    # ETAPA 1: Identificar questões que serão desconsideradas (owner_id nulo)
    logger.info("\nSTEP 1: Identifying questions to SKIP (null owner_id)")
    logger.info("-" * 80)
    
    all_questions = df[df['type'] == 'question'].copy()
    
    null_owner_questions = all_questions[
        (all_questions['owner_id'] == 'nan') | 
        (all_questions['owner_id'] == '')
    ]
    
    null_owner_question_ids = set(null_owner_questions['question_id'])
    
    # Todos os posts relacionados a questões com owner_id nulo
    posts_to_skip = df[df['question_id'].isin(null_owner_question_ids)]
    
    logger.info(f"Questions with null owner_id: {len(null_owner_questions)}")
    logger.info("These questions will SKIP the self-answer filter automatically")
    
    if not posts_to_skip.empty:
        skip_by_site = posts_to_skip.groupby(['site_alias', 'type']).size().unstack(fill_value=0)
        
        logger.info("\nPosts to SKIP by site (will remain in dataset):")
        for site in skip_by_site.index:
            q_count = int(skip_by_site.loc[site, 'question']) if 'question' in skip_by_site.columns else 0
            a_count = int(skip_by_site.loc[site, 'answer']) if 'answer' in skip_by_site.columns else 0
            c_count = int(skip_by_site.loc[site, 'comment']) if 'comment' in skip_by_site.columns else 0
            total = q_count + a_count + c_count
            
            logger.info(f"  {site}: {total} posts (questions: {q_count}, answers: {a_count}, comments: {c_count})")
    else:
        logger.info("No posts to skip")
    
    # ETAPA 2: Identificar questões que serão consideradas para análise
    logger.info(f"\n{'='*80}")
    logger.info("STEP 2: Identifying questions to CONSIDER for self-answer check")
    logger.info("-" * 80)
    
    questions_to_consider = all_questions[
        (all_questions['owner_id'] != 'nan') & 
        (all_questions['owner_id'] != '') &
        (all_questions['answer_count'] > 0)
    ]
    
    questions_to_consider_ids = set(questions_to_consider['question_id'])
    
    # Todos os posts relacionados a questões que serão consideradas
    posts_to_consider = df[df['question_id'].isin(questions_to_consider_ids)]
    
    logger.info(f"Questions with valid owner_id and answers: {len(questions_to_consider)}")
    logger.info("These questions will be checked for self-answers")
    
    if not posts_to_consider.empty:
        consider_by_site = posts_to_consider.groupby(['site_alias', 'type']).size().unstack(fill_value=0)
        
        logger.info("\nPosts to CONSIDER by site:")
        for site in consider_by_site.index:
            q_count = int(consider_by_site.loc[site, 'question']) if 'question' in consider_by_site.columns else 0
            a_count = int(consider_by_site.loc[site, 'answer']) if 'answer' in consider_by_site.columns else 0
            c_count = int(consider_by_site.loc[site, 'comment']) if 'comment' in consider_by_site.columns else 0
            total = q_count + a_count + c_count
            
            logger.info(f"  {site}: {total} posts (questions: {q_count}, answers: {a_count}, comments: {c_count})")
    
    # ETAPA 3: Análise de auto-respostas
    if not questions_to_consider.empty:
        logger.info(f"\n{'='*80}")
        logger.info("STEP 3: Analyzing self-answers")
        logger.info("-" * 80)
        
        answers = df[df['type'] == 'answer'].copy()
        
        # Apenas respostas das questões que estamos considerando
        answers_to_check = answers[answers['question_id'].isin(questions_to_consider_ids)]
        
        if not answers_to_check.empty:
            # Merge questões com suas respostas
            q_with_a = questions_to_consider[['question_id', 'owner_id', 'site_alias']].merge(
                answers_to_check[['question_id', 'owner_id']],
                on='question_id',
                suffixes=('_q', '_a')
            )
            
            # Verifica se é auto-resposta (ambos owner_id válidos e iguais)
            q_with_a['is_self_answer'] = (
                (q_with_a['owner_id_a'] != 'nan') & 
                (q_with_a['owner_id_a'] != '') & 
                (q_with_a['owner_id_q'] == q_with_a['owner_id_a'])
            )
            
            # Agrupa por questão
            answer_stats = q_with_a.groupby(['question_id', 'site_alias']).agg(
                total_answers=('question_id', 'count'),
                self_answers=('is_self_answer', 'sum')
            ).reset_index()
            
            # Identifica questões onde TODAS as respostas são auto-respostas
            all_self_answered = answer_stats[
                (answer_stats['total_answers'] > 0) & 
                (answer_stats['self_answers'] > 0) &
                (answer_stats['self_answers'] == answer_stats['total_answers'])
            ]
            
            self_answered_question_ids = set(all_self_answered['question_id'])
            
            if self_answered_question_ids:
                logger.info(f"Found {len(self_answered_question_ids)} questions where ALL answers are self-answers")
                
                self_answered_by_site = all_self_answered.groupby('site_alias').agg(
                    num_questions=('question_id', 'count'),
                    num_self_answers=('total_answers', 'sum')
                ).sort_values('num_questions', ascending=False)
                
                logger.info("\nSelf-answered questions by site:")
                for site, row in self_answered_by_site.iterrows():
                    example_ids = all_self_answered[all_self_answered['site_alias'] == site]['question_id'].head(3).tolist()
                    example_str = ", ".join(map(str, example_ids))
                    
                    logger.info(f"  {site}: {int(row['num_questions'])} questions, {int(row['num_self_answers'])} self-answers")
                    logger.info(f"    Example question IDs: [{example_str}]")
                
                # ETAPA 4: Remoção
                logger.info(f"\n{'='*80}")
                logger.info("STEP 4: Removing self-answered questions and associated posts")
                logger.info("-" * 80)
                
                posts_before_removal = len(df)
                posts_to_remove = df[df['question_id'].isin(self_answered_question_ids)]
                
                removal_by_site = posts_to_remove.groupby(['site_alias', 'type']).size().unstack(fill_value=0)
                
                logger.info("Posts REMOVED by site:")
                for site in removal_by_site.index:
                    q_count = int(removal_by_site.loc[site, 'question']) if 'question' in removal_by_site.columns else 0
                    a_count = int(removal_by_site.loc[site, 'answer']) if 'answer' in removal_by_site.columns else 0
                    c_count = int(removal_by_site.loc[site, 'comment']) if 'comment' in removal_by_site.columns else 0
                    total = q_count + a_count + c_count
                    
                    logger.info(f"  {site}: {total} posts (questions: {q_count}, answers: {a_count}, comments: {c_count})")
                
                # Remove do dataframe
                df = df[~df['question_id'].isin(self_answered_question_ids)]
                
                posts_after_removal = len(df)
                logger.info(f"\nTotal posts removed: {posts_before_removal - posts_after_removal}")
                
                # ETAPA 5: Resultado final da filtragem de auto-resposta
                logger.info(f"\n{'='*80}")
                logger.info("STEP 5: Final result after self-answer filtering")
                logger.info("-" * 80)
                
                final_by_site = df.groupby(['site_alias', 'type']).size().unstack(fill_value=0)
                
                logger.info("Posts REMAINING by site:")
                for site in final_by_site.index:
                    q_count = int(final_by_site.loc[site, 'question']) if 'question' in final_by_site.columns else 0
                    a_count = int(final_by_site.loc[site, 'answer']) if 'answer' in final_by_site.columns else 0
                    c_count = int(final_by_site.loc[site, 'comment']) if 'comment' in final_by_site.columns else 0
                    total = q_count + a_count + c_count
                    
                    logger.info(f"  {site}: {total} posts (questions: {q_count}, answers: {a_count}, comments: {c_count})")
                
                logger.info(f"\nTotal posts remaining: {len(df)}")
            else:
                logger.info("No questions with only self-answers found")
                logger.info("All considered questions have at least one answer from another user")
        else:
            logger.info("No answers found for the questions being considered")
    else:
        logger.info("\nNo questions to consider (all questions have null owner_id or no answers)")
    
    df_questions = df[df['type'] == 'question'].copy()
    logger.info(f"\nTotal questions after self-answer filtering: {len(df_questions)}")

    for col in ['answer_count', 'view_count', 'score', 'comment_count']:
        if col not in df_questions.columns:
            df_questions[col] = 0

    if df_questions.empty:
        logger.warning("No questions found")
        return

    if 'site_alias' not in df_questions.columns:
        logger.error("Column 'site_alias' not found in DataFrame")
        return

    sites = df_questions['site_alias'].unique()
    logger.info(f"\n{'='*80}")
    logger.info(f"FILTERING BY SITE - Percentile {percentile*100}%")
    logger.info(f"{'='*80}")
    logger.info(f"Total sites found: {len(sites)}")
    
    popular_questions_list = []
    
    for site in sites:
        site_questions = df_questions[df_questions['site_alias'] == site]
        
        if site_questions.empty:
            logger.warning(f"No questions found for site {site}")
            continue
        
        logger.info(f"\nSite: {site}")
        logger.info(f"Total questions: {len(site_questions)}")
        
        site_quantiles = site_questions[[
            'answer_count', 'view_count', 'score', 'comment_count']].quantile(percentile)
        
        logger.info(f"Thresholds (percentile {percentile*100}%):")
        logger.info(f"  answer_count >= {site_quantiles['answer_count']:.2f}")
        logger.info(f"  view_count >= {site_quantiles['view_count']:.2f}")
        logger.info(f"  score >= {site_quantiles['score']:.2f}")
        logger.info(f"  comment_count >= {site_quantiles['comment_count']:.2f}")
        
        mask = (
            (site_questions['answer_count'] >= site_quantiles['answer_count']) &
            (site_questions['view_count'] >= site_quantiles['view_count']) &
            (site_questions['score'] >= site_quantiles['score']) &
            (site_questions['comment_count'] >= site_quantiles['comment_count'])
        )
        
        site_popular = site_questions[mask]
        logger.info(f"Popular questions found: {len(site_popular)}")
        
        if not site_popular.empty:
            popular_questions_list.append(site_popular)
    
    if not popular_questions_list:
        logger.warning("No questions meet popularity criteria in any site")
        return
    
    all_popular_questions = pd.concat(popular_questions_list, ignore_index=True)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"FILTERING SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total popular questions (all sites): {len(all_popular_questions)}")

    popular_question_ids = set(all_popular_questions['question_id'])
    popular_related = df[df['question_id'].isin(popular_question_ids)]

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    popular_related.to_csv(output_csv, index=False, quoting=csv.QUOTE_MINIMAL)

    logger.info(f"\nTotal records saved to {output_csv}: {len(popular_related)}")
    
    type_counts = popular_related['type'].value_counts()
    logger.info(f"  Questions: {type_counts.get('question', 0)}")
    logger.info(f"  Answers: {type_counts.get('answer', 0)}")
    logger.info(f"  Comments: {type_counts.get('comment', 0)}")

    logger.info(f"\n{'='*80}")
    logger.info("FINAL COUNT BY SITE:")
    logger.info(f"{'='*80}")
    
    site_type_counts = popular_related.groupby(['site_alias', 'type']).size().unstack(fill_value=0)
    
    for site in site_type_counts.index:
        q_count = site_type_counts.loc[site, 'question'] if 'question' in site_type_counts.columns else 0
        a_count = site_type_counts.loc[site, 'answer'] if 'answer' in site_type_counts.columns else 0
        c_count = site_type_counts.loc[site, 'comment'] if 'comment' in site_type_counts.columns else 0
        
        logger.info(f"{site}:")
        logger.info(f"  Questions: {q_count}")
        logger.info(f"  Answers: {a_count}")
        logger.info(f"  Comments: {c_count}")
        logger.info(f"  Total: {q_count + a_count + c_count}")


def main():
    """Main function used by the pipeline"""
    logger.info("--- STEP 6: Filtering popular posts ---")
    filter_popular_posts(CONNECTED_POSTS, FILTRED_POSTS, percentile=0.75)
    logger.info("=== Step 6 completed successfully ===")


if __name__ == "__main__":
    main()