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


def get_pages_with_category(category_patterns, limit=None):
    
    title_to_page = {}
    
    def process_page(text):
        title = re.search(r'<title>(.+)</title>', text).group(1)
        
        # TODO: This should be broken down into two lists.
        # as this function could be used generally. Some of the
        # more later ones shouldn't actually matter because their
        # name won't actually match any subjects.
        title_patterns = [
            '(disabiguation)', 
            'List of', 
            ' and ', 
            ' kids', 
            'Knights', 
            'X-Men', 
            'Category:',
            '(characters),
            'The League of Extraordinary Gentlemen', 
            'The Fabulous Furry Freak Brothers',
            'The Emperor\'s New Clothes'
        ]
        
        for title_pattern in title_patterns:
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
                try:
                    process_page(text)    
                except Exception as e:
                    print(e)
                article_lines = None
                
    return title_to_page


def de_wiki(text):
    patterns_to_remove = [
        r'\<ref.*?\</ref\>', 
        r'{{[^{]+?}}',  # Some of these do contain content, e.g. {{c.|lk=no|1100}} and {{nihongo|'''Prince Zuko'''|祖寇|Zǔ Kòu}}
        r'{{[^{]+?}}',  # HACK: Repeat pattern for nested versions that sometimes appear.
        r'{{[^{]+?}}',
        r'\[\[File:.+?(?=\n)',
        r'={2,5}((See also)|(Notes)|(Sources)|(References))={2,5}.*'
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=(re.MULTILINE | re.DOTALL))
    
    patterns_to_sub = [
        (r'\[\[([^|]+?)\]\]', r'\1'),
        (r'\[\[(.+?)\|(.+?)\]\]', r'\2'), 
        (r"'''(.+?)'''", r'\1'),
        (r"''(.+?)''", r"\1"),
        (r"<nowiki>(.+?)</nowiki>", r"\1"), 
        (r'\n+', r'\n\n')
    ]
    
    for pattern, replacement in patterns_to_sub:
        text = re.sub(pattern, replacement, text)
        
    return text.strip()        


def get_paragraphs(text):
    text = re.sub(r'==.+==', '', text)
    paragraphs = [p.strip() for p in text.split('\n')]
    return [p for p in paragraphs if p]
    
    
def convert_articles(name_to_article, lemmatize=False, limit=None):
    converted = {}
    for i, (article_name, text) in enumerate(name_to_article.items()):
        print(article_name)
        character_name = re.sub(r'\(.*\)', '', article_name)
        text = de_wiki(text)
        sentences = []
        paragrahs = get_paragraphs(text)
        # print('Paragraphs:', len(paragrahs))
        for paragraph in get_paragraphs(text):
            subject_tokens = transforms.get_subject_tokens(paragraph, character_name)
            # print('Subject tokens:', len(subject_tokens))
            for subject_token in subject_tokens:
                extracted = transforms.extract_phrase(subject_token, character_name)
                extracted = transforms.tokens_to_str(extracted, spaces_before_punct=True)
                sentences.append(extracted)
        converted[article_name] = sentences
        if limit is not None and i == limit:
            break
    return converted
        

def sandbox1():
    file_name = 'character_bios.pickle'
    load_path = os.path.join(data_dir_path, file_name)
    name_to_article = joblib.load(load_path)
    converted = convert_articles(name_to_article, limit=1000)
    file_name = 'character_bios_processed.pickle'
    utils.archive_data(file_name)
    dump_path = os.path.join(data_dir_path, file_name)
    joblib.dump(converted, dump_path, compress=3)
    
    

def sandbox():
    patterns = [
        r'.+characters in.+',
        r'.*characters introduced in' 
    ]
    title_to_page = get_pages_with_category(patterns, limit=125000)
    file_name = 'character_bios.pickle'
    path = os.path.join(data_dir_path, file_name)
    utils.archive_data(file_name)
    joblib.dump(title_to_page, path, compress=3)
