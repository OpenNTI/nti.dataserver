#! /usr/bin/env python

from __future__ import generators

import re
import math

# patch encodings.aliases to recognize 'ansi_x3_4_1968'
from encodings.aliases import aliases # The aliases dictionary
if not aliases.has_key('ansi_x3_4_1968'):
	aliases['ansi_x3_4_1968'] = 'ascii'
del aliases # Not needed any more


has_highbit_char = re.compile(r"[\x80-\xff]").search

# gimmick to probabilistically find HTML/XML tags.
# Note that <style and HTML comments are handled by crack_html_style()
# and crack_html_comment() instead -- they can be very long, and long
# minimal matches have a nasty habit of blowing the C stack.
html_re = re.compile(r"""
    <
    (?![\s<>])  # e.g., don't match 'a < b' or '<<<' or 'i<<5' or 'a<>b'
    # guessing that other tags are usually "short"
    [^>]{0,256} # search for the end '>', but don't run wild
    >
""", re.VERBOSE | re.DOTALL)

class Stripper(object):
	# the retained portions are catenated together with self.separator.
	# CAUTION:  This used to be blank.  But then I noticed spam putting
	# HTML comments embedded in words, like
	#     FR<!--slkdflskjf-->EE!
	# Breaking this into "FR" and "EE!" wasn't a real help <wink>.
	separator = ''  # a subclass can override if this isn't appropriate

	def __init__(self, find_start, find_end):
		# find_start and find_end have signature
		#     string, int -> match_object
		# where the search starts at string[int:int].  If a match isn't found,
		# they must return None.  The match_object for find_start, if not
		# None, is passed to self.tokenize, which returns a (possibly empty)
		# list of tokens to generate.  Subclasses may override tokenize().
		# Text between find_start and find_end is thrown away, except for
		# whatever tokenize() produces.  A match_object must support method
		#     span() -> int, int    # the slice bounds of what was matched
		self.find_start = find_start
		self.find_end = find_end

	# efficiency note:  This is cheaper than it looks if there aren't any
	# special sections.  Under the covers, string[0:] is optimized to
	# return string (no new object is built), and likewise ' '.join([string])
	# is optimized to return string.  It would actually slow this code down
	# to special-case these "do nothing" special cases at the Python level!
	
	def analyze(self, text):
		i = 0
		retained = []
		pushretained = retained.append
		tokens = []
		while True:
			m = self.find_start(text, i)
			if not m:
				pushretained(text[i:])
				break
			start, end = m.span()
			pushretained(text[i : start])
			tokens.extend(self.tokenize(m))
			m = self.find_end(text, end)
			if not m:
				# No matching end - act as if the open
				# tag did not exist.
				pushretained(text[start:])
				break
			dummy, i = m.span()
		return self.separator.join(retained), tokens

	def tokenize(self, match_object):
		# override this if you want to suck info out of the start pattern.
		return []

# ----------------------------------

# remove HTML <style gimmicks.
html_style_start_re = re.compile(r"""
    < \s* style\b [^>]* >
""", re.VERBOSE)

class StyleStripper(Stripper):
	def __init__(self):
		Stripper.__init__(self, html_style_start_re.search,
						  re.compile(r"</style>").search)

crack_html_style = StyleStripper().analyze

# ----------------------------------

# remove HTML comments.
class CommentStripper(Stripper):
	def __init__(self):
		Stripper.__init__(self,
						  re.compile(r"<!--|<\s*comment\s*[^>]*>").search,
						  re.compile(r"-->|</comment>").search)

crack_html_comment = CommentStripper().analyze

# ----------------------------------

# remove stuff between <noframes> </noframes> tags.
class NoframesStripper(Stripper):
	def __init__(self):
		Stripper.__init__(self,
						  re.compile(r"<\s*noframes\s*>").search,
						  re.compile(r"</noframes\s*>").search)

crack_noframes = NoframesStripper().analyze

# ----------------------------------

# can HTML for constructs often seen in viruses and worms.
# <script  </script
# <iframe  </iframe
# src=cid:
# height=0  width=0

virus_re = re.compile(r"""
    < /? \s* (?: script | iframe) \b
|   \b src= ['"]? cid:
|   \b (?: height | width) = ['"]? 0
""", re.VERBOSE)                        # '

def find_html_virus_clues(text):
	for bingo in virus_re.findall(text):
		yield bingo

# ----------------------------------

numeric_entity_re = re.compile(r'&#(\d+);')

def numeric_entity_replacer(m):
	try:
		return chr(int(m.group(1)))
	except:
		return '?'

# ----------------------------------

breaking_entity_re = re.compile(r"""
    &nbsp;
|   < (?: p
      |   br
      )
    >
""", re.VERBOSE)

default_skip_max_word_size = 12

# for support of the replace_nonascii_chars option, build a string.translate
# table that maps all high-bit chars and control chars to a '?' character.

non_ascii_translate_tab = ['?'] * 256
# leave blank up to (but not including) DEL alone
for i in range(32, 127):
	non_ascii_translate_tab[i] = chr(i)

# leave "normal" whitespace alone
for ch in ' \t\r\n':
	non_ascii_translate_tab[ord(ch)] = ch
del i, ch

non_ascii_translate_tab = ''.join(non_ascii_translate_tab)

def log2(n, log=math.log, c=math.log(2)):
	return log(n)/c

def tokenize_word(word, _len=len, maxword=default_skip_max_word_size, generate_long_skips=True):
	n = _len(word)
	# make sure this range matches in tokenize().
	if 3 <= n <= maxword:
		yield word

	elif n >= 3:
		# a long word.
		
		# don't want to skip embedded email addresses.
		# An earlier scheme also split up the y in x@y on '.'.  Not splitting
		# improved the f-n rate; the f-p rate didn't care either way.
		if n < 40 and '.' in word and word.count('@') == 1:
			p1, p2 = word.split('@')
			yield 'email name:' + p1
			yield 'email addr:' + p2
		else:
			# there's value in generating a token indicating roughly how
			# many chars were skipped.  This has real benefit for the f-n
			# rate, but is neutral for the f-p rate.  I don't know why!
			# XXX Figure out why, and/or see if some other way of summarizing
			# XXX this info has greater benefit.
			if generate_long_skips:
				yield "skip:%c %d" % (word[0], n // 10 * 10)
				
			if has_highbit_char(word):
				hicount = 0
				for i in map(ord, word):
					if i >= 128:
						hicount += 1
					yield "8bit%%:%d" % round(hicount * 100.0 / len(word))

def tokenize_text(text, maxword=default_skip_max_word_size, generate_long_skips=True, 
				  do_short_runs=False):
	"""
	Tokenize everything in the chunk of text we were handed.
	"""
	short_runs = set()
	short_count = 0
	for w in text.split():
		n = len(w)
		if n < 3:
			# count how many short words we see in a row - meant to
			# latch onto crap like this:
			# X j A m N j A d X h
			# M k E z R d I p D u I m A c
			# C o I d A t L j I v S j
			short_count += 1
		else:
			if short_count:
				short_runs.add(short_count)
				short_count = 0
			# make sure this range matches in tokenize_word().
			if 3 <= n <= maxword:
				yield w

			elif n >= 3:
				for t in tokenize_word(w, maxword=maxword):
					yield t
	if short_runs and do_short_runs:
		yield "short:%d" % int(log2(max(short_runs)))
			
def tokenize(text, maxword=default_skip_max_word_size, replace_nonascii_chars=False,
			 generate_long_skips=True, short_runs=False):

	# replace numeric character entities (like &#97; for the letter # 'a').
	text = numeric_entity_re.sub(numeric_entity_replacer, text)

	# normalize case.
	text = text.lower()

	if replace_nonascii_chars:
		# replace high-bit chars and control chars with '?'.
		text = text.translate(non_ascii_translate_tab)

	for t in find_html_virus_clues(text):
		yield "virus:%s" % t

	# get rid of uuencoded sections, embedded URLs, <style gimmicks,
	# and HTML comments.
	for cracker in (crack_html_style,
					crack_html_comment,
					crack_noframes):
		text, tokens = cracker(text)
		for t in tokens:
			yield t

	# remove HTML/XML tags.  Also &nbsp;.  <br> and <p> tags should
	# create a space too.
	text = breaking_entity_re.sub(' ', text)
	
	# it's important to eliminate HTML tags rather than, e.g.,
	# replace them with a blank (as this code used to do), else
	# simple tricks like
	#    Wr<!$FS|i|R3$s80sA >inkle Reduc<!$FS|i|R3$s80sA >tion
	# can be used to disguise words.  <br> and <p> were special-
	# cased just above (because browsers break text on those,
	# they can't be used to hide words effectively).
	text = html_re.sub('', text)
	for t in tokenize_text(	text, maxword=maxword, 
							generate_long_skips=generate_long_skips, do_short_runs=short_runs):
		yield t


