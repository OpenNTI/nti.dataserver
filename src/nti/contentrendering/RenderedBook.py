#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from xml.dom.minidom import parse
from concurrent.futures import ProcessPoolExecutor
import os

from zope.deprecation import deprecate
from zope import interface
from BTrees.OOBTree import OOBTree

from nti.utils.minidom import minidom_writexml
from . import interfaces
from . import run_phantom_on_page
_runPhantomOnPage = run_phantom_on_page
from . import javascript_path

import html5lib
from html5lib import treewalkers, serializer, treebuilders

import urllib
from pyquery import PyQuery
import codecs


class RenderedBook(object):

	interface.implements(interfaces.IRenderedBook)

	TOC_FILE_NAME = 'eclipse-toc.xml'

	document = None
	contentLocation = None
	tocFile = None

	def __init__(self, document, location):
		self.contentLocation = os.path.abspath( location )
		self.tocFile = os.path.join(self.contentLocation, self.TOC_FILE_NAME)
		self.document = document
		self.pages = OOBTree()
		self._toc = None
		self._processPages()

		for pageid, page in self.pages.items():
			logger.debug( '%s -> %s', pageid, page.ntiid )
		logger.info( "Book at %s had %d pages", os.path.abspath(location), len(self.pages) )


	def _processPages(self):
		javascript =  javascript_path( 'getPageInfo.js')

		results = self.runPhantomOnPages(javascript)

		pages = {}
		for pageinfo in results.values():
			pages[pageinfo['ntiid']] = pageinfo

		def set_info(root):
			if root.ntiid:
				page_info = pages.get( root.ntiid )
				if page_info: root._pageInfo = page_info
				self.pages[root.ntiid] = root

			for child in root.childTopics:
				set_info( child )
		set_info( self.toc.root_topic )

	@property
	def jobname(self):
		try:
			return self.document.userdata.get('jobname', '')
		except AttributeError:
			return ''

	@property
	def toc(self):
		"""
		An :class:`EclipseTOC` object. Changes made to the returned
		object are persistent in memory for the life of this object (and possibly on disk).
		"""
		if self._toc is None:
			self._toc = EclipseTOC(self.tocFile)
		return self._toc

	@deprecate("Prefer the toc property")
	def getEclipseTOC(self):
		"""
		Returns a newly parsed TOC object.
		"""
		return EclipseTOC(self.tocFile)

	def _get_phantom_function(self):
		"""
		This cannot be simply a class attribute because
		it gets wrapped as an instance method automatically.
		:return: The pickalable function to map across nodes.
		"""
		return _runPhantomOnPage

	def runPhantomOnPages(self, script, *args):
		"""
		:return: Dictionary of {(ntiid,href,label) => object from script}
		"""

		eclipseTOC = self.toc
		nodesForPages = eclipseTOC.getPageNodes()

		# Notice that we very carefully do not send anything attached
		# to the DOM itself over to the executor processess. Not only
		# is it large to serialize, it is potentially
		# risky: arbitrary, non-pickalable objects could get attached there
		results = {}

		with ProcessPoolExecutor() as executor:
			for the_tuple in executor.map( self._get_phantom_function(),
										   [os.path.join( self.contentLocation, node.getAttribute( b'href' ) )
											for node in nodesForPages],
										   [script] * len(nodesForPages),
										   [args] * len(nodesForPages),
										   [(node.getAttribute(b'ntiid'),node.getAttribute(b'href'),node.getAttribute(b'label'))
											 for node in nodesForPages]):
				key = the_tuple[0]
				result = the_tuple[1]

				results[key] = result

		return results

class EclipseTOC(object):
	interface.implements(interfaces.IEclipseMiniDomTOC)

	def __init__(self, f):
		self.filename = f
		self.dom = parse(self.filename)
		# We may or may not have an href for the root toc yet.
		# If not, assume it to be index.html
		tocs = self.dom.getElementsByTagName( b"toc" )
		if len(tocs) == 1 and not tocs[0].getAttribute( b"href" ):
			tocs[0].setAttribute( b"href", "index.html" )
		self._toc = None

	@property
	@deprecate("Prefer the `filename` property.")
	def file(self):
		return self.filename

	@property
	def contentLocation(self):
		return os.path.split( self.filename )[0]

	@property
	def root_topic(self):
		"""
		The `IEclipseMiniDomTopic` representing the root
		of the topic tree (index.html).
		"""
		if not self._toc:
			self._toc = _EclipseTOCMiniDomTopic( self.dom.getElementsByTagName( b"toc" )[0],
												 self.contentLocation )
		return self._toc

	# FIXME These names need adjustment. There are "page" XML nodes, but the method
	# names below use "page" to mean a page in the the TOC, i.e., a 'topic' or 'toc'
	# node

	def getPageForDocumentNode(self, node):
		#Walk up the node try untill we find something with an id that matches our label
		if node is None:
			return None

		title = None
		if getattr(node, 'title', None):
			title = node.title.textContent if hasattr(node.title, 'textContent') else node.title
		matchedNodes = []
		if title:
			matchedNodes = self.getPageNodeWithAttribute(b'label', title)

		if len(matchedNodes) > 0:
			return matchedNodes[0]


		return self.getPageForDocumentNode(node.parentNode)

	def getPageNodeWithNTIID(self, ntiid, node=None):
		"""
		:raises IndexError: If no such node can be found.
		"""
		return self.getPageNodeWithAttribute(b'ntiid', value=ntiid, node=node)[0]

	def getPageNodeWithAttribute(self, name, value=None, node=None):
		"""
		:param node: The node to begin the search at. Defaults to the root.
		:return: A list of DOM nodes.
		"""

		if node is None:
			node = self.getRootTOCNode()

		nodes = []
		if (node.nodeName == 'topic' or node.nodeName == 'toc') and \
			   getattr(node, 'hasAttribute', None) and node.hasAttribute(name):
			if value is None or node.getAttribute(name) == value:
				nodes.append(node)

		for child in node.childNodes:
			nodes.extend(self.getPageNodeWithAttribute(name, value=value, node=child))

		return nodes

	def getRootTOCNode(self):
		return self.dom.getElementsByTagName(b'toc')[0]

	def getPageNodes(self):
		":return: Nodes for all top-level HTML pages. Nodes for interior sections are not returned."
		return [x for x in self.getPageNodeWithAttribute(b'href')
				if (x.hasAttribute(b'ntiid') and '#' not in x.getAttribute(b'href'))]

	def save(self):
		minidom_writexml( self.dom, self.filename )


class _EclipseTOCMiniDomTopic(object):
	"""
	Represents a topic from an eclipse TOC, both the TOC information
	and the on-disk page information.

	Attributes
	save_dom: If True (the default) then we will save the
	page dom upon modification.
	location, sourceFile: The full path to the file on disk
	filename, href: The filename-only portion of the location
	topic, toc_dom_node: An minidom Element
	"""

	interface.implements( interfaces.IEclipseMiniDomTopic )

	save_dom = True

	modifiedTopic = False
	modifiedDom = False
	_dom = None
	_doc = None
	ordinal = 1
	_childTopics = None

	def __init__( self, topic_dom_node,
				  contentLocation,
				  href=None,
				  pageInfo=None,
				  title=None ):
		"""
		:param string contentLocation: The full path to the directory root for the content.
		:param string href: If given, the filename of the on-disk page for this
			topic. If not given, we will use the 'href' attribute in the dom.
		:param string title: The title of the page (the 'label' attribute in the dom).
			If not given, we will use the title in the on-disk page.
		:param dict pageInfo: Information dictionary about the page.
		"""
		self.topic = topic_dom_node
		self.toc_dom_node = self.topic
		self.contentLocation = contentLocation

		# These four are identical for b/w/c
		self.sourceFile = href or (self.get_topic_filename( )
								   and os.path.join( contentLocation, self.get_topic_filename() ) )
		self.location = self.sourceFile

		self.href = href or os.path.split(self.sourceFile)[-1]
		self.filename = self.href


		self._pageInfo = pageInfo if pageInfo is not None else OOBTree()

		self._title = title


	# TODO: Clean up some of these names.

	@property
	def ntiid(self):
		ntiid = self._pageInfo.get( 'ntiid' )
		if not ntiid and self.dom:
			ntiid = self.read_ntiid()
			self._pageInfo['ntiid'] = ntiid
		return ntiid

	@property
	def title(self):
		title = self._title
		if not title and self.dom:
			title = self.get_title()
			self._title = title
		return title
	label = title

	@property
	@deprecate("Prefer to access the specific property")
	def pageInfo(self):
		return self._pageInfo

	@property
	def outgoing_links(self):
		"A sequence of strings naming links from this page."
		return self._pageInfo.get('OutgoingLinks',())

	@property
	def scroll_height(self):
		"""
		:return: An integer giving the relative height of the content of this page.
		:raises KeyError: If no size is known.
		"""
		return self.get_scroll_height( default=self )

	@property
	def scroll_width(self):
		"""
		:return: An integer giving the relative width of the content of this page.
		:raises KeyError: If no size is known
		"""
		return self.get_scroll_width( default=self )

	def get_scroll_height( self, default=-1 ):
		"""
		:return: The scroll height if known, otherwise the `default` (-1)
		"""
		return self._get_int( 'scrollHeight', default=default )

	def get_scroll_width( self, default=-1 ):
		"""
		:return: The scroll width if known, otherwise the `default` (-1)
		"""
		return self._get_int( 'scrollWidth', default=default )

	def _get_int( self, key, default=-1 ):
		try:
			return self._pageInfo[key]
		except KeyError:
			if default == self:
				raise
			return default

	def __repr__( self ):
		return b"%s('%s', %s, '%s', '%s')" % (self.__class__.__name__,
											  str(self.location).encode( 'string_escape' ),
											  self._pageInfo,
											  str(self.href).encode( 'string_escape' ),
											  (self.label or '[MISSING]').encode('utf-8').encode( 'string_escape' ))

	@property
	@deprecate("Prefer `childTopics`; this returns arbitrary Nodes")
	def childNodes(self):
		"""
		:return: An iterable of :class:`_Topic` objects representing the children
			of this object.
		"""
		childCount = 1
		for x in self.topic.childNodes:
			result = self.__class__( x, self.contentLocation )
			result.ordinal = childCount
			childCount += 1
			yield result

	@property
	def childTopics(self):
		"""
		:return: An iterable of :class:`_EclipseTOCMiniDomTopic` objects representing the topic element children
			of this object. Only those topics that have files are returned (if the topic is a reference
			to a fragment, it is not returned).
		"""
		if self._childTopics is None:
			self._childTopics = []
			childCount = 1
			for x in self.topic.childNodes:
				# Exclude things with hrefs that look like fragments (but do include things that are missing hrefs altogether)
				# both of these measures are for backwards compatibility
				if x.nodeType == x.ELEMENT_NODE and x.localName == 'topic' \
				  and (not x.attributes.has_key( b'href' ) or '#' not in x.attributes[b'href'].value):
					result = self.__class__( x, self.contentLocation )
					result.ordinal = childCount
					childCount += 1
					self._childTopics.append( result )
		return self._childTopics

	@property
	def nodeType(self): return self.topic.nodeType

	@property
	def localName(self): return self.topic.localName

	@property
	def dom(self):
		# TODO: Under some circumstances we should be discarding this dom for memory reasons
		if not self._dom:
			if not self.sourceFile or not os.path.exists( self.sourceFile ):
				# Careful with logging here: __repr__ calls this method!
				logger.warn( "Unable to get dom for missing file %s in %s", self.sourceFile, self.__dict__ )
				return None
			# By using the HTML5 parser, we can get more consistent results,
			# regardless of how the templates were setup. And when we write, we'll
			# be in a normalized form for all browsers. One immediate cost is that
			# it's quite a bit slower to parse than pyquery's native methods
			dom = None
			p = html5lib.HTMLParser( tree=treebuilders.getTreeBuilder("lxml"), #PyQuery needs lxml doc
									 namespaceHTMLElements=False )

			with open(self.sourceFile) as f:
				doc = p.parse( f, encoding='utf-8' )
				dom = PyQuery( doc.getroot() )

			# try:
			# we've seen this throw ValueError: I/O operation on closed file
			# we've also seen AttributeError: 'NoneType' object has no attribute 'xpath'
			# on dom("body")
			# 	dom = PyQuery( filename=self.sourceFile )
			# 	body_len = len(dom("body"))
			# except (ValueError,AttributeError):
			# 	logger.warn( "Failed to parse %s as XML. Will try HTML.", self.sourceFile, exc_info=False )
			# if body_len != 1:
			# 	dom = PyQuery( filename=self.sourceFile, parser="html" )
			self._doc = doc
			self._dom = dom
		return self._dom

	def write_dom(self, force=False):
		if not self._dom: return

		if self.save_dom or force:
			# This matches nti_render. See rationale there.
			with codecs.open( self.sourceFile, 'w',
							  encoding='ascii',
							  errors='xmlcharrefreplace') as f:
				# We parsed with html5lib, we need to write with html5lib
				# If we don't, if we write with etree:
				# ... etree.tostring( self._doc, method='html', encoding=unicode )
				# we wind up with things that break in HTML5. Specifically, <SVG> nodes
				# wind up with a namespace, which is not acceptable
				walker = treewalkers.getTreeWalker("lxml")
				# Write the original, whole doc, which will reflect the PyQuery modifications (not self._dom)
				# This way we get the doctype
				stream = walker(self._doc)
				s = serializer.xhtmlserializer.XHTMLSerializer(inject_meta_charset=False,
															   omit_optional_tags=False,
															   quote_attr_values=True,
															   strip_whitespace=True,
															   use_trailing_solidus=True,
															   space_before_trailing_solidus=True,
															   sanitize=False )
				for i in s.serialize(stream):
					f.write( i )

				f.flush()

	def set_ntiid( self ):
		"""
		Set the NTIID for the specifed topic if one is not already present.
		"""
		if self.topic.attributes.get( b'ntiid' ): # 'in' doesn't work with this dict-like thing
			# No need to read from the file if it was already present.
			#logger.info( "Not setting ntiid because %s trumps %s", self.topic.attributes['ntiid'].value, self.read_ntiid() )
			return False

		ntiid = self.read_ntiid()
		if ntiid:
			self.topic.attributes[b"ntiid"] = ntiid
			self._pageInfo[b'ntiid'] = ntiid
			self.modifiedTopic = True

		return self.modifiedTopic

	def read_ntiid(self):
		"""
		Return the NTIID from the specified file
		"""
		try:
			return self.dom(b"meta[name=NTIID]").attr( b"content" )
		except IOError:
			logger.debug( "Unable to open file %s", self.sourceFile, exc_info=True )
			return None

	def get_title( self ):
		return self.dom(b"title").text()

	def get_topic_filename( self ):
		if self.topic.attributes and self.topic.attributes.get(b'href'):
			return self.topic.attributes.get(b'href').value

	def topic_with_filename( self, filename ):
		"""
		:return: The topic having a matching filename, this object or beneath it, or None.
		"""
		if self.get_topic_filename( ) == filename:
			return self
		for kid in self.childTopics:
			node = kid.topic_with_filename( filename )
			if node:
				return node

	def set_background_image( self, image_path ):

		dom = self.dom
		if dom is None:
			return False

		dom(b"body").attr[b"style"] = r"background-image: url('" + image_path + r"')"
		self.write_dom()

		self.modifiedDom = True
		return self.modifiedDom

	def get_background_image( self ):
		dom = self.dom
		if dom is None:
			return None
		return dom(b'body').attr(b'style')

	def set_content_height( self, contentHeight ):
		dom = self.dom
		if dom is None:
			return None
		dom( b"meta[name=NTIRelativeScrollHeight]" ).attr[b'content'] = str(contentHeight)
		self.modifiedDom = True
		self.write_dom()

		pageNode = self.toc_dom_node

		pageNode.attributes[b'NTIRelativeScrollHeight'] = str(contentHeight)
		self.modifiedTopic = True
		return True

	def set_default_sharing_group( self, sharedWith ):
		self.topic.attributes[b'sharedWith'] = sharedWith
		self.modifiedTopic = True
		return self.modifiedTopic

	def get_default_sharing_group( self ):
		if self.topic.attributes and self.topic.attributes.get(b'sharedWith'):
			return self.topic.attributes.get(b'sharedWith').value
		else: return None

	def has_icon( self ):
		return (self.topic.attributes and self.topic.attributes.get(b'icon'))

	def set_icon( self, icon ):
		self.topic.attributes[b'icon'] = urllib.quote( icon )
		self.modifiedTopic = True
		return self.modifiedTopic

	def get_icon( self ):
		if self.has_icon():
			return urllib.unquote(self.topic.attributes.get(b'icon').value)
		else: return None

	def set_label( self, label ):
		self.topic.attributes[b'label'] = label
		self.modifiedTopic = True
		return self.modifiedTopic

	def is_chapter(self):
		attributes = self.topic.attributes
		if attributes:
			label = attributes.get(b'label',None)
			return (label and label.value != 'Index')
		return False
