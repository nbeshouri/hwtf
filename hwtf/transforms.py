"""
This module contains text transformation functions.

"""


import re
import spacy
from . import utils


_word_black_list = sorted(utils.load_values('character_article_word_black_list.csv'), 
                          key=lambda x: -len(x))
_model_cache = {}


#
# CLAUSE EXTRACTION
#


def extract_phrase(subject_token, target_name):
    """
    Extract a list of tokens that are in the same clause as the target.
    
    Args:
        subject_token (spacy.tokens.token.Token): The token of the subject
            of the clause you want extracted.
        target_name (str): The full name of the target subject.
    
    Returns:
        list: A list of both spacy tokens and strings representing 
            meta-tokens.
    
    """
    # Iterate over all tokens in the subtree, replacing some with
    # meta-tokens.
    selected_tokens = []
    for token in subject_token.head.subtree:
        # If the token is a space or newline, continue.
        if not token.text.strip():
            continue        
        # Otherwise, we're going to either keep the token as is or
        # replace it with a meta-token.
        if (token == subject_token 
                or (subject_token == token.head 
                    and token.dep_ == 'compound' 
                    and token.text.lower() in target_name.lower())
                or ('nsubj' in token.dep_ and token.pos_ == 'PRON')):
            selected_tokens.append('<SUBJECT>')
        elif token.ent_type_ and not token.is_punct:
            selected_tokens.append(f'<ENITY>')
        elif token.pos_ == 'PROPN':
            selected_tokens.append('<ENITY>')
        else:
            selected_tokens.append(token)        
    
    # The list of tokens created above contains duplicate <ENITY> tokens
    # that have to be cleaned up. Here 
    output = []
    for selected_token in selected_tokens:
        # Store some bools for use in below if statements.
        token_is_string = isinstance(selected_token, str)
        prev_token_is_string = output and isinstance(output[-1], str)
        prev_token_is_meta = prev_token_is_string and '<' in output[-1]
        cur_and_prev_are_meta = (output and token_is_string 
                                 and prev_token_is_string and '<' in selected_token
                                 and '<' in output[-1])
        
        # TODO: Replace the below series of if ... continue statements
        # a single if ... else statement. 
        
        # Remove quotes around some <ENTITY>s (e.g. works of art).
        # These interfer with joining neighboring <ENITY> tags 
        # together (and also look funny).
        if (len(output) >= 2 
                and not token_is_string 
                and selected_token.text == '"' 
                and prev_token_is_string 
                and '<' in output[-1]
                and not isinstance(output[-2], str) 
                and output[-2].text == '"'):
            
            meta_token = output.pop()
            output.pop()  # The quotation mark.
            
            # If there's already a meta char, just assume the one we 
            # just popped is a duplicate and don't bother reappending it.
            if not output or not isinstance(output[-1], str) or '<' not in output[-1]: 
                output.append(meta_token)
            continue
        
        # Prevent Spider-Man from becoming <ENITY>-<ENITY>.
        if not token_is_string and selected_token.text == '-' and prev_token_is_meta:
            continue
        
        if cur_and_prev_are_meta:
            if '<SUBJECT>' in (selected_token, output[-1]):
                output.pop()
                output.append('<SUBJECT>')
            continue
        
        output.append(selected_token)
    
    return output


def get_subject_tokens(text, target_name):
    """
    Extract subject tokens for clauses about the target.
    
    Args:
        text (str): The text that contains sentences about the target.
        target_name (str): The name of the 
    
    Returns:
        List[spacy.tokens.token.Token]: Tokens representing the subjects
            of clauses about target_name.
    
    """
    remove_patterns = [r'\(.+?\)', r'\[.+?\]', r'#']
    for pattern in remove_patterns:
        text = re.sub(pattern, '', text)
    
    nlp_model = get_large_model()
    parsed = nlp_model(text)
    
    is_subject = []
    subjects_of_interest = []
    for token in parsed:
        token_is_subject = ('nsubj' in token.dep_ 
                            and token.pos_ == 'PROPN' 
                            and token.text.lower() in target_name.lower())
        token_is_subj_pron = (token.pos_ == 'PRON' and is_subject and is_subject[-1])
        if token_is_subject or token_is_subj_pron:
            is_subject.append(True)
            subjects_of_interest.append(token)
        else:
            is_subject.append(False)
    
    # Keep the subjects with the highest level root.
    output = []
    for token in subjects_of_interest:
        for other_token in subjects_of_interest:
            if token != other_token and other_token.head.is_ancestor(token):
                break
        else:
            output.append(token)
    
    return output


def tokens_to_str(tokens, spaces_before_punct=False, cap_first_word=True, 
                  add_period=True, convert_to_lemmas=False, remove_stop_words=False, 
                  remove_punct=False, lower_case=False, remove_numbers=False):    
    """Convert a list of spacy tokens and str meta-tokens into a single sentence string."""
    # TODO: This function is one big hack. Refractor or replace.
    
    if add_period and not remove_punct:
        if isinstance(tokens[-1], str) or not tokens[-1].is_punct:
            tokens.append('.')
        elif tokens[-1].is_punct:
            if tokens[-1].text in ',:;':
                tokens.pop()
                tokens.append('.')    
    
    strings = []
    for i, token in enumerate(tokens):
        is_first_word = i == 0
        
        # TODO: Most of these, especially skip_space, can be simplified
        # by looking at the stings and not the tokens. Much of the
        # complexity is dealing with the fact that (1) the inputs can
        # either either strings or spacy tokens.
        cur_not_string = not isinstance(token, str)
        last_two_not_str = i >= 1 and cur_not_string and not isinstance(tokens[i - 1], str)
        last_three_not_str = i >= 2 and last_two_not_str and not isinstance(tokens[i - 2], str)
        is_hyphen = cur_not_string and token.text == '-'
        is_word_after_hyphen = last_two_not_str and not token.is_punct and tokens[i - 1].text == '-'    
        cur_is_punct = ((cur_not_string and (token.is_punct or token.dep_ == 'case' or token.text == "n't")) 
                        or not cur_not_string and token in ('.'))
        is_open_quote = cur_not_string and token.text == '"' and sum(1 for s in strings if s == '"') % 2 == 0
        last_is_open_quote = strings and strings[-1] == '"' and sum(1 for s in strings if s == '"') % 2 != 0
        skip_space = is_first_word or ((is_hyphen or is_word_after_hyphen) and not remove_punct)
        
        if remove_stop_words and cur_not_string and token.is_stop:
            continue
            
        if remove_numbers and cur_not_string and token.pos_ == 'NUM':
            continue
            
        if remove_punct and cur_not_string and token.is_punct:
            continue
        
        if not spaces_before_punct:
            skip_space = True if cur_is_punct and not spaces_before_punct else skip_space
            skip_space = False if is_open_quote else skip_space
            skip_space = True if last_is_open_quote else skip_space
        
        if not isinstance(token, str):
            if not convert_to_lemmas:
                token = token.text
            else:
                token = token.lemma_
        
        token = token.strip()
        if not token:
            continue
        
        if not skip_space:
            strings.append(' ')
            
        if cap_first_word and not lower_case and is_first_word and '<' not in token:
            token = token.capitalize()
            
        if lower_case and '<' not in token:
            token = token.lower()
            
        strings.append(token)
    
    # TODO the strip here shouldn't be needed, but some of them are starting with 
    # with blanks in lemmatized version. It's probably the space being added after 
    # `if not skip_space:`
    return ''.join(strings).strip()  


def filter_subtree(head, rules):
    """Return the subtree of the head rule based replacements."""
    for rule, replacement in rules:
        if rule(head):
            if callable(replacement):
                replacement = replacement(head)
            return [replacement]
    if len(list(head.children)) == 0:
        return [head]
    output = []
    for child in head.lefts:
        output.extend(get_subtree(child, rules))
    output.append(head)
    for child in head.rights:
        output.extend(get_subtree(child, rules))
    
    return [token for token in output if token]


#
# TEXT FILTERING
#


def remove_entities_and_prop_nouns(text):
    """Remove named entities and proper nouns from the input text."""
    nlp_model = get_large_model()
    output = []
    for token in nlp_model(text):
        if (token.pos_ == 'PROPN' 
                or token.lemma_ == '-PRON-'
                or token.text == "'s"
                or token.ent_type_ 
                or not token.is_ascii 
                or not token.text.strip()):
            continue
        output.append(token.text)
    return ' '.join(output)


def remove_black_listed_words(text):
    """Black listed terms from the input text."""
    for pattern in _word_black_list:
        pattern = r'\b' + pattern + r'\b'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s{2,}', ' ', text)
    text = text.strip()
    return text


#
# SIMPLE NLP
#


def to_lemmas(text):
    """Convert words in `text` to a string of lemmas."""
    # TODO: Option to leave hypens in tact?
    # TODO: Some of this stuff should be optional.
    # TODO: Change name to lemmatize.
    # TODO: This should share code with tokenize.
    nlp_model = get_minimal_model()
    lemmas = []
    text = text.lower()
    for token in nlp_model(text):
        if (token.is_ascii 
                and not token.is_punct 
                and not token.is_stop 
                and not token.is_digit
                and token.text.strip() 
                and len(token.text) < 15):
            lemmas.append(token.lemma_.strip())
    return ' '.join(lemmas)


def to_tokens(text):
    """Convert words in `text` to a string of tokens."""
    tokens = []
    allowed_punct = set('.?!,')
    nlp_model = get_minimal_model()
    for token in nlp_model(text):
        if ((token.is_punct and token.text not in allowed_punct)
                or len(token.text) > 15
                or not token.is_ascii
                or token.text == ' '):
            continue
        tokens.append(token.text)
    return ' '.join(tokens)


def get_polarity(text):
    """Get average pos/neg polarity of a string."""
    from textblob import TextBlob
    blob = TextBlob(text)
    return blob.sentiment.polarity


#
# NLP MODEL MANAGMENT
#


def get_minimal_model():
    """Return a spacy model without parsing, tagging, or ner."""
    if 'minimal' not in _model_cache:
        _model_cache['minimal'] = spacy.load(
            'en_core_web_sm', 
            disable=['parser', 'tagger', 'ner']
        )
    return _model_cache['minimal']


def get_large_model():
    """Return the large spacy model everything turned on."""
    if 'large' not in _model_cache:
        nlp = spacy.load('en_core_web_lg')
        # Due to a bug, this language model doesn't contain
        # stop words, so we fix that here.
        for word in nlp.Defaults.stop_words:
            lex = nlp.vocab[word]
            lex.is_stop = True
        _model_cache['large'] = nlp
    
    return _model_cache['large']
