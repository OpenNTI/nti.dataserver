# -*- coding: utf-8 -*-
"""
Indexing content utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component

from nti.contentprocessing import split_content

from nti.contentfragments import interfaces as frg_interfaces

def sanitize_content(text, table=None, tokens=False):
	"""
	clean any html from the specified text and then tokenize it

	:param text: context to sanitize
	:param tokens: boolean to return a list of tokens
	:param table: translation table
	"""
	if not text:
		return text

	# turn incoming into plain text.
	# NOTE: If the HTML included entities like like &lt,
	# this may still have things in it that sort of look like
	# tags:
	#    &lt;link text&gt; => <link text>
	# But of course we CANNOT and MUST NOT attempt to run an additional
	# parsing pass on it, as that's likely to wind up with gibberish results
	# since its nothing actually close to HTML
	# Since we're using a named adapter, we need to be careful
	# not to re-adapt multiple times
	raw = text
	text = component.getAdapter(text, frg_interfaces.IPlainTextContentFragment, name='text')
	__traceback_info__ = raw, text, type(text)
	# translate and tokenize words
	text = text.translate(table) if table else text
	tokenized_words = split_content(text)
	result = tokenized_words if tokens else ' '.join(tokenized_words)
	return result

def parse_last_modified(t):
	"""
	parsed to a float value a rendered based last modified date
	"""
	result = time.time()
	try:
		if t:
			ms = ".0"
			idx = t.rfind(".")
			if idx != -1:
				ms = t[idx:]
				t = t[0:idx]

			t = time.strptime(t, "%Y-%m-%d %H:%M:%S")
			t = long(time.mktime(t))
			result = str(t) + ms
	except:
		pass
	return float(result)
