import spacy

_model_cache = {}


def get_minimal_model():
    if 'minimal' not in _model_cache:
        _model_cache['minimal'] = spacy.load('en_core_web_sm', disable=['parser', 'tagger', 'ner'])
    return _model_cache['minimal']


def get_large_model():
    if 'large' not in _model_cache:
        nlp = spacy.load('en_core_web_lg')
        # Due to a bug, this language model doesn't contain
        # stop words, so we fix that here.
        for word in nlp.Defaults.stop_words:
            lex = nlp.vocab[word]
            lex.is_stop = True
        _model_cache['large'] = nlp
    
    return _model_cache['large']