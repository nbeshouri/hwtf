"""
This module contains the code to train both of the two models as well
as some model specific and show specific utilities.

"""

import os
from sklearn.feature_extraction.text import CountVectorizer
from gensim.models import doc2vec, LdaMulticore, LdaModel
from gensim import matutils
from . import utils


def train_doc2vec_model(name_to_article, vector_size=75, window=10, epochs=100, save_name=None):
    """Build, train, and return a gensim doc2vec model."""
    train_corpus = []
    for name, article in name_to_article.items():
        words = article.split(' ')
        tagged_doc = doc2vec.TaggedDocument(words, [name])
        train_corpus.append(tagged_doc)
    model = doc2vec.Doc2Vec(vector_size=vector_size, window=window, epochs=epochs, workers=6)
    model.build_vocab(train_corpus)
    model.train(train_corpus, total_examples=model.corpus_count, epochs=model.epochs)
    if save_name is not None:
        utils.save_data(model, save_name)
    return model
    

def train_lda_model(name_to_article, num_topics=10, passes=10, workers=8, save_name=None):
    """Build, train, and return a gensim lda model."""
    names, articles = tuple(zip(*name_to_article.items()))
    count_vectorizer = CountVectorizer(ngram_range=(1, 2))
    counts = count_vectorizer.fit_transform(articles)
    counts = counts.transpose()
    corpus = matutils.Sparse2Corpus(counts)
    id2word = dict((v, k) for k, v in count_vectorizer.vocabulary_.items())
    model = LdaMulticore(corpus=corpus, num_topics=num_topics, id2word=id2word, passes=passes, workers=workers)
    output = model, count_vectorizer, names
    if save_name is not None:
        utils.save_data(output, save_name)
    return output
    