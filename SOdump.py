import os
import csv
import xml.etree.ElementTree as ET
import datetime


SITES = {
    "stackoverflow": "stackoverflow.com",
    "crypto": "crypto.stackexchange.com",
    "security": "security.stackexchange.com"
}

# tags
QUESTION_TAGS = {
    "stackoverflow": ["python", "encryption", "rsa"],
    "crypto": ["encryption", "rsa"],
    "security": ["encryption", "rsa"]
}


BASE_DIR = "./Extraidos dump"  

#CSV que vão sair
QUESTIONS_CSV = "questions_dump.csv"
ANSWERS_CSV = "answers_dump.csv"
COMMENTS_CSV = "comments_dump.csv"


question_features = [
    'site', 'tag', 'question_id', 'accepted_answer_id', 'answer_count',
    'creation_date', 'is_answered', 'last_activity_date', 'last_edit_date',
    'owner_id', 'owner_reputation', 'score', 'view_count', 'title', 'body'
]
answer_features = [
    'site', 'tag', 'answer_id', 'question_id', 'comment_count',
    'creation_date', 'is_accepted', 'last_activity_date',
    'owner_reputation', 'owner_id', 'score', 'body'
]
comment_features = [
    'site', 'tag', 'comment_id', 'post_id', 'creation_date',
    'edited', 'owner_reputation', 'owner_id', 'score', 'body'
]


def initiateCSVs():
    #criação dos csv
    if not os.path.exists(QUESTIONS_CSV):
        with open(QUESTIONS_CSV, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(question_features)
    if not os.path.exists(ANSWERS_CSV):
        with open(ANSWERS_CSV, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(answer_features)
    if not os.path.exists(COMMENTS_CSV):
        with open(COMMENTS_CSV, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(comment_features)

def safe_date(ts):
    
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.strftime('%Y/%m/%d, %H:%M:%S')
    except Exception:
        
        return ts



def parse_posts(site_alias):
    
    site_name = SITES[site_alias]
    tags_of_interest = QUESTION_TAGS.get(site_alias, [])
    folder = os.path.join(BASE_DIR, site_name)
    posts_path = os.path.join(folder, "Posts.xml")
    if not os.path.exists(posts_path):
        print(f"[{site_alias}] ⚠ Posts.xml não encontrado em: {posts_path}")
        return

    print(f"[{site_alias}] Processando Posts: {posts_path}")
    
    context = ET.iterparse(posts_path, events=("start",))
    for _, elem in context:
        if elem.tag == "row":
            post_type = elem.attrib.get("PostTypeId")  
            tags_field = elem.attrib.get("Tags", "")
            
            if post_type == "1":
                
                if any(f"<{tag}>" in tags_field for tag in tags_of_interest):
                    row = [
                        site_alias,
                        ";".join(tags_of_interest),
                        elem.attrib.get("Id"),
                        elem.attrib.get("AcceptedAnswerId", ""),
                        elem.attrib.get("AnswerCount", "0"),
                        safe_date(elem.attrib.get("CreationDate", "")),
                        elem.attrib.get("IsAnswered", ""),  
                        safe_date(elem.attrib.get("LastActivityDate", "")),
                        safe_date(elem.attrib.get("LastEditDate", "")),
                        elem.attrib.get("OwnerUserId", ""),
                        elem.attrib.get("OwnerReputation", ""),
                        elem.attrib.get("Score", "0"),
                        elem.attrib.get("ViewCount", "0"),
                        elem.attrib.get("Title", ""),
                        elem.attrib.get("Body", "")
                    ]
                    with open(QUESTIONS_CSV, "a", encoding="utf-8", newline="") as f:
                        csv.writer(f).writerow(row)

            
            elif post_type == "2":
                row = [
                    site_alias,
                    ";".join(tags_of_interest),
                    elem.attrib.get("Id"),
                    elem.attrib.get("ParentId", ""),
                    elem.attrib.get("CommentCount", "0"),
                    safe_date(elem.attrib.get("CreationDate", "")),
                    elem.attrib.get("IsAccepted", ""),  
                    safe_date(elem.attrib.get("LastActivityDate", "")),
                    elem.attrib.get("OwnerReputation", ""),
                    elem.attrib.get("OwnerUserId", ""),
                    elem.attrib.get("Score", "0"),
                    elem.attrib.get("Body", "")
                ]
                with open(ANSWERS_CSV, "a", encoding="utf-8", newline="") as f:
                    csv.writer(f).writerow(row)
        elem.clear()

def parse_comments(site_alias):
    
    site_name = SITES[site_alias]
    tags_of_interest = QUESTION_TAGS.get(site_alias, [])
    folder = os.path.join(BASE_DIR, site_name)
    comments_path = os.path.join(folder, "Comments.xml")
    if not os.path.exists(comments_path):
        print(f"[{site_alias}] ⚠ Comments.xml não encontrado em: {comments_path}")
        return

    print(f"[{site_alias}] Processando Comments: {comments_path}")
    context = ET.iterparse(comments_path, events=("start",))
    for _, elem in context:
        if elem.tag == "row":
            row = [
                site_alias,
                ";".join(tags_of_interest),
                elem.attrib.get("Id"),
                elem.attrib.get("PostId", ""),
                safe_date(elem.attrib.get("CreationDate", "")),
                elem.attrib.get("Edited", "False"),
                elem.attrib.get("UserId", ""),
                "",  
                elem.attrib.get("Score", "0"),
                elem.attrib.get("Text", "")
            ]
            with open(COMMENTS_CSV, "a", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow(row)
        elem.clear()



if __name__ == "__main__":
    print("Inicializando CSVs …")
    initiateCSVs()

    for site_alias in SITES.keys():
        parse_posts(site_alias)
        parse_comments(site_alias)

    print("Processamento concluído!")
