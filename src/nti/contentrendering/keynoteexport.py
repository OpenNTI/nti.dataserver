#!/usr/bin/env python2.7

from __future__ import print_function, unicode_literals

import re
from lxml import etree
from lxml.cssselect import CSSSelector

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

def extract_text( keynote ):
	# We simple-mindedly extract any text that
	# duplicates that which comes from a master slide
	# TODO: This should take the master-slide-ref into account
	master_text = []
	for master_slide in MASTER_SLIDE( keynote ):
		for p in P( master_slide ):
			if p.text:
				master_text.append( p.text )
	def _find_section_title( element ):
		# TODO: Heuristics about font size, etc
		for text in TEXTS( slide ):
			for p in P( text ):
				if not p.text or p.text in master_text: continue
				return p.text

	cur_section_title = None
	for slide in SLIDE( keynote ):
		new_section_title = _find_section_title( slide )
		if new_section_title and new_section_title != cur_section_title:
			print( "\section{" + _latex_escape( new_section_title, section=True ) + "}" )
			cur_section_title = new_section_title
		for text_or_img in TEXT_OR_IMAGE_DATA( slide ):
		#for text in TEXTS( slide ):
			# TODO: Some people do a poor job
			# marking up the document, using linebreaks for
			# separation of bullet items. Detect that.
			# TODO: LaTeX literals
			#print( b"\tXML: " + etree.tostring( text, encoding='utf-8' ) )
			if _localname( text_or_img ) == 'text':
				text = text_or_img
				for p in P( text ):
					if not p.text or p.text in master_text: continue
					print( _latex_escape( p.text ) )
					try:
						if _localname( p[-1] ) == 'br':
							print( ' ' )
					except IndexError: pass
			else:
				image_data = text_or_img
				print( "\includegraphics[width=400px]{" + image_data.get( '{' + _NAMESPACES['sf'] + '}path' ) + "}" )

if __name__ == '__main__':
	doc = etree.parse( '/Users/jmadden/tmp/RainforestClean/index.apxl.gz' )
	print( br"""\documentclass{book}
	\usepackage{graphicx}
	\begin{document}
	""" )
	extract_text( doc )
	print( r"\end{document}" )
