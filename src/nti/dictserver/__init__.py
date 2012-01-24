#/usr/bin/env python2.7

import os.path
from dictionary import ChromeDictionary

import re
import json

from zope import component
from . import interfaces

def __wiki_clean(defn):
	if not defn: return defn
	defn = re.sub( "\{\{.*?\}\}", "", defn ).replace( '[[', '').replace(']]', '').strip()
	return defn.replace( 'http://en.wiktionary.org/wiki/', '' )

def lookup( info, dictionary=None ):
	"""
	Given a WordInfo, fills it in.

	:param info: A :class:`WordInfo` or a string.
	:param dictionary: Implementation of :class:`interfaces.IDictionary` or None.
	:return: A :class:`WordInfo` with the definition filled in.
	"""
	if isinstance( info, basestring ):
		info = WordInfo( info )

	if dictionary is None:
		dictionary = component.queryUtility( interfaces.IDictionary )
	if dictionary is None:
		dictionary = ChromeDictionary(os.path.dirname(__file__) + '/../../wiktionary/dict.db')
		component.provideUtility( dictionary )


	s = dictionary.lookup(info.word)

	term = json.loads( s )
	#term = json.load(urllib2.urlopen("http://dictionary-lookup.org/" + info.word ))

	info.ipa = term.get('ipa')
	info.etymology = __wiki_clean(term.get('etymology'))
	dictInfo = DictInfo()
	for meaning in term.get('meanings',()):
		meaning.setdefault( 'examples', [] )
		dictInfo.addDefinition(DefInfo( [(__wiki_clean(meaning['content']),meaning['examples'])], meaning['type'] ) )
	info.addInfo( dictInfo )
	info.addInfo( LinkInfo( 'http://www.google.com/search?q=' + info.word ) )
	therInfo = TherInfo()
	info.addInfo( therInfo )
	for synonym in term.get('synonyms',()):
		therInfo.addSynonym( synonym )

	return info


from xml.dom.minidom import getDOMImplementation

class _InfoRoot(object):
	pass

class DefInfo(_InfoRoot):

	def __init__( self, definitions, partofspeech='noun' ):
		""" Definitions is a list of strings or tuples, with the first
		element in the tuple being the definition, and the second
		item, if any, being the examples. """
		self.definitions = definitions
		self.partofspeech = partofspeech

	def toXML( self, dom, parent ):
		for defn in self.definitions:
			defElem = dom.createElement( 'definition' )
			defElem.setAttribute( "partOfSpeech", self.partofspeech )
			if hasattr( defn, '__iter__' ):
				defElem.appendChild( dom.createTextNode( defn[0] ) )
				if len(defn) > 1:
					exs = [defn[1]]
					if hasattr( defn[1], '__iter__' ) :
						exs = defn[1]
					for ex in exs:
						exElem = dom.createElement( 'example' )
						exElem.appendChild( dom.createTextNode( ex ))
						defElem.appendChild( exElem )
			else:
				defElem.appendChild( dom.createTextNode( defn ) )
			parent.appendChild( defElem )

class WordInfo(_InfoRoot):

	def __init__( self, word ):
		self.ipa = None
		self.etymology = None
		self.word = word
		self.infos = []

	def addInfo( self, info ):
		self.infos.append( info )

	def __iter__(self):
		return self.infos.__iter__()



	def toXML( self ):
		""" Returns a DOM """
		dom = getDOMImplementation().createDocument( None, 'WordInfo',
													 None )

		top_element = dom.documentElement
		top_element.setAttribute( 'word', self.word )
		if isinstance( self.ipa, list ):
			for p in self.ipa:
				ipa = dom.createElement( 'ipa' )
				ipa.appendChild( dom.createTextNode( p ) )
				top_element.appendChild( ipa )
		if self.etymology:
			ety = dom.createElement( 'EtymologyInfo' )
			ety.appendChild( dom.createTextNode( self.etymology ) )
			top_element.appendChild( ety )
		for child in self:
			child.toXML( dom, top_element )
		# TODO: Could use Pyramid to construct this URL
		stylesheet = dom.createProcessingInstruction(
			'xml-stylesheet', 'href="static/style.xsl" type="text/xsl"')
		dom.insertBefore( stylesheet, top_element )
		return dom

	def toXMLString(self):
		return self.toXML().toxml( "UTF-8" )

	def writeXML(self, writer ):
		self.toXML().writexml( writer )

class DictInfo(_InfoRoot):

	def __init__( self ):
		self.definitions = []

	def addDefinition( self, definition ):
		self.definitions.append( definition )

	def __iter__(self):
		return self.definitions.__iter__()

	def toXML( self, dom, parent ):
		info = dom.createElement( "DictInfo" )
		parent.appendChild( info )
		for child in self:
			child.toXML( dom, info )



class LinkInfo(_InfoRoot):

	def __init__( self, href, title='Search on Google', source='Google', display='inline'):
		self.href = href
		self.source = source
		self.display = display
		self.title = title

	def toXML( self, dom, parent ):
		link = dom.createElement( 'LinkInfo' )
		link.setAttribute( 'href', self.href )
		link.setAttribute( 'source', self.source )
		link.setAttribute( 'display', self.display )
		link.setAttribute( 'title', self.title )
		parent.appendChild( link )

class TherInfo(_InfoRoot):

	def __init__(self):
		self.synonyms = []

	def addSynonym( self, synonym ):
		self.synonyms.append( synonym )


	def toXML( self, dom, parent ):
		if not self.synonyms: return
		info = dom.createElement( "TherInfo" )
		parent.appendChild( info )
		for child in self.synonyms:
			syn = dom.createElement( "synonym" )
			syn.appendChild( dom.createTextNode( child ) )
			info.appendChild( syn )



