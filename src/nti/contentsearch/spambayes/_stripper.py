from __future__ import print_function, unicode_literals, generators

import re

from zope import interface

from nti.contentsearch import interfaces as cs_interfaces

# patch encodings.aliases to recognize 'ansi_x3_4_1968'
from encodings.aliases import aliases # The aliases dictionary
if not aliases.has_key('ansi_x3_4_1968'):
	aliases['ansi_x3_4_1968'] = 'ascii'
del aliases # Not needed any more

has_highbit_char = re.compile(r"[\x80-\xff]").search

# gimmick to probabilistically find html/xml tags.
# Note that <style and html comments are handled by crack_html_style()
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
	# html comments embedded in words, like
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

fname_sep_re = re.compile(r'[/\\:]')

def crack_filename(fname):
	yield "fname:" + fname
	components = fname_sep_re.split(fname)
	morethan1 = len(components) > 1
	for component in components:
		if morethan1:
			yield "fname comp:" + component
		pieces = urlsep_re.split(component)
		if len(pieces) > 1:
			for piece in pieces:
				yield "fname piece:" + piece

# strip out uuencoded sections and produce tokens.  The return value
# is (new_text, sequence_of_tokens), where new_text no longer contains
# uuencoded stuff.  Note that we're not bothering to decode it!  Maybe
# we should.  One of my persistent false negatives is a spam containing
# nothing but a uuencoded money.txt; OTOH, uuencode seems to be on
# its way out (that's an old spam).

uuencode_begin_re = re.compile(r"""
    ^begin \s+
    (\S+) \s+   # capture mode
    (\S+) \s*   # capture filename
    $
""", re.VERBOSE | re.MULTILINE)

uuencode_end_re = re.compile(r"^end\s*\n", re.MULTILINE)

class UUencodeStripper(Stripper):
	def __init__(self):
		Stripper.__init__(self, uuencode_begin_re.search,
								uuencode_end_re.search)

	def tokenize(self, m):
		mode, fname = m.groups()
		return (['uuencode mode:%s' % mode] +
				['uuencode:%s' % x for x in crack_filename(fname)])

crack_uuencode = UUencodeStripper().analyze

# strip and specially tokenize embedded URL like strings.

url_re = re.compile(r"""
    (https? | ftp)  # capture the protocol
    ://             # skip the boilerplate
    # Do a reasonable attempt at detecting the end.  It may or may not
    # be in html, may or may not be in quotes, etc.  If it's full of %
    # escapes, cool -- that's a clue too.
    ([^\s<>"'\x7f-\xff]+)  # capture the guts
""", re.VERBOSE)                        # '

urlsep_re = re.compile(r"[;?:@&=+,$.]")

class URLStripper(Stripper):
	def __init__(self):
		search = url_re.search
		Stripper.__init__(self, search, re.compile("").search)

	def tokenize(self, m):
		proto, guts = m.groups()
		assert guts
		if proto is None:
			if guts.lower().startswith("www"):
				proto = "http"
			elif guts.lower().startswith("ftp"):
				proto = "ftp"
			else:
				proto = "unknown"
		tokens = ["proto:" + proto]
		pushclue = tokens.append

		# lose the trailing punctuation for casual embedding, like:
		#     The code is at http://mystuff.org/here?  Didn't resolve.
		# or
		#     I found it at http://mystuff.org/there/.  Thanks!
		while guts and guts[-1] in '.:?!/':
			guts = guts[:-1]
		for piece in guts.split('/'):
			for chunk in urlsep_re.split(piece):
				pushclue("url:" + chunk)
		return tokens

received_complaints_re = re.compile(r'\([a-z]+(?:\s+[a-z]+)+\)')
crack_urls = URLStripper().analyze
	
# remove html <style gimmicks.
html_style_start_re = re.compile(r"""
    < \s* style\b [^>]* >
""", re.VERBOSE)

class StyleStripper(Stripper):
	def __init__(self):
		Stripper.__init__(self, html_style_start_re.search,
						  re.compile(r"</style>").search)

crack_html_style = StyleStripper().analyze

# remove html comments.
class CommentStripper(Stripper):
	def __init__(self):
		Stripper.__init__(self,
						  re.compile(r"<!--|<\s*comment\s*[^>]*>").search,
						  re.compile(r"-->|</comment>").search)

crack_html_comment = CommentStripper().analyze

# remove stuff between <noframes> </noframes> tags.
class NoframesStripper(Stripper):
	def __init__(self):
		Stripper.__init__(self,
						  re.compile(r"<\s*noframes\s*>").search,
						  re.compile(r"</noframes\s*>").search)

crack_noframes = NoframesStripper().analyze

# can html for constructs often seen in viruses and worms.
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

numeric_entity_re = re.compile(r'&#(\d+);')

def numeric_entity_replacer(m):
	try:
		return chr(int(m.group(1)))
	except:
		return '?'

breaking_entity_re = re.compile(r"""
    &nbsp;
|   < (?: p
      |   br
      )
    >
""", re.VERBOSE)


word_re = re.compile("(?x)(?:[A-Z]\\.)+ | \\$?\\d+(?:\\.\\d+)?%? | \\w+(?:[-']\\w+)*", re.MULTILINE | re.DOTALL | re.UNICODE)

@interface.implementer(cs_interfaces.IContentTranslationTable )
def _default_translation_table():
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
	return non_ascii_translate_tab

