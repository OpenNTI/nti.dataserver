from __future__ import print_function, unicode_literals

import math

LN2 = math.log(2)

default_hist_nbuckets = 200
default_hist_percentiles = (5, 25, 75, 95)

default_ham_cutoff = 0.20
default_spam_cutoff = 0.90

default_use_bigrams = False
default_unknown_word_prob = 0.5
default_arc_discriminators = 50
default_max_discriminators = 150
default_unknown_word_strength = 0.45
default_minimum_prob_strength = 0.10

default_tkn_skip_max_word_size = 12
default_tkn_min_lengh_word_size = 3

PERSISTENT_HAM_INT = 1
PERSISTENT_SPAM_INT = 2
PERSISTENT_UNSURE_INT = 0

def is_spam(disposition):
	return disposition == PERSISTENT_SPAM_INT

def is_ham(disposition):
	return disposition == PERSISTENT_HAM_INT

def is_unsure(disposition=None):
	return disposition is None or disposition == PERSISTENT_UNSURE_INT

def classify(prob, ham_cutoff=default_ham_cutoff, spam_cutoff=default_spam_cutoff):
	if prob < ham_cutoff:
		disposition = PERSISTENT_HAM_INT
	elif prob > spam_cutoff:
		disposition = PERSISTENT_SPAM_INT
	else:
		disposition = PERSISTENT_UNSURE_INT
	return disposition
		
