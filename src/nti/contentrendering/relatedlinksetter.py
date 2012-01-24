#!/usr/bin/env python
import os
import sys
from RenderedBook import RenderedBook, EclipseTOC
import itertools
import collections
import six

import logging
logger = logging.getLogger(__name__)

import domutils

from . import interfaces
from zope import interface
from zope import component

def main(args):
 	""" Main program routine """

	if not len(args)>0:
		print "Usage: contentsizesetter.py path/to/content"
		sys.exit()

	contentLocation = args.pop(0)

	performTransforms(RenderedBook(contentLocation))

def performTransforms(book, save_toc=True, context=None):
	"""
	Use the toc file to find all the pages in the contentLocation.
	Use phantomjs and js to render the page and extract the content size.
	Stuff the contentsize in the page as a meta tag and add it to toc
	:param book: Instance of :class:`RenderedBook`.
	:return: A list of tuples whose length is the number of transforms applied
	"""

	utils = list(component.getUtilitiesFor(interfaces.IStaticRelatedItemsAdder,context=context))
	for name, util in utils:
		logger.info( "Running transform %s (%s)", name, util )
		util.transform( book )

	if save_toc:
		book.toc.save()
	return utils


def _is_relation_of_type_and_qual(page1, ntiid, tpe, qualifier):

	return domutils.node_has_attribute_with_value(page1, 'ntiid', ntiid) \
		and domutils.node_has_attribute_with_value(page1, 'type', tpe) \
		and domutils.node_has_attribute_with_value(page1, 'qualifier', qualifier)

def _nodes_contain_relation_of_type_qual( alreadyrelatednodes, ntiid, tpe, qualifier ):
	for node in alreadyrelatednodes:
		if _is_relation_of_type_and_qual( node, ntiid, tpe, qualifier ):
			return True
	return False

def _node_of_id_type_qual( document, ntiid, tpe, qualifier="", nodename='page' ):
	pageNode = document.createElement( nodename )

	pageNode.setAttribute('ntiid', ntiid)
	pageNode.setAttribute('type', tpe)
	pageNode.setAttribute('qualifier', qualifier)

	return pageNode

class AbstractRelatedAdder(object):


	@classmethod
	def transform(cls,book):
		cls(book)()

	def __init__( self, book ):
		self.book = book

	def __call__(self):
		pass

	def _pageid_is_related_to_pageids(self, relatesTo, relatedTo, tpe, qualifier="", node_type='page'):
		"""
		Mark the TOC node for `relatesTo` as being related to each id in `relatedTo`.
		:return: A list of nodes added as new relations.
		"""
		relatesToNode = self.book.toc.getPageNodeWithNTIID(relatesTo)
		return self._pagenode_is_related_to_pageids( relatesToNode, relatedTo, tpe, qualifier, node_type )

	def _pagenode_is_related_to_pageids( self, relatesToNode, relatedToIds, tpe, qualifier="", node_type='page' ):
		"""
		:return: A list of nodes added as new relations.
		"""
		relatedPages = domutils.getOrCreateNodeInDocumentBeneathWithName(relatesToNode, 'Related')

		if not isinstance(relatedToIds, collections.Iterable) or isinstance(relatedToIds, six.string_types):
			relatedToIds = [relatedToIds]

		alreadyrelatednodes = list(relatedPages.childNodes)

		result = []
		for idToAdd in relatedToIds:
			if not _nodes_contain_relation_of_type_qual( alreadyrelatednodes, idToAdd, tpe, qualifier ):
				new_node =  _node_of_id_type_qual( self.book.toc.dom, idToAdd, tpe, qualifier, node_type )
				result.append( new_node )
				relatedPages.appendChild( new_node )
		return result

class TOCRelatedAdder(AbstractRelatedAdder):
	"""
	Adds relationships based on finding things that contain the same index terms.
	"""
	interface.classProvides(interfaces.IStaticRelatedItemsAdder)

	def __call__( self ):
		book = self.book
		relatedTuples = []
		theIndexs = book.document.getElementsByTagName('printindex')

		#some books (mathcounts) dont have an index.
		if len(theIndexs) < 1:
			return

		theIndex = theIndexs[0]

		for group in theIndex.groups:
			entries = [entry for column in group for entry in column]

			for entry in entries:
				related = self._recursive_related_pages_for_index_entry(entry)
				relatedTuples.append(related)

		relatedTuples = [t for t in relatedTuples if t[1]]

		for key, relationships in relatedTuples:
			for relatesTo, relatedTo in relationships:
				self._pageid_is_related_to_pageids( relatesTo, relatedTo, 'index', qualifier=key )

	def _recursive_related_pages_for_index_entry(self, entry):
		"""
		:return: A tuple (index key string, [list (relating pageId, related to page id)])
		"""

		eclipseTOC = self.book.toc
		def _error(node):
			page = eclipseTOC.getPageForDocumentNode(node)
			attrs = getattr(page, 'attributes')
			raise ValueError( "No NTIID for entry %s doc node %s page %s attrs %s" % (entry, node, page, attrs) )
		pages = [self.book.pages[eclipseTOC.getPageForDocumentNode(page).getAttribute('ntiid') or _error(page)]
				 for page
				 in entry.pages]
		pageIds = [page.ntiid for page in pages if page is not None]

		related = []
		related.extend( [x for x in itertools.permutations(pageIds, 2) if x[0] != x[1]] )

		for childEntry in entry.childNodes:
			childRelated = self._recursive_related_pages_for_index_entry(childEntry)
			related.extend(childRelated[1])

		return (entry.key.textContent, related)

class ExistingTOCRelatedAdder(AbstractRelatedAdder):
	"""
	Copies all related nodes from an existing TOC file.
	"""
	interface.classProvides(interfaces.IStaticRelatedItemsAdder)
	def __call__(self):
		existing_toc_file = os.path.join( self.book.contentLocation, '..', 'related-items.xml' )
		if not os.path.exists( existing_toc_file ):
			logger.info( "No existing related items at %s", existing_toc_file )
			return

		logger.info( "Merging existing related items at %s", existing_toc_file )
		existing_toc = EclipseTOC( existing_toc_file )
		for _, page in self.book.pages.items():
			ntiid = page.ntiid
			try:
				topic = existing_toc.getPageNodeWithNTIID( ntiid )
			except IndexError:
				continue
			else:
				for c in topic.childNodes:
					if c.nodeType != c.ELEMENT_NODE or c.localName != "Related":
						continue
					content_topic = self.book.toc.getPageNodeWithNTIID( ntiid )
					related_container = domutils.getOrCreateNodeInDocumentBeneathWithName(content_topic, 'Related')
					for related in c.childNodes:
						if related.nodeType == related.ELEMENT_NODE:
							related_container.appendChild( related )


import re
filere = re.compile('(?P<file>.*?\.html).*')

class LinkRelatedAdder(AbstractRelatedAdder):
	"""
	Adds relationships based on links found between pages (specified in the source text).
	"""
	interface.classProvides(interfaces.IStaticRelatedItemsAdder)

	def __call__( self ):
		for _, page in self.book.pages.items():
			self._add_outgoing_links_from_page( page )

	def _add_outgoing_links_from_page( self, page ):

		def file_part_of_link(link):
			# TODO: Shouldn't this just be path traversal?
			results = None

			match = filere.match(link)
			if match:
				results = match.group('file')

			return results

		fileNameAndLinkList = [(file_part_of_link(link), link) for link in page.outgoing_links]

		for fileNameAndLink in fileNameAndLinkList:
			fileName = fileNameAndLink[0]
			link = fileNameAndLink[1]

			if fileName and link:
				tocNodes = self.book.toc.getPageNodeWithAttribute('href', fileName)
				if not tocNodes: continue
				tocNode = tocNodes[0]
				self._pageid_is_related_to_pageids( page.ntiid, tocNode.getAttribute('ntiid'), 'link', qualifier=link )

