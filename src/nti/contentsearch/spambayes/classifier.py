from __future__ import generators

# An implementation of a Bayes-like spam classifier.
#
# Paul Graham's original description:
#
#     http://www.paulgraham.com/spam.html
#
# A highly fiddled version of that can be retrieved from our CVS repository,
# via tag Last-Graham.  This made many demonstrated improvements in error
# rates over Paul's original description.
#
# This code implements Gary Robinson's suggestions, the core of which are
# well explained on his webpage:
#
#    http://radio.weblogs.com/0101454/stories/2002/09/16/spamDetection.html
#
# This is theoretically cleaner, and in testing has performed at least as
# well as our highly tuned Graham scheme did, often slightly better, and
# sometimes much better.  It also has "a middle ground", which people like:
# the scores under Paul's scheme were almost always very near 0 or very near
# 1, whether or not the classification was correct.  The false positives
# and false negatives under Gary's basic scheme (use_gary_combining) generally
# score in a narrow range around the corpus's best spam_cutoff value.
# However, it doesn't appear possible to guess the best spam_cutoff value in
# advance, and it's touchy.
#
# The last version of the Gary-combining scheme can be retrieved from our
# CVS repository via tag Last-Gary.
#
# The chi-combining scheme used by default here gets closer to the theoretical
# basis of Gary's combining scheme, and does give extreme scores, but also
# has a very useful middle ground (small # of msgs spread across a large range
# of scores, and good cutoff values aren't touchy).
#
# This implementation is due to Tim Peters et alia.

import re
import math
from collections import defaultdict

from nti.contentsearch.spambayes.chi2 import chi2Q

# ---------------------------------

DOMAIN_AND_PORT_RE = re.compile(r"([^:/\\]+)(:([\d]+))?")
HTTP_ERROR_RE = re.compile(r"HTTP Error ([\d]+)")
URL_KEY_RE = re.compile(r"[\W]")

LN2 = math.log(2)       # used frequently by chi-combining

# ---------------------------------

class WordInfo(object):
	# A WordInfo is created for each distinct word.  spamcount is the
	# number of trained spam msgs in which the word appears, and hamcount
	# the number of trained ham msgs.
	#
	# Invariant:  For use in a classifier database, at least one of
	# spamcount and hamcount must be non-zero.
	#
	# Important:  This is a tiny object.  Use of __slots__ is essential
	# to conserve memory.
	__slots__ = 'spamcount', 'hamcount'
	
	def __init__(self):
		self.__setstate__((0, 0))
	
	def __repr__(self):
		return "WordInfo %s" % repr((self.spamcount, self.hamcount))
	
	def __getstate__(self):
		return self.spamcount, self.hamcount
	
	def __setstate__(self, t):
		self.spamcount, self.hamcount = t

class Classifier(object):
	
	# allow a subclass to use a different class for WordInfo
	WordInfoClass = WordInfo

	def __init__(self, unknown_word_strength=0.45, unknown_word_prob=0.5, mapfactory=dict):
		self.nspam = self.nham = 0
		self.wordinfo = mapfactory()
		self._v_probcache = defaultdict(dict)
		self.unknown_word_prob = unknown_word_prob
		self.unknown_word_strength = unknown_word_strength
			
	@property
	def probcache(self):
		return self._v_probcache

	# spamprob() implementations.  One of the following is aliased to
	# spamprob, depending on option settings.
	# Currently only chi-squared is available, but maybe there will be
	# an alternative again someday.
	
	# Across vectors of length n, containing random uniformly-distributed
	# probabilities, -2*sum(ln(p_i)) follows the chi-squared distribution
	# with 2*n degrees of freedom.  This has been proven (in some
	# appropriate sense) to be the most sensitive possible test for
	# rejecting the hypothesis that a vector of probabilities is uniformly
	# distributed.  Gary Robinson's original scheme was monotonic *with*
	# this test, but skipped the details.  Turns out that getting closer
	# to the theoretical roots gives a much sharper classification, with
	# a very small (in # of msgs), but also very broad (in range of scores),
	# "middle ground", where most of the mistakes live.  In particular,
	# this scheme seems immune to all forms of "cancellation disease":  if
	# there are many strong ham *and* spam clues, this reliably scores
	# close to 0.5.  Most other schemes are extremely certain then -- and
	# often wrong.
	def chi2_spamprob(self, wordstream, evidence=False):
		"""
		Return best-guess probability that wordstream is spam.
		wordstream is an iterable object producing words.
		The return value is a float in [0.0, 1.0].

		If optional arg evidence is True, the return value is a pair probability, evidence
		where evidence is a list of (word, probability) pairs.
		"""
		
		from math import frexp, log as ln

		# we compute two chi-squared statistics, one for ham and one for
		# spam.  The sum-of-the-logs business is more sensitive to probs
		# near 0 than to probs near 1, so the spam measure uses 1-p (so
		# that high-spamprob words have greatest effect), and the ham
		# measure uses p directly (so that lo-spamprob words have greatest
		# effect).
		#
		# For optimization, sum-of-logs == log-of-product, and f.p.
		# multiplication is a lot cheaper than calling ln().  It's easy
		# to underflow to 0.0, though, so we simulate unbounded dynamic
		# range via frexp.  The real product H = this H * 2**Hexp, and
		# likewise the real product S = this S * 2**Sexp.
		H = S = 1.0
		Hexp = Sexp = 0
		
		clues = self._getclues(wordstream)
		for prob, _, _ in clues: # a clue is a prob,word,record
			S *= 1.0 - prob
			H *= prob
			if S < 1e-200:  # prevent underflow
				S, e = frexp(S)
				Sexp += e
			if H < 1e-200:  # prevent underflow
				H, e = frexp(H)
				Hexp += e

		# Compute the natural log of the product = sum of the logs:
		# ln(x * 2**i) = ln(x) + i * ln(2).
		S = ln(S) + Sexp * LN2
		H = ln(H) + Hexp * LN2

		n = len(clues)
		if n:
			S = 1.0 - chi2Q(-2.0 * S, 2*n)
			H = 1.0 - chi2Q(-2.0 * H, 2*n)

			# how to combine these into a single spam score?  We originally
			# used (S-H)/(S+H) scaled into [0., 1.], which equals S/(S+H).  A
			# systematic problem is that we could end up being near-certain
			# a thing was (for example) spam, even if S was small, provided
			# that H was much smaller.
			# Rob Hooft stared at these problems and invented the measure
			# we use now, the simpler S-H, scaled into [0., 1.].
			prob = (S-H + 1.0) / 2.0
		else:
			prob = 0.5

		if evidence:
			clues = [(w, p) for p, w, _r in clues]
			clues.sort(lambda a, b: cmp(a[1], b[1]))
			clues.insert(0, ('*S*', S))
			clues.insert(0, ('*H*', H))
			return prob, clues
		else:
			return prob

	spamprob = chi2_spamprob
	
	def learn(self, wordstream, is_spam, use_bigrams=False):
		"""
		Teach the classifier by example.
		
		wordstream is a word stream representing a message.  If is_spam is
		True, you're telling the classifier this message is definitely spam,
		else that it's definitely not spam.
		"""
		if use_bigrams:
			wordstream = self._enhance_wordstream(wordstream)
		self._add_msg(wordstream, is_spam)

	def unlearn(self, wordstream, is_spam, use_bigrams=False):
		"""
		In case of pilot error, call unlearn ASAP after screwing up.
		Pass the same arguments you passed to learn().
		"""
		if use_bigrams:
			wordstream = self._enhance_wordstream(wordstream)
		self._remove_msg(wordstream, is_spam)
	
	def probability(self, record):
		"""
		Compute, store, and return prob(msg is spam | msg contains word).
		
		This is the Graham calculation, but stripped of biases, and
		stripped of clamping into 0.01 thru 0.99.  The Bayesian
		adjustment following keeps them in a sane range, and one
		that naturally grows the more evidence there is to back up
		a probability.
		"""

		spamcount = getattr(record, 'spamcount', 0)
		hamcount = getattr(record, 'hamcount', 0)

		# try the cache first
		try:
			return self.probcache[spamcount][hamcount]
		except KeyError:
			pass

		nham = float(self.nham or 1)
		nspam = float(self.nspam or 1)

		assert hamcount <= nham, "Token seen in more ham than ham trained."
		hamratio = hamcount / nham

		assert spamcount <= nspam, "Token seen in more spam than spam trained."
		spamratio = spamcount / nspam

		prob = spamratio / (hamratio + spamratio)

		S = self.unknown_word_strength
		StimesX = S * self.unknown_word_prob


		# Now do Robinson's Bayesian adjustment.
		#
		#		 s*x + n*p(w)
		# f(w) = --------------
		#		   s + n
		#
		# I find this easier to reason about like so (equivalent when
		# s != 0):
		#
		#		x - p
		#  p +  -------
		#	   1 + n/s
		#
		# IOW, it moves p a fraction of the distance from p to x, and
		# less so the larger n is, or the smaller s is.

		n = hamcount + spamcount
		prob = (StimesX + n * prob) / (S + n)

		# update the cache
		self.probcache[spamcount][hamcount] = prob
		
		return prob
