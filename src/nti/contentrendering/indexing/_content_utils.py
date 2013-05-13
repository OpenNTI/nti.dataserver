# -*- coding: utf-8 -*-
"""
Indexing content utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time

from zope import component

from nti.contentprocessing import split_content

from nti.contentfragments import interfaces as frg_interfaces
from nti.contentfragments.html import _sanitize_user_html_to_text

def sanitize_content(text, tokens=False, table=None):
	"""
	clean any html from the specified text and then tokenize it
	
	:param text: context to sanitize
	:param tokens: boolean to return a list of tokens
	:param table: translation table
	"""

	if not text:
		return text

	# user ds sanitizer
	text = _sanitize_user_html_to_text(text)

	# remove any html (i.e. meta, link) that is not removed
	text = component.getAdapter(text, frg_interfaces.IPlainTextContentFragment, name='text')

	# tokenize words
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
