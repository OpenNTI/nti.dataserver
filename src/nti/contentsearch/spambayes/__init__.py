import math

LN2 = math.log(2)

default_hist_nbuckets = 200
default_hist_percentiles = (5, 25, 75, 95)

default_ham_cutoff = 0.20
default_spam_cutoff = 0.90

PERSISTENT_HAM_STRING = u'ham'
PERSISTENT_SPAM_STRING = u'spam'
PERSISTENT_UNSURE_STRING = u'unsure'

def classify(prob, ham_cutoff=default_ham_cutoff, spam_cutoff=default_spam_cutoff):
	if prob < ham_cutoff:
		disposition = PERSISTENT_HAM_STRING
	elif prob > spam_cutoff:
		disposition = PERSISTENT_SPAM_STRING
	else:
		disposition = PERSISTENT_UNSURE_STRING
	return disposition
		