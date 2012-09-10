#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Converters and utilities for dealing with HTML content fragments.
In particular, sanitazation.


$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

import html5lib
from html5lib import treewalkers, serializer, treebuilders
#from html5lib import filters
#from html5lib.filters import sanitizer
import lxml.etree

from nti.contentfragments import interfaces as frg_interfaces

class _SliceDict(dict):
	"""
	There is a bug in html5lib 0.95: The _base.TreeWalker now returns
	a dictionary from normalizeAttrs. Some parts of the code, notably sanitizer.py 171
	haven't been updated from 0.90 and expect a list. They try to reverse it using a
	slice, and the result is a type error. We can fix this.
	"""

	def __getitem__( self, key ):
		# recognize the reversing slice, [::-1]
		if isinstance(key,slice) and key.start is None and key.stop is None and key.step == -1:
			return self.items()[::-1]
		return dict.__getitem__( self, key )

# TODO: Consider also http://packages.python.org/PottyMouth/
from html5lib.sanitizer import HTMLSanitizerMixin
# There is a bug in 0.95: the sanitizer converts attribute dicts
# to lists when they should stay dicts
_orig_sanitize = HTMLSanitizerMixin.sanitize_token
def _sanitize_token(self, token ):
	to_dict = False

	if token.get('name') in self.allowed_elements and isinstance( token.get( 'data' ), dict ):
		if not isinstance( token.get('data') , _SliceDict ):
			token['data'] = _SliceDict( {k[1]:v for k, v in token['data'].items()} )
		to_dict = True
	result = _orig_sanitize( self, token )
	if to_dict:
		# TODO: We're losing namespaces for attributes in this process
		result['data'] = {(None,k):v for k,v in result['data']}
	return result

HTMLSanitizerMixin.sanitize_token = _sanitize_token

# In order to be able to serialize a complete document, we
# must whitelist the root tags as of 0.95
# TODO: Maybe this means now we can parse and serialize in one step?
HTMLSanitizerMixin.allowed_elements.extend( ['html', 'head', 'body'] )

# We use data: URIs to communicate images and sounds in one
# step. FIXME: They aren't really safe and we should have tighter restrictions
# on them, such as by size.
HTMLSanitizerMixin.acceptable_protocols.append( 'data' )

def _html5lib_tostring(doc,sanitize=True):
	"""
	:return: A unicode string representing the document in normalized
		HTML5 form, parseable as XML.
	"""
	walker = treewalkers.getTreeWalker("lxml")
	stream = walker(doc)
	# We can easily subclass filters.HTMLSanitizer to add more
	# forbidden tags, and some CSS things to filter. Then
	# we pass a treewalker over it to the XHTMLSerializer instead
	# of using the keyword arg.
	# We want to produce parseable XML so that it's easy to deal with
	# outside a browser
	# TODO: What about stripping excess whitespace? Seems like a good idea...
	s = serializer.xhtmlserializer.XHTMLSerializer(inject_meta_charset=False,
												   omit_optional_tags=False,
												   quote_attr_values=True,
												   strip_whitespace=False,
												   use_trailing_solidus=True,
												   space_before_trailing_solidus=True,
												   sanitize=sanitize )
	output_generator = s.serialize(stream) # By not passing the 'encoding' arg, we get a unicode string
	string = u''.join( output_generator )
	return string

def _to_sanitized_doc( user_input ):
	# We cannot sanitize and parse in one step; if there is already
	# HTML around it, then we wind up with escaped HTML as text:
	# <html>...</html> => <html><body>&lthtml&gt...&lt/html&gt</html>
	p = html5lib.HTMLParser( tree=treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False )
	doc = p.parse( user_input )
	string = _html5lib_tostring( doc, sanitize=True )

	# Our normalization is pathetic.
	# replace unicode nbsps
	string = string.replace(u'\u00A0', ' ' )

	# Back to lxml to do some dom manipulation
	p = html5lib.HTMLParser( tree=treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False )
	doc = p.parse( string )

	return doc

def _doc_to_plain_text( doc ):
	string = lxml.etree.tostring( doc,
								  method='text',
								  encoding=unicode )
	return frg_interfaces.PlainTextContentFragment( string )



def sanitize_user_html( user_input, method='html' ):
	"""
	Given a user input string of plain text, HTML or HTML fragment, sanitize
	by removing unsupported/dangerous elements and doing some normalization.
	If it can be represented in plain text, do so.

	:param string method: One of the ``method`` values acceptable to
		:func:`lxml.etree.tostring`. The default value, ``html``, causes this
		method to produce either HTML or plain text, whatever is most appropriate.
		Passing the value ``text`` causes this method to produce only plain text captured
		by traversing the elements with lxml.

	:return: Something that implements :class:`frg_interfaces.IUnicodeContentFragment`,
		typically either :class:`frg_interfaces.IPlainTextContentFragment` or
		:class:`frg_interfaces.ISanitizedHTMLContentFragment`.
	"""

	doc = _to_sanitized_doc( user_input )

	for node in doc.iter():
		# Turn top-level text nodes into paragraphs.
		if node.tag == 'p' and node.tail:
			tail = node.tail
			node.tail = None
			p = lxml.etree.Element( node.tag, node.attrib )
			p.text = tail
			node.addnext( p )

		# Strip spans that are the empty (they used to contain style but no longer)
		elif node.tag == 'span' and len(node) == 0 and not node.text:
			node.getparent().remove( node )

		# Spans that are directly children of a paragraph (and so could not contain
		# other styling through inheritance) that have the pad's default style get that removed
		# so they render as default on the browser as well
		elif node.tag == 'span' and node.getparent().tag == 'p' and node.get( 'style' ) == 'font-family: \'Helvetica\'; font-size: 12pt; color: black;':
			del node.attrib['style']

	if method == 'text':
		return _doc_to_plain_text( doc )

	string = _html5lib_tostring( doc, sanitize=False )
	# If we can go back to plain text, do so.
	normalized = string[len('<html><head></head><body>'): 0 - len('</body></html>')]
	while normalized.endswith( '<br />' ):
		# remove trailing breaks
		normalized = normalized[0:-6]
	# If it has no more tags, we can be plain text.
	if '<' not in normalized:
		string = frg_interfaces.PlainTextContentFragment( normalized.strip() )
	else:
		string = frg_interfaces.SanitizedHTMLContentFragment( "<html><body>" + normalized + "</body></html>" )
	return string

from repoze.lru import lru_cache

# Caching these can be quite effective, especially during
# content indexing operations when the same content is indexed
# for multiple users. Both input and output are immutable
# TODO: For the non-basestring cases, we could actually cache the representation
# in a non-persistent field of the object? (But the objects aren't Persistent, so
# _v fields might not work?)

@interface.implementer(frg_interfaces.IPlainTextContentFragment)
@component.adapter(basestring)
@lru_cache(10000)
def _sanitize_user_html_to_text( user_input ):
	"""
	Registered as an adapter with the name 'text' for convenience.

	See :func:`sanitize_user_html`.
	"""
	return sanitize_user_html( user_input, method='text' )

@interface.implementer(frg_interfaces.IPlainTextContentFragment)
@component.adapter(frg_interfaces.IHTMLContentFragment)
@lru_cache(10000)
def _html_to_sanitized_text( html ):
	return _doc_to_plain_text( _to_sanitized_doc( html ) )


@interface.implementer(frg_interfaces.IPlainTextContentFragment)
@component.adapter(frg_interfaces.ISanitizedHTMLContentFragment)
@lru_cache(10000)
def _sanitized_html_to_sanitized_text( sanitized_html ):
	p = html5lib.HTMLParser( tree=treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False )
	doc = p.parse( sanitized_html )

	return _doc_to_plain_text( doc )
