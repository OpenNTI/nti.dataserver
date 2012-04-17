#!/usr/bin/env python2.7

from __future__ import print_function, unicode_literals

import re
from lxml import etree
from lxml.cssselect import CSSSelector

from zope import interface
from . import interfaces

_NAMESPACES = {
	'sfa': "http://developer.apple.com/namespaces/sfa",
	'sf' : "http://developer.apple.com/namespaces/sf",
	'xsi': "http://www.w3.org/2001/XMLSchema-instance",
	'key': "http://developer.apple.com/namespaces/keynote2"}

def _sel( s ): return CSSSelector( s, namespaces=_NAMESPACES )

SLIDE = _sel( 'key|slide' )
MASTER_SLIDE = _sel( 'key|master-slide' )
###
## A slide is structured something like this:
#   {http://developer.apple.com/namespaces/keynote2}stylesheet
#   {http://developer.apple.com/namespaces/keynote2}style-ref
#   {http://developer.apple.com/namespaces/keynote2}title-placeholder
#   {http://developer.apple.com/namespaces/keynote2}body-placeholder
#   {http://developer.apple.com/namespaces/keynote2}object-placeholder
#   {http://developer.apple.com/namespaces/keynote2}slide-number-placeholder
#   {http://developer.apple.com/namespaces/keynote2}page
#   {http://developer.apple.com/namespaces/keynote2}thumbnails
#   {http://developer.apple.com/namespaces/keynote2}events
#   {http://developer.apple.com/namespaces/keynote2}sticky-notes
#   {http://developer.apple.com/namespaces/keynote2}build-chunks
#   {http://developer.apple.com/namespaces/keynote2}master-ref
#   {http://developer.apple.com/namespaces/keynote2}notes
## Content can be found in the title, body, and object placeholders.
## For graphics, it can also be found in the <page> <layers>

# Text-body can occur both within key:text and sf:text
# don't ask me what the difference is
KEY_TEXT = _sel( 'key|text' )
SF_TEXT = _sel( 'sf|text' )
TEXTS = _sel( 'key|text, sf|text' )

# Many of the paragraph elements are empty (placeholders?)
# the following select non-empty text elements
NE_P = _sel( 'sf|p:not(:empty)' )
P = _sel( 'sf|p' )

# Movies
MOVIE_MAIN = _sel( 'sf|movie-media sf|main-movie' )
MOVIE_POSTER = _sel( 'sf|movie-media sf|poster-image' )

# Images
IMAGE_DATA = _sel( 'sf|image-media sf|filtered-image sf|data' )

TEXT_OR_IMAGE_DATA = _sel( 'sf|image-media sf|filtered-image sf|data, key|text, sf|text' )

# Master slides define stylesheets, things can have stylesheet-refs

def _localname( element ):
	return etree.QName( element ).localname if element is not None else None

def _latex_escape( txt, section=False ):
	txt = txt.replace( u'\u201d', "''" )
	txt = txt.replace( u'\u201c', "``" )
	txt = txt.replace( u'\u2019', "'" )
	math_repl = (lambda m: '$' + m.group( 1 ) + '$')\
					if not section \
					else (lambda m: '')
	txt = re.sub( '(_+)', math_repl, txt )
	return txt
_FORCED_NEWLINE = '\\\\\n'

def _text_of( p ):
	return etree.tostring( p, encoding=unicode, method='text' )

class _ElementPlainTextContentFragment(unicode):
	interface.implements(interfaces.IPlainTextContentFragment)

	def __new__( cls, element ):
		return super(_ElementPlainTextContentFragment,cls).__new__( cls, _text_of( element ) )

	def __init__( self, element=None ):
		# Note: __new__ does all the actual work, because these are immutable as strings
		super(_ElementPlainTextContentFragment,self).__init__( _text_of( element ) )
		self.element = element

class _Image(object):
	interface.implements(interfaces.ILatexContentFragment)
	path = None
	def __init__( self, path=None ):
		self.path = path

	def __str__( self ):
		return "\includegraphics[width=400px]{" + self.path + '}'

class _List(object):
	interface.implements(interfaces.ILatexContentFragment)
	level = 1
	def __init__( self ):
		self.children = []

	def __str__( self ):
		lines = ['\t' * self.level + r'\begin{itemize}']
		for kid in self.children:
			line = '\t' * self.level
			if not isinstance( kid, _List ) and kid != _FORCED_NEWLINE:
				line = line + '\item '
			line = line + unicode( interfaces.ILatexContentFragment( kid ) )
			lines.append( line )
		lines.append( '\end{itemize}' )
		return '\n'.join( (unicode(line) for line in lines) )

class _Slide(object):
	interface.implements(interfaces.ILatexContentFragment)
	element = None
	slide_num = 0
	def __init__(self):
		self.text_elements = []

	def add_text_element( self, p ):
		if p is not None and _text_of( p ):
			self.text_elements.append( _ElementPlainTextContentFragment( p ) )

	@property
	def children(self): return self.text_elements

	def __str__( self ):

		lines = [u'\section{' + interfaces.ILatexContentFragment( self.text_elements[0] ) + '}'
				 if self.text_elements
				 else '']

		for kid in self.text_elements:
			lines.append( interfaces.ILatexContentFragment( kid ) )
		return '\n'.join( (unicode(line) for line in lines) )

class _MasterSlide(_Slide):

	def __init__( self ):
		super(_MasterSlide,self).__init__()
		self.texts = []

	def add_text_element( self, p ):
		super(_MasterSlide,self).add_text_element( p )
		if p is not None and _text_of( p ):
			self.texts.append( _text_of( p ) )

class _Presentation(object):

	def __init__( self ):
		self.master_slides = []
		self.slides = []

	def text_is_on_master( self, text ):
		"""
		Answer whether or not the given text is on the master slide.
		"""
		for master_slide in self.master_slides:
			if text in master_slide.texts:
				return True

	def to_latex( self ):
		lines = [br'\documentclass{book}', br'\usepackage{graphicx}', br'\begin{document}']
		for slide in self.slides:
			lines.append( interfaces.ILatexContentFragment( slide ) )
		lines.append( r'\end{document}' )
		return '\n'.join( (unicode(line) for line in lines) )

	def remove_duplicated_masters( self ):
		lines = {}
		for slide in self.slides:
			for text in slide.text_elements:
				lines[text] = lines.get( text, 0 ) + 1

		for k, v in lines.iteritems():
			if v >= len(self.slides) - 2: # -2 for title, QandA
				for slide in self.slides:
					try:
						slide.text_elements.remove( k )
					except ValueError: pass

def extract_text( keynote, jobname, imagedir ):
	# We simple-mindedly extract any text that
	# duplicates that which comes from a master slide
	# TODO: This should take the master-slide-ref into account
	presentation = _Presentation()


	for master_slide in MASTER_SLIDE( keynote ):
		slide = _MasterSlide()
		slide.element = master_slide
		presentation.master_slides.append( slide )

		for p in P( master_slide ):
			slide.add_text_element( p )


	def _find_section_title( element ):
		# TODO: Heuristics about font size, etc
		for text in TEXTS( element ):
			for p in P( text ):
				if not _text_of( text ) or presentation.text_is_on_master( _text_of( p ) ):
					continue
				return p.text

	def _make_fragments( p):
		fragments = [_ElementPlainTextContentFragment( p )]
		try:
			if p.find( './/{' + _NAMESPACES['sf'] + '}br' ) is not None:
				fragments.append( interfaces.LatexContentFragment( '\\\\\n' ) )
		except IndexError:
			pass
		return fragments

	cur_section_title = None
	slide_num = 1
	for slide in SLIDE( keynote ):
		the_slide = _Slide( )
		the_slide.element = slide
		the_slide.slide_num = slide_num
		slide_num += 1
		presentation.slides.append( the_slide )

		new_section_title = _find_section_title( slide )
		if new_section_title and new_section_title != cur_section_title:
			cur_section_title = new_section_title
		for text_or_img in TEXT_OR_IMAGE_DATA( slide ):
			# TODO: Some people do a poor job
			# marking up the document, using linebreaks for
			# separation of bullet items. Detect that.
			if _localname( text_or_img ) == 'text':
				text = text_or_img
				for p in P( text ):
					text_body = etree.tostring( p, encoding=unicode )
					if not text_body or presentation.text_is_on_master( text_body ):
						continue
					if p.get( '{http://developer.apple.com/namespaces/sf}list-level' ):
						fragments = _make_fragments( p )

						level = int( p.get( '{http://developer.apple.com/namespaces/sf}list-level' ) )
						parent = the_slide
						grandparent = None
						for _ in range( 0, level ):
							grandparent = parent
							parent = parent.children[-1]

						parent = parent if hasattr( parent, 'children' ) else grandparent
						if isinstance( parent, _List ) and parent.level == level:
							parent.children.extend( fragments )
						else:
							lst = _List()
							lst.level = level
							lst.children.extend( fragments )
							parent.children.append( lst )


					else:
						the_slide.text_elements.extend( _make_fragments( p ) )
			else:
				image_data = text_or_img
				the_slide.text_elements.append( _Image( image_data.get( '{' + _NAMESPACES['sf'] + '}path' ) ) )

			try:
				int(the_slide.text_elements[-1])
			except (TypeError,ValueError):
				pass
			else:
				del the_slide.text_elements[-1]

			slide_image_file_name = u'%s_%03d.png' % (jobname,the_slide.slide_num)
			slide_image_file_name = os.path.join( imagedir, slide_image_file_name )

		if os.path.exists( slide_image_file_name ):
			the_slide.children.append( _Image( os.path.splitext(slide_image_file_name)[0] ) )

	presentation.remove_duplicated_masters()
	return presentation


if __name__ == '__main__':
	from zope.configuration import xmlconfig
	import nti.contentrendering
	import sys
	import os.path

	xmlconfig.file( 'configure.zcml', package=nti.contentrendering )

	filename = sys.argv[1]
	basename = os.path.basename( filename )
	jobname = os.path.splitext( basename )[0]

	doc = etree.parse( filename )
	pres = extract_text( doc, jobname, os.path.join( os.path.dirname( filename ), 'SlideImages' )  )
	print( pres.to_latex() )
