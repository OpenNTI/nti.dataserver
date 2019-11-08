
from .vocabulary import Term, Vocabulary

def testVocab():
    vocab = Vocabulary([Term(x) for x in ('first', 'second', 'third')])
    return vocab
    