#!/usr/bin/env python
"""
Utility to take a case from Google Scholar and dump it to TeX
$Revision$
"""
from __future__ import unicode_literals, print_function

from zope import interface
import nti.contentrendering
from nti.contentrendering import interfaces
from nti.contentfragments import interfaces as frg_interfaces

import requests
import pyquery
from lxml import etree
import sys
import re

def _text_of( p ):
	return etree.tostring( p, encoding=unicode, method='text' )

class _ElementPlainTextContentFragment(frg_interfaces.PlainTextContentFragment):
	children = ()
	def __new__( cls, element ):
		return super(_ElementPlainTextContentFragment,cls).__new__( cls, _text_of( element ) )

	def __init__( self, element=None ):
		# Note: __new__ does all the actual work, because these are immutable as strings
		super(_ElementPlainTextContentFragment,self).__init__( _text_of( element ) )
		self.element = element


class _Container(frg_interfaces.LatexContentFragment):

	children = ()

	def add_child( self, child ):
		if self.children == ():
			self.children = []
		self.children.append( child )


class _WrappedElement(_Container):
	wrapper = None

	def __new__( cls, text ):
		return super(_WrappedElement,cls).__new__( cls, '\\' + cls.wrapper + '{' + text + '}' )

	def __init__( self, text=None ):
		# Note: __new__ does all the actual work, because these are immutable as strings
		super(_WrappedElement,self).__init__( self, '\\' + self.wrapper + '{' + text + '}' )

class _Footnote(_WrappedElement):
	wrapper = 'footnote'

class _Chapter(_WrappedElement):
	wrapper = 'chapter'

class _Section(_WrappedElement):
	wrapper = 'section'

class _Label(_WrappedElement):
	wrapper = 'label'

class _Title(_WrappedElement):
	wrapper = 'title'

class _TextIT(_WrappedElement):
	wrapper = 'textit'

class _TextBF(_WrappedElement):
	wrapper = 'textbf'

class _ntipagenum(_WrappedElement):
	wrapper = 'ntipagenum'

class _href(_Container):

	def __new__( cls, url, text=None ):
		return super(_href,cls).__new__( cls, '\\href{' + url + '}' )

	def __init__( self, url, text=None ):
		super(_href,self).__init__( self, '\\href{' + url + '}' )
		# Note: __new__ does all the actual work, because these are immutable as strings
		self.add_child( '{' )
		self.add_child( text )
		self.add_child( '}' )

def _url_to_pyquery( url ):
	# Must use requests, not the url= argument, as
	# that User-Agent is blocked
	# The custom user-agent string is to trick Google into sending UTF-8.
	return pyquery.PyQuery( requests.get( url, headers={'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/537.1+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2"} ).text )

def _case_name_of( opinion ):
	return opinion(b"#gsl_case_name").text()

def _opinion_of( doc ):
	# depending on if we got the new look or the old look this is
	# two different names
	return doc( b"#gsl_opinion, #gs_opinion" )

def _included_children_of( opinion ):
	return opinion( b"p,center,h2,blockquote" )

def _footnotes_of( doc ):
	if len(doc(b"small")):
		small = doc(b"small")[0]
		ps = list(small.itersiblings())
		return ps
	else:
		return []

def _p_to_content(footnotes, p, include_tail=True):
	accum = []
	kids = p.getchildren()
	if not kids:
		if include_tail:
			# If we fail to include this check, we get
			# duplicate text in and out of the link
			accum.append( _ElementPlainTextContentFragment( p ) )
		elif p.text and p.text.strip():
			accum.append( frg_interfaces.PlainTextContentFragment( p.text.strip() ) )
	else:
		def _tail(e):
			if e is not None and e.tail and e.tail.strip():
				accum.append( frg_interfaces.PlainTextContentFragment( e.tail.strip() ) )
		# complex element with nested children to deal with.
		if p.text and p.text.strip():
			accum.append( frg_interfaces.PlainTextContentFragment( p.text ) )
		for kid in kids:
			if kid.tag == 'i':
				accum.append( _TextIT(kid.text) )
			elif kid.tag == 'b':
				accum.append( _TextBF(kid.text) )
			elif kid.tag == 'a':
				# anchors and links and pagenumbers
				if kid.get( 'class' ) == 'gsl_pagenum':
					accum.append( _Label( kid.text ) )
					accum.append( _ntipagenum( kid.text ) )
				elif kid.get( 'class' ) == 'gsl_pagenum2':
					pass
				elif (kid.get( 'href' ) or '').startswith( '#' ):
					# These are just to footnotes, so we don't want to
					# output anything, but we do want the tail
					pass
					#accum.append( "(DOC LINK: " + _text_of( kid ) + " " + kid.get( 'href' ) + ")")
				elif kid.get( 'href' ):
					# \href[options]{URL}{text}
					# TODO: We're not consistent with when we recurse
					# The tail of the <a> is not part of the link, so make sure
					# not to treat it as such.
					href = _href( _url_escape(kid.get( 'href' )),
								  _p_to_content( footnotes, kid, include_tail=False ) )

					accum.append( href )
					for c in href.children:
						accum.append( c )
				else:
					accum.append( _ElementPlainTextContentFragment( kid ) )
					kid = None
			elif kid.tag == 'sup':
				# footnote refs
				accum.append( _find_footnote( footnotes, kid ) )
			elif kid.tag == 'p':
				accum.append( _p_to_content( footnotes, kid ) )
			_tail(kid)
		if include_tail:
			_tail(p)


	return frg_interfaces.LatexContentFragment( ' '.join( [frg_interfaces.ILatexContentFragment( x ) for x in accum] ) )

def _find_footnote( footnotes, sup ):
	# footnote refs
	ref_to = sup[0].get( 'href' )[1:]
	accum = []
	for i in footnotes:
		# Locate the anchor at the begining of the footnote
		# This may or may not actually be an anchor element
		anchor = {}
		if len(i.getchildren()) and i.getchildren()[0].tag == 'a':
			anchor = i.getchildren()[0]

		if anchor.get( 'name' ) == ref_to \
		  or  _text_of( i ).startswith( ref_to ):
			# found it
			accum.append( _p_to_content( footnotes, i ) )
		elif _text_of( i ).startswith( '[' ) and accum: # The next one
			break
		elif accum:
			accum.append( _p_to_content( footnotes, i ) )
	return  _Footnote( ' '.join( [frg_interfaces.ILatexContentFragment( x ) for x in accum] ) )

def _url_escape(u):
	return u.replace( '&', '\\&').replace( '_', '\\_' )

CONTAINERS = { 'blockquote': 'quote',
			   'center': 'center' }

def _opinion_to_tex( doc, output=None, base_url=None ):
	tex = []

	name = _case_name_of( doc )
#	tex.append( _Title( name ) )
	footnotes = _footnotes_of( doc )
	for i in footnotes:
		i.getparent().remove( i )

	# This flattens and expands a list. That was fine before
	# we did any recursion. Now that there's recursion, it's not
	# so fine. We need increasing sophistication; for now we
	# go the first step of ignoring things we encounter as we
	# traverse.
	inc_children = _included_children_of( _opinion_of( doc ) )
	exc_children = set()

	current = _Chapter( name )
	tex.append( current )

	section = _Section( "Opinion of the Court" )
	if hasattr( current, 'parent' ):
		current = getattr( current, 'parent' ) # Close the nesting. This deals with exactly one level
	current.add_child( section )
	setattr( section, 'parent', current )
	current = section

	for inc_child in inc_children:
		if inc_child in exc_children:
			continue

		if inc_child.tag in ('p',):
			if ( re.search( r'^Justice [A-Z]*|^Chief Justice [A-Z]*|^MR. JUSTICE [A-Z]*|^MR. CHIEF JUSTICE [A-Z]*', unicode( inc_child.text ) ) ):
				if ( re.search( r'concurring|dissenting', unicode( inc_child.text ) ) ):
					section = _Section( inc_child.text.strip() )
					if hasattr( current, 'parent' ):
						current = getattr( current, 'parent' ) # Close the nesting. This deals with exactly one level
					current.add_child( section )
					setattr( section, 'parent', current )
					current = section
			else:
				for child in inc_child.getchildren():
					if ( re.search( r'^\s*Justice [A-Z]*|^\s*Chief Justice [A-Z]*|^\s*MR. JUSTICE [A-Z]*|^\s*MR. CHIEF JUSTICE [A-Z]*', unicode(child.tail) ) ):
						if ( re.search( r'concurring|dissenting', unicode( child.tail ) ) or
						     re.search( r'dissent|concur', unicode( _text_of( inc_child.itersiblings().next() ) ) ) ):
							section = _Section( child.tail.strip() )
							if hasattr( current, 'parent' ):
								current = getattr( current, 'parent' ) # Close the nesting. This deals with exactly one level
							current.add_child( section )
							setattr( section, 'parent', current )
							current = section
			current.add_child( _p_to_content( footnotes, inc_child ) )
		elif inc_child.tag in CONTAINERS:
			exc_children.update( inc_child.getchildren() )
			container = _Container( "\\begin{%s}" % CONTAINERS[inc_child.tag] )
			content = _p_to_content( footnotes, inc_child )
			container.add_child( content )
			container.add_child( frg_interfaces.LatexContentFragment( '\\end{%s}' % CONTAINERS[inc_child.tag] ) )
			if content or getattr( content, 'children', ()):
				current.add_child( container )
		elif inc_child.tag == 'h2':
			current.add_child( _p_to_content( footnotes, inc_child ) )

	if output is None:
		output = sys.stdout # Capture this at runtime, it does change

	def _print(node):
		print( frg_interfaces.ILatexContentFragment(node).encode('utf-8'), file=output )
		print( file=output )
		for child in getattr( node, 'children', ()):
			_print( frg_interfaces.ILatexContentFragment(child) )

	for node in tex:
		_print( node )

def main():
	from zope.configuration import xmlconfig
	xmlconfig.file( 'configure.zcml', package=nti.contentrendering )
	url = sys.argv[1]
	pq = _url_to_pyquery( url )
	_opinion_to_tex( pq, base_url=url )

if __name__ == '__main__': # pragma: no cover
	main()
