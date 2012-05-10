#!/usr/bin/env python
"""
Utility to take a case from Google Scholar and dump it to TeX
$Revision$
"""
from __future__ import unicode_literals, print_function

from zope import interface
import nti.contentrendering
from . import interfaces

import requests
import pyquery
from lxml import etree
import sys

def _text_of( p ):
	return etree.tostring( p, encoding=unicode, method='text' )

class _ElementPlainTextContentFragment(interfaces.PlainTextContentFragment):
	children = ()
	def __new__( cls, element ):
		return super(_ElementPlainTextContentFragment,cls).__new__( cls, _text_of( element ) )

	def __init__( self, element=None ):
		# Note: __new__ does all the actual work, because these are immutable as strings
		super(_ElementPlainTextContentFragment,self).__init__( _text_of( element ) )
		self.element = element


class _Container(interfaces.LatexContentFragment):

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
	return pyquery.PyQuery( requests.get( url ).text )

def _case_name_of( opinion ):
	return opinion(b"#gsl_case_name").text()

def _opinion_of( doc ):
	# depending on if we got the new look or the old look this is
	# two different names
	return doc( b"#gsl_opinion, #gs_opinion" )

def _included_children_of( opinion ):
	return opinion( b"p,center,h2,blockquote" )

def _footnotes_of( doc ):
	small = doc(b"small")[0]
	ps = list(small.itersiblings())
	return ps

def _p_to_content(footnotes, p, include_tail=True):
	accum = []
	kids = p.getchildren()
	if not kids:
		accum.append( _ElementPlainTextContentFragment( p ) )
	else:
		def _tail(e):
			if e is not None and e.tail and e.tail.strip():
				accum.append( interfaces.PlainTextContentFragment( e.tail.strip() ) )
		# complex element with nested children to deal with.
		if p.text and p.text.strip():
			accum.append( interfaces.PlainTextContentFragment( p.text ) )
		for kid in kids:
			if kid.tag == 'i':
				accum.append( _TextIT(kid.text) )
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
			_tail(kid)
		if include_tail:
			_tail(p)


	return interfaces.LatexContentFragment( ' '.join( [interfaces.ILatexContentFragment( x ) for x in accum] ) )

def _find_footnote( footnotes, sup ):
	# footnote refs
	ref_to = sup[0].get( 'href' )[1:]
	accum = []
	for i in footnotes:
		if _text_of( i ).startswith( ref_to ):
			# found it
			accum.append( _p_to_content( footnotes, i ) )
		elif _text_of( i ).startswith( '[' ) and accum: # The next one
			break
		elif accum:
			accum.append( _p_to_content( footnotes, i ) )
	return  _Footnote( ' '.join( [interfaces.ILatexContentFragment( x ) for x in accum] ) )

def _url_escape(u):
	return u.replace( '&', '\\&').replace( '_', '\\_' )

def _opinion_to_tex( doc, output=None, base_url=None ):
	tex = []

	name = _case_name_of( doc )
	tex.append( _Title( name ) )
	footnotes = _footnotes_of( doc )
	for i in footnotes:
		i.getparent().remove( i )
	inc_children = _included_children_of( _opinion_of( doc ) )

	current = _Chapter( name )
	tex.append( current )
	for inc_child in inc_children:
		if inc_child.tag in ('p','center'):
			current.add_child( _p_to_content( footnotes, inc_child ) )
		elif inc_child.tag in ('blockquote',):
			container = _Container( "\\begin{quote}" )
			container.add_child( _p_to_content( footnotes, inc_child ) )
			container.add_child( interfaces.LatexContentFragment( '\\end{quote}' ) )
			current.add_child( container )
		elif inc_child.tag == 'h2':
			section = _Section( _text_of( inc_child ).strip() )
			if hasattr( current, 'parent' ):
				current = getattr( current, 'parent' ) # Close the nesting. This deals with exactly one level
			current.add_child( section )
			setattr( section, 'parent', current )
			current = section

	if output is None:
		output = sys.stdout

	def _print(node):
		print( interfaces.ILatexContentFragment(node).encode('utf-8'), file=output )
		print( file=output )
		for child in getattr( node, 'children', ()):
			_print( interfaces.ILatexContentFragment(child) )

	lines = [br'\documentclass{book}', br'\usepackage{graphicx}', br'\usepackage{nti.contentrendering.ntilatexmacros}', br'\usepackage{hyperref}']
	if base_url:
		lines.append( br'\hyperbaseurl{' + _url_escape(base_url) + b'}' )
	lines.append( br'\begin{document}' )
	for line in lines:
		print( line, file=output )
	for node in tex:
		_print( node )
	print( br'\end{document}', file=output )

def main():
	from zope.configuration import xmlconfig
	xmlconfig.file( 'configure.zcml', package=nti.contentrendering )
	url = sys.argv[1]
	pq = _url_to_pyquery( url )
	_opinion_to_tex( pq, base_url=url )

if __name__ == '__main__':
	main()
