from . import utils
from bs4 import BeautifulSoup
import bz2
import re
import os
import joblib
from . import transforms


DUMP_PATH = '/Users/nbeshouri/Downloads/enwiki-20180520-pages-articles.xml.bz2'

 
def get_article_iterator():
    """Return a generator that yields the raw XML for each article."""
    with bz2.open(DUMP_PATH, 'rt', encoding='utf-8') as f:
        article_lines = None
        for line in f:
            # A the start of each page node, create a list to collect
            # the lines (opening and closing <page> tags occur on
            # their own lines in the dump).
            if '<page>' in line:
                article_lines = []
            # If inside a page node, save the line (article_lines is
            # None when outside a page node).
            if article_lines is not None:
                article_lines.append(line)
            # If this is the last line in the page node, yield the 
            # complete article text and reset article_lines to None.
            if '</page>' in line:            
                yield ''.join(article_lines)
                article_lines = None
                

def get_pages_with_category(category_patterns, title_black_list=None, limit=None):
    """
    Get a dict of articles whose categories match the supplied patterns.
    
    Args:
        category_patterns (List[str]): A list of patterns used to select
            articles. Only articles with these patterns will be returned.
        title_black_list (List[str]): An optional list of patterns used 
            to exclude articles based on their title.
        limit (int): An optional limit on the number of articles 
            to return.
        
    Returns:
        Dict[str, str]: A dictionary mapping from article titles article
            text. Note that this text is still in Wikitext markup.
    
    """
    
    black_list = [
        '(disabiguation)', 
        'List of', 
        'Category:',
        'Template:',
        'File:'
    ]
    
    # Extend black list.
    if title_black_list is not None:
        black_list += title_black_list
    
    category_patterns = [r'\[Category:' + pattern + r'\]' for pattern in category_patterns]
    
    # Collect all non-black listed non-redirect articles.
    title_to_page = {}
    
    for raw_article in get_article_iterator():
        title = re.search(r'<title>(.+)</title>', raw_article).group(1)
        
        # Continue if the title is black listed.    
        if utils.matches_patterns(black_list, title):
            continue
                
        # Continue if article is a redirect.
        if '<redirect>' in raw_article:
            continue
        
        # Continue if the article doesn't match any category patterns.
        if not utils.matches_patterns(category_patterns, raw_article):
            continue
        
        # Use bs4 to extract the article's text from the XML.                 
        soup = BeautifulSoup(raw_article, 'lxml')
        text_node = soup.find('text')
        article_text = text_node.get_text()
        title_to_page[title] = article_text

        if len(title_to_page) % 100 == 0:
            print('Articles found:', len(title_to_page), 'Last title:', title)
        
        if limit is not None and len(title_to_page) == limit:
            break
            
    return title_to_page


def de_wiki(text, remove_section_names=False):
    """Remove most of the Wikitext meta-text."""
    # TODO: The casting section shouldn't be dumped if its the main section.
    # TODO: Some of the {{...}} elements contain content e.g.
    # {{c.|lk=no|1100}} and {{nihongo|'''Prince Zuko'''|祖寇|Zǔ Kòu}}.
    
    patterns_to_remove = [
        r'\<ref.*?\</ref\>', 
        r'{{[^{]+?}}', 
        r'{{[^{]+?}}',  # HACK: Repeat pattern for nested versions that sometimes appear.
        r'{{[^{]+?}}',
        r'<!--.*?-->',  # These are Comments in Wikitext.
        r'\[\[File:.+?(?=\n)',
        r'{\|.*?\|}',
        r'<\w+>.*?</\w+>',
        r'={2,10} ((See also)|(Notes)|(Sources)|(References)|(Bibliography)) ={2,10}.*',
    ]

    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=(re.MULTILINE | re.DOTALL | re.IGNORECASE))
    
    if remove_section_names:
        text = re.sub(r'={2,}.*?={2,}', '', text)
    
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
    
    
def extract_phrases_about_subject(name_to_article, limit=None):
    """
    Convert raw articles to extracted strings about the article's subject.
    
    Args:
        name_to_article (Dict[str, str]): A dictionary mapping character
            names to their articles.
    
    Returns:
        tokenized_sents (Dict[str, str]): A dictionary mapping article
            names to a single string containing all the extracted
            phrases. These are lower case, but retain punctuation and
            stop words.
        lemmatized_sents (Dict[str, str]): A dictionary mapping article
            names to a single string containing all the extracted
            phrases. These are lower case, with stop words and
            punctuation removed.
            
    """
    
    tokenized_articles = {}
    lemmatized_articles = {}

    for article_name, text in name_to_article.items():
        character_name = re.sub(r'\(.*\)', '', article_name)
        text = de_wiki(text, remove_section_names=True)
        
        tokenized_sents = []
        lemmatized_sents = []
        paragrahs = (p.strip() for p in text.split('\n') if p.strip())
        
        for paragraph in paragrahs:
            # Extract spacy tokens representing mentions of the character.
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
        
        tokenized_articles[article_name] = ' '.join(tokenized_sents)
        lemmatized_articles[article_name] = ' '.join(lemmatized_sents)
        
        if len(tokenized_articles) % 100 == 0:
            print('Processed:', len(tokenized_articles), 'Last:', article_name)
        
        if limit is not None and len(tokenized_articles) == limit:
            break
    
    return tokenized_articles, lemmatized_articles
        

def sandbox1():
    file_name = 'character_bios.pickle'
    load_path = os.path.join(data_dir_path, file_name)
    name_to_article = joblib.load(load_path)
    tokenized_articles, lemmatized_articles = extract_phrases_about_subject(name_to_article, limit=None)
    
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
    
