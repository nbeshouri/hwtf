from .key_value_store import KeyValueStore
from . import utils
from bs4 import BeautifulSoup
import bz2
import re
import os
import joblib
from . import transforms


DB_PATH = '/Users/nbeshouri/Downloads/wiki.sqlite'
DUMP_PATH = '/Users/nbeshouri/Downloads/enwiki-20180520-pages-articles.xml.bz2'
DB_PATH = '/Volumes/Data 1/Not Backed Up/Temp/wiki.sqlite'

data_dir_path = os.path.join(os.path.dirname(__file__), 'data')


def get_pages_with_category(category_patterns, title_black_list=None, limit=None):
    
    title_to_page = {}
    
    def process_page(text):
        title = re.search(r'<title>(.+)</title>', text).group(1)
        
        black_list = [
            '(disabiguation)', 
            'List of', 
            'Category:',
            'Template:',
            'File:'
        ]
        
        if title_black_list is not None:
            black_list = black_list + title_black_list
        
        for title_pattern in black_list:
            if title_pattern in title:
                return
        
        if '<redirect>' in text:
            return
        
        matched = False
        for pattern in category_patterns:
            pattern = r'\[Category:' + pattern + r'\]'
            match = re.search(pattern, text)
            if match is not None:
                matched = True
                break
        
        if not matched:
            return
                    
        soup = BeautifulSoup(text, 'lxml')
        text_node = soup.find('text')
        article_text = text_node.get_text()
        title_to_page[title] = article_text

        if len(title_to_page) % 1000 == 0:
            print('Articles found:', len(title_to_page), 'Last title:', title)
    
    # TODO: Readlines?    
    with bz2.open(DUMP_PATH, 'rt', encoding='utf-8') as f:
        article_lines = None
        for line in f:
            if limit is not None and len(title_to_page) > limit:
                break
            
            if '<page>' in line:
                article_lines = []
            if article_lines is not None:
                article_lines.append(line)
            if '</page>' in line:            
                text = ''.join(article_lines)
                
                process_page(text)    
                
                # try:
                #     process_page(text)    
                # except Exception as e:
                #     print(e)
                article_lines = None
                
    return title_to_page


def de_wiki(text, truncation_patterns=None, remove_section_names=False):
    # TODO: The casting section shouldn't be dumped if its the main section.
    patterns_to_remove = [
        r'\<ref.*?\</ref\>', 
        r'{{[^{]+?}}',  # Some of these do contain content, e.g. {{c.|lk=no|1100}} and {{nihongo|'''Prince Zuko'''|祖寇|Zǔ Kòu}}
        r'{{[^{]+?}}',  # HACK: Repeat pattern for nested versions that sometimes appear.
        r'{{[^{]+?}}',
        r'<!--.*?-->',  # Comments.
        r'\[\[File:.+?(?=\n)',
        r'{\|.*?\|}',
        r'={2,10}((See also)|(Notes)|(Sources)|(References)|(Bibliography))={2,10}.*',
    ]

    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=(re.MULTILINE | re.DOTALL | re.IGNORECASE))

    if truncation_patterns is not None:
        for truncation_pattern in truncation_patterns:
            text = re.split(truncation_pattern, text, flags=re.IGNORECASE)[0]
    
    if remove_section_names:
        text = re.sub(r'={2,10}.*?={2,10}', '', text)
    
    patterns_to_sub = [
        (r'\[\[([^|]+?)\]\]', r'\1'),
        (r'\[\[(.+?)\|(.+?)\]\]', r'\2'), 
        (r"'''(.+?)'''", r'\1'),
        (r"''(.+?)''", r"\1"),
        (r"<nowiki>(.+?)</nowiki>", r"\1"), 
        (r'\n+', r'\n\n'),
        (r'  ', ' '),
        (r'&nbsp;', ' ')
    ]

    for pattern, replacement in patterns_to_sub:
        text = re.sub(pattern, replacement, text)
        
    
            
    
        
        

    return text.strip()        


# def de_wiki(text, trucation_patterns=[]):
# 
#     patterns_to_remove = [
#         r'\<ref.*?\</ref\>', 
#         r'{{[^{]+?}}',  # Some of these do contain content, e.g. {{c.|lk=no|1100}} and {{nihongo|'''Prince Zuko'''|祖寇|Zǔ Kòu}}
#         r'{{[^{]+?}}',  # HACK: Repeat pattern for nested versions that sometimes appear.
#         r'{{[^{]+?}}',
#         r'\[\[File:.+?(?=\n)',
#         r'={2,5}((See also)|(Notes)|(Sources)|(References)|(Bibliography)|(' + stop_at_section + '))={2,5}.*'
#     ]
# 
#     for pattern in patterns_to_remove:
#         text = re.sub(pattern, '', text, flags=(re.MULTILINE | re.DOTALL))
# 
#     patterns_to_sub = [
#         (r'\[\[([^|]+?)\]\]', r'\1'),
#         (r'\[\[(.+?)\|(.+?)\]\]', r'\2'), 
#         (r"'''(.+?)'''", r'\1'),
#         (r"''(.+?)''", r"\1"),
#         (r"<nowiki>(.+?)</nowiki>", r"\1"), 
#         (r'\n+', r'\n\n')
#     ]
# 
#     for pattern, replacement in patterns_to_sub:
#         text = re.sub(pattern, replacement, text)
# 
#     return text.strip()   

def get_paragraphs(text):
    text = re.sub(r'==.+==', '', text)
    paragraphs = [p.strip() for p in text.split('\n')]
    return [p for p in paragraphs if p]
    
    
def convert_articles(name_to_article, limit=None):
    tokenized_articles = {}
    lemmatized_articles = {}
    for article_name, text in name_to_article.items():
        character_name = re.sub(r'\(.*\)', '', article_name)
        text = de_wiki(text)
        tokenized_sents = []
        lemmatized_sents = []
        paragrahs = get_paragraphs(text)
        for paragraph in get_paragraphs(text):
            subject_tokens = transforms.get_subject_tokens(paragraph, character_name)
            for subject_token in subject_tokens:
                extracted = transforms.extract_phrase(subject_token, character_name)
                tokenized_sent = transforms.tokens_to_str(
                    extracted, 
                    spaces_before_punct=True,
                    lower_case=True,
                    remove_numbers=True
                )
                tokenized_sents.append(tokenized_sent)
                lemmatized_sent = transforms.tokens_to_str(
                    extracted, 
                    remove_punct=True, 
                    convert_to_lemmas=True,
                    remove_stop_words=True,
                    lower_case=True,
                    remove_numbers=True
                )
                lemmatized_sents.append(lemmatized_sent)
        tokenized_articles[article_name] = tokenized_sents
        lemmatized_articles[article_name] = lemmatized_sents
        if len(tokenized_articles) % 100 == 0:
            print('Processed:', len(tokenized_articles), 'Last:', article_name)
        if limit is not None and len(tokenized_articles) == limit:
            break
    return tokenized_articles, lemmatized_articles
        

def sandbox1():
    file_name = 'character_bios.pickle'
    load_path = os.path.join(data_dir_path, file_name)
    name_to_article = joblib.load(load_path)
    tokenized_articles, lemmatized_articles = convert_articles(name_to_article, limit=None)
    
    file_name = 'character_bios_tokenized.pickle'
    utils.archive_data(file_name)
    dump_path = os.path.join(data_dir_path, file_name)
    joblib.dump(tokenized_articles, dump_path, compress=3)
    
    file_name = 'character_bios_lemmatized.pickle'
    utils.archive_data(file_name)
    dump_path = os.path.join(data_dir_path, file_name)
    joblib.dump(lemmatized_articles, dump_path, compress=3)
    
    

def sandbox():
    
    title_black_list = utils.load_values('character_article_title_black_list.csv')
    
    patterns = [
        r'.+characters in.+',
        r'.*characters introduced in',
        r'Characters in.+'
    ]
    
    title_to_page_raw = get_pages_with_category(
        patterns, 
        title_black_list=title_black_list, 
        limit=125000
    )
    title_to_page = {}
    for name, article in title_to_page_raw.items():
        match = re.search('==.*(Characters|Cast).*==', article, re.IGNORECASE)
        if not match:
            title_to_page[name] = article
    
    file_name = 'character_bios.pickle'
    path = os.path.join(data_dir_path, file_name)
    utils.archive_data(file_name)
    joblib.dump(title_to_page, path, compress=3)
    

def sandbox3():
    patterns = [
        r'Films.+',
    ]
    title_to_page = get_pages_with_category(patterns, limit=125000)
    file_name = 'films.pickle'
    path = os.path.join(data_dir_path, file_name)
    utils.archive_data(file_name)
    joblib.dump(title_to_page, path, compress=3)
    
