"""
This module contains a collection of functions used to generate different
versions of the data set.

Todo:
    * These need testing after refactoring.
    * All of these should have the option all save the data to disk.

"""

from . import wikipedia
from . import utils
from . import transforms


CHAR_ARTICLES_FILE_NAME = 'character_bios.pickle'


def get_character_extracts(limit=None, remove_black_listed=True):
    """Return a dict of article extracts ready for training."""
    name_to_article = utils.load_data(CHAR_ARTICLES_FILE_NAME)
    tokenized_articles, lemmatized_articles = wikipedia.convert_articles(name_to_article, limit=limit)
    
    def join_and_filter(name_to_article):    
        output = {}
        for name, sents in name_to_article.items():
            text = ' '.join(sents)
            if remove_black_listed:
                text = transforms.remove_black_listed(text)
            output[name] = text
        return output
        
    tokenized_articles = join_and_filter(tokenized_articles)
    lemmatized_articles = join_and_filter(lemmatized_articles)
    
    return tokenized_articles, lemmatized_articles


def get_character_cleaned_articles(remove_section_names=True, remove_ents=False, lemmatize=False, 
                           tokenize=True, limit=None, remove_black_listed=False):
    """Return a dict of articles ready for training."""                       
    name_to_article = utils.load_data(CHAR_ARTICLES_FILE_NAME)
    output = {}
    for name, article in name_to_article.items():
        text = wikipedia.de_wiki(article, remove_section_names=remove_section_names)
        if remove_black_listed:
            text = transforms.remove_black_listed(text)
        if remove_ents:
            text = transforms.remove_ents(text)
        elif lemmatize:
            text = transforms.to_lemmas(text)
        elif tokenize:
            text = transforms.to_tokens(text)
        output[name] = text
        if limit is not None and len(output) >= limit:
            break
    return output


def get_character_articles():
    """Get a dict of raw character related articles from the Wikipedia dump."""
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
        # Check to see if article is really about a collection of characters.
        match = re.search('==.*(Characters|Cast).*==', article, re.IGNORECASE)
        if not match:
            title_to_page[name] = article
    
    return title_to_page


def get_movie_articles():
    """Get a dict of raw film summaries from the Wikipedia dump."""
    patterns = [
        r'Films.+',
    ] 
    return get_pages_with_category(patterns, limit=125000)
