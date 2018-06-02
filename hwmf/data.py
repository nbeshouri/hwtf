
from . import wikipedia
from . import utils
from . import transforms


def get_character_articles(remove_section_names=True, remove_ents=True, lemmatize=True, tokenize=False, limit=None, remove_black_listed=True):
    name_to_article = utils.load_data('character_bios.pickle')
    sections = ['Critical reception', 'Portrayal', 'Casting', 'Reception', 
                'In popular culture', 'Parodies', 'Production', 'Criticism', 'Reaction', 
                'in other media']
    patterns = [r'={2,10}.*?' + s + r'.*?={2,10}' for s in sections]
    output = {}
    for name, article in name_to_article.items():
        text = wikipedia.de_wiki(article, truncation_patterns=patterns, remove_section_names=remove_section_names)
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


def get_character_extracts(limit=None, remove_black_listed=True):
    # TODO:_Move stuff around so that it looks more like the above...
    name_to_article = utils.load_data('character_bios.pickle')
    tokenized_articles, lemmatized_articles = wikipedia.convert_articles(name_to_article, limit=limit)
    # output_tokenized = {}
    # for name, sents in tokenized_articles.items():
    #     text = ' '.join(sents)
    #     if remove_black_listed:
    #         text = transforms.remove_black_listed(text)
    #     output_tokenized[name] = text

    output_lemmatized = {}
    for name, sents in lemmatized_articles.items():
        text = ' '.join(sents)
        if remove_black_listed:
            text = transforms.remove_black_listed(text)
        output_lemmatized[name] = text

    return tokenized_articles, output_lemmatized

