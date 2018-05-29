"""
This module contains text transformation functions. It should probably
also contain some of the data manipulation funtions in models.py.

"""

import re
import spacy


nlp = spacy.load('en_core_web_lg')
# Due to a bug, this language model doesn't contain
# stop words, so we fix that here.
for word in nlp.Defaults.stop_words:
    lex = nlp.vocab[word]
    lex.is_stop = True


def tokens_to_str(tokens, spaces_before_punct=False, cap_first_word=True, add_period=True):
    tokens = list(tokens)
    
    if add_period:
        if isinstance(tokens[-1], str) or not tokens[-1].is_punct:
            tokens.append('.')
        elif tokens[-1].is_punct:
            if tokens[-1].text in ',:;':
                tokens.pop()
                tokens.append('.')    
    
    strings = []
    for i, token in enumerate(tokens):
        is_first_word = i == 0
        
        cur_not_string = not isinstance(token, str)
        last_two_not_str = i >= 1 and cur_not_string and not isinstance(tokens[i - 1], str)
        last_three_not_str = i >= 2 and last_two_not_str and not isinstance(tokens[i - 2], str)
        is_hyphen = cur_not_string and token.text == '-'
        is_word_after_hyphen = last_two_not_str and not token.is_punct and tokens[i - 1].text == '-'    
        cur_is_punct = (cur_not_string and (token.is_punct or token.dep_ == 'case' or token.text == "n't")) or not cur_not_string and token in ('.')   
        is_open_quote = cur_not_string and token.text == '"' and sum(1 for s in strings if s == '"') % 2 == 0
        last_is_open_quote = not is_first_word and strings[-1] == '"' and sum(1 for s in strings if s == '"') % 2 != 0
        skip_space = is_first_word or is_hyphen or is_word_after_hyphen
        
        if not spaces_before_punct:
            skip_space = True if cur_is_punct and not spaces_before_punct else skip_space
            skip_space = False if is_open_quote else skip_space
            skip_space = True if last_is_open_quote else skip_space
        
        
        if not isinstance(token, str):
            token = token.text
        
        token = token.strip()
        if not token:
            continue
        
        if not skip_space:
            strings.append(' ')
            
        if is_first_word and cap_first_word and '<' not in token:
            token = token.capitalize()
            
        strings.append(token)
        
    return ''.join(strings)


def extract_phrase(subject_token, target_name):
    selected_tokens = []
    for token in subject_token.head.subtree:
        if not token.text.strip():
            continue        
        if (token == subject_token 
                or (subject_token == token.head and token.dep_ == 'compound' and token.text.lower() in target_name.lower())
                or ('nsubj' in token.dep_ and token.pos_ == 'PRON')):
            selected_tokens.append('<SUBJECT>')
        elif token.ent_type_ and not token.is_punct:  # Sometimes empty/punct tokens have ents.
            selected_tokens.append(f'<ENITY>')
        elif token.pos_ == 'PROPN':
            selected_tokens.append('<ENITY>')
        else:
            selected_tokens.append(token)        
    
    output = []
    for selected_token in selected_tokens:
        token_is_string = isinstance(selected_token, str)
        prev_token_is_string = output and isinstance(output[-1], str)
        cur_and_prev_are_meta = output and token_is_string and prev_token_is_string and '<' in selected_token and '<' in output[-1]

        is_space_or_new_line = not token_is_string and not selected_token.text.strip()
        if is_space_or_new_line:
            continue
        
        if (len(output) >= 2 
                and not token_is_string 
                and selected_token.text == '"' 
                and prev_token_is_string 
                and '<' in output[-1]
                and not isinstance(output[-2], str) 
                and output[-2].text == '"'):
            
            meta_token = output.pop()
            output.pop()
            
            # If there's already a meta char, just assume the one we 
            # just popped is a duplicate and don't bother reappending it.
            if not output or not isinstance(output[-1], str) or '<' not in output[-1]: 
                output.append(meta_token)
            continue
            
        
        if cur_and_prev_are_meta or is_space_or_new_line:
            if '<SUBJECT>' in (selected_token, output[-1]):
                output.pop()
                output.append('<SUBJECT>')
        else:
            output.append(selected_token)
    
    return output


def get_subject_tokens(text, target_name):
    
    def subject_test(token):
        return 'nsubj' in token.dep_ and token.pos_ == 'PROPN' and token.text.lower() in target_name.lower()
    
    remove_patterns = [r'\(.+?\)', r'\[.+?\]']
    for pattern in remove_patterns:
        text = re.sub(pattern, '', text)
    
    parsed = nlp(text)
    
    is_subject = []
    subjects_of_interest = []
    for token in parsed:
        if subject_test(token) or (token.pos_ == 'PRON' and is_subject and is_subject[-1]):
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



        














def normalize(text):
    """Make text lowercase and make some replacements."""
    text = text.lower()
    
    replacements = [
        (r'\[.*\]', ''),  # Remove meta-text annotation.
        (r'\(.*\)', ''),  
        (r'[——]', ' '),
        (r'--', ' '),
        (r'-\s', ' '),
        (r'doo+m', 'doom'),
        (r'\?+', '?'),
        (r'!+', '!'),
        (r'\.+', '.'),
        (r'aw+', 'aw'),
        (r'hm+', 'hm'),
        (r'no+', 'no'),
        (r'a+h+', 'ah'),
        (r'soo+n', 'soon'),
        (r'[“”]', '"'),
        (r"’", r"'")
    ]
    
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    
    return text


def to_lemmas(text):
    """Convert words in `text` to a string of lemmas."""
    lemmas = []
    for token in nlp(text):
        if not token.is_punct and not token.is_stop and len(token.text) < 15:
            if token.lemma_ != ' ':
                lemmas.append(token.lemma_.strip())
    return ' '.join(lemmas)


def to_tokens(text):
    """Convert words in `text` to a string of tokens."""
    tokens = []
    allowed_punct = set('.?!,')
    for token in nlp(text):
        if ((token.is_punct and token.text not in allowed_punct)
                or len(token.text) > 15
                or token.text == ' '):
            continue
        tokens.append(token.text)
    return ' '.join(tokens)


def get_polarity(text):
    """Get average pos/neg polarity of a string."""
    from textblob import TextBlob
    blob = TextBlob(text)
    return blob.sentiment.polarity
    

