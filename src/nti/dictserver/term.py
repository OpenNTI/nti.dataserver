#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of dictionary term objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from xml.dom.minidom import getDOMImplementation

from zope import interface

from nti.dictserver.interfaces import IDictionaryTerm

_InfoRoot = object

@interface.implementer(IDictionaryTerm)
class DictionaryTerm(_InfoRoot):

	ipa = None
	etymology = None

	def __init__(self, word):
		self.word = word
		self.infos = []

	def addInfo(self, info):
		self.infos.append(info)

	def __iter__(self):
		return self.infos.__iter__()

	def __len__(self):
		"""
		How many infos we hold. Note that this also makes us False when empty.
		"""
		return len(self.infos)

	def findInfo(self, clazz):
		"""
		Return the first instance of the given class that we hold.
		"""
		for info in self:
			if isinstance(info, clazz):
				return info

	def toXML(self):
		""" Returns a DOM """
		dom = getDOMImplementation().createDocument(None, 'WordInfo', None)

		top_element = dom.documentElement
		top_element.setAttribute('word', self.word)
		if isinstance(self.ipa, list):
			for p in self.ipa:
				ipa = dom.createElement('ipa')
				ipa.appendChild(dom.createTextNode(p))
				top_element.appendChild(ipa)
		if self.etymology:
			ety = dom.createElement('EtymologyInfo')
			ety.appendChild(dom.createTextNode(self.etymology))
			top_element.appendChild(ety)
		for child in self:
			child.toXML(dom, top_element)
		# TODO: Could/should use Pyramid to construct this URL
		stylesheet = dom.createProcessingInstruction(
			'xml-stylesheet', 'href="static/style.xsl" type="text/xsl"')
		dom.insertBefore(stylesheet, top_element)
		return dom

	def toXMLString(self, encoding='UTF-8'):
		return self.toXML().toxml(encoding=encoding)

	def writeXML(self, writer):
		self.toXML().writexml(writer)

class DefInfo(_InfoRoot):
	"""
	Information about dictionary definitions, grouped by part of speech.
	"""

	def __init__(self, definitions, partofspeech='noun'):
		""" Definitions is a sequence of strings or tuples, with the first
		element in the tuple being the definition, and the second
		item, if any, being the examples. """
		self.definitions = definitions
		self.partofspeech = partofspeech

	def toXML(self, dom, parent):
		for defn in self.definitions:
			defElem = dom.createElement('definition')
			defElem.setAttribute("partOfSpeech", self.partofspeech)
			if hasattr(defn, '__iter__'):
				defElem.appendChild(dom.createTextNode(defn[0]))
				if len(defn) > 1:
					exs = [defn[1]]
					if hasattr(defn[1], '__iter__') :
						exs = defn[1]
					for ex in exs:
						exElem = dom.createElement('example')
						exElem.appendChild(dom.createTextNode(ex))
						defElem.appendChild(exElem)
			else:
				defElem.appendChild(dom.createTextNode(defn))
			parent.appendChild(defElem)

class DictInfo(_InfoRoot):
	"""
	Definitions for a term from a single dictionary source.
	"""

	def __init__(self):
		self.definitions = []

	def addDefinition(self, definition):
		self.definitions.append(definition)

	def __iter__(self):
		return self.definitions.__iter__()

	def __len__(self):
		"""
		How many definitions we hold. Note that this also makes us False when empty.
		"""
		return len(self.definitions)

	def toXML(self, dom, parent):
		info = dom.createElement("DictInfo")
		parent.appendChild(info)
		for child in self:
			child.toXML(dom, info)

class LinkInfo(_InfoRoot):

	def __init__(self, href, title='Search on Google', source='Google', display='inline'):
		self.href = href
		self.source = source
		self.display = display
		self.title = title

	def toXML(self, dom, parent):
		link = dom.createElement('LinkInfo')
		link.setAttribute('href', self.href)
		link.setAttribute('source', self.source)
		link.setAttribute('display', self.display)
		link.setAttribute('title', self.title)
		parent.appendChild(link)

class TherInfo(_InfoRoot):
	"""
	Thesaurus information for a term from a single source.
	"""

	def __init__(self):
		self.synonyms = []

	def addSynonym(self, synonym):
		self.synonyms.append(synonym)

	def __len__(self):
		"""
		How many synonyms we hold. Note that this also makes us False when empty.
		"""
		return len(self.synonyms)

	def toXML(self, dom, parent):
		if not self.synonyms: 
			return
		info = dom.createElement("TherInfo")
		parent.appendChild(info)
		for child in self.synonyms:
			syn = dom.createElement("synonym")
			syn.appendChild(dom.createTextNode(child))
			info.appendChild(syn)
