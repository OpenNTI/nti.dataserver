#!/usr/bin/env python

from __future__ import unicode_literals, print_function

# disable "super on old-style class for Components, it is new-style"
# pylint: disable=E1002

from zope import schema
from zope import interface

class IEclipseMiniDomTOC(interface.Interface):
	"""
	Represents the 'eclipse-toc' in a :mod:`xml.dom.minidom` format.
	"""

	filename = schema.TextLine(
		title="The location on disk of the eclipse-toc.xml file.")

	dom = interface.Attribute("The minidom representing the parsed contents of the file.")

	def save():
		"""
		Causes the in-memory contents of the `dom` to be written to disk.
		"""

class IEclipseMiniDomTopic(interface.Interface):
	"""
	Represents a `topic` element from the table-of-contents.
	"""

	ordinal = schema.Int(title="The number (starting at 1) representing which nth child of the parent I am.")

	childTopics = schema.Iterable(title="All the child topics of this topic.")

	dom = interface.Attribute('The :class:`pyquery.pyquery.PyQuery` object representing the HTML contents. Will be None if not parsable')

	ntiid = schema.TextLine(title='The NTIID of this content')

	def write_dom(force=False):
		"Causes the in-memory `dom` to be written to disk at the file it was read from."

class IRenderedBook(interface.Interface):

	document = interface.Attribute("The plasTeX Document object used to create the rendering.")

	contentLocation = schema.TextLine(
		title=u"The location of the directory on disk containing the content")

	toc = schema.Object(IEclipseMiniDomTOC,
						 title="The shared in-memory TOC for this book.")

	jobname = schema.TextLine(
		title="The name of the rendering job that produced this book, or the empty string.",
		default='')

	tocFile = schema.TextLine(
		title=u"The location of the eclipse toc file")

class IIconFinder(interface.Interface):
	"""
	Something that can find an icon for a topic in a rendered book.
	"""

	def find_icon():
		"""
		:return: A URL path relative to the content location giving
			an icon, or None if there is no icon.
		"""

class IBackgroundImageFinder(interface.Interface):
	"""
	Something that can find a background image for a topic in a rendered book.
	"""

	def find_background_image():
		"""
		:return: A URL path relative to the content location giving
			an image, or None if there is no icon.
		"""

class IDocumentTransformer(interface.Interface):
	"""
	Given a plasTeX DOM document, mutate the document
	in place to achieve some specified end. IDocumentTransformer
	*should* perform an idempotent transformation.
	"""

	def transform(document):
		"""
		Perform the document transformation.
		"""

class IRenderedBookTransformer(interface.Interface):
	"""
	Given a :class:`IRenderedBook`, mutate its on-disk state
	to achieve some specified end. This *should* be idempotent.
	"""

	def transform(book):
		"""
		Perform the book transformation.

		:param book: The :class:`IRenderedBook`.
		"""

class IRenderedBookValidator(interface.Interface):
	"""
	Given a rendered book, check that its in-memory and on
	disk state meets some criteria. At this time, this interface
	does not define what happens if that is not true.
	"""

	def check(book):
		"""
		Check the book's adherence to the rule of this interface.

        :return: Undefined.
		"""

class IRenderedBookArchiver(interface.Interface):
	"""
	Given a :class:`IRenderedBook`, it creates an offline archive.
	"""

	def archive(book, out_dir=None, verbose=False):
		"""
		Perform the book archiving.

		:param book: The :class:`IRenderedBook`.
		:param out_dir: The output directory
		:param verbose: Verbose mode
		"""

class IStaticRelatedItemsAdder(IRenderedBookTransformer):
	"""
	Transforms the book's TOC by adding related items mined from
	the book.
	"""

class IVideoAdder(IRenderedBookTransformer):
	"""
	Transforms the contents of the book by adding videos.
	"""

class IStaticVideoAdder(IVideoAdder):
	"""
	Adds videos using static information.
	"""

class IStaticYouTubeEmbedVideoAdder(IStaticVideoAdder):
	"""
	Uses static information to add embedded YouTube video references to the book content.
	"""

####
# Embedded subcontainers
####
from zope.mimetype.interfaces import IContentTypeAware
class IEmbeddedContainer(IContentTypeAware):
	"""
	Intended to be implemented (or adapted from) nodes in the plasTeX
	DOM tree, this object represents a portion of content, embedded
	in other content, that should function as its own user-generated
	data container. Typically these will be rendered in HTML with ``<object>``
	tags, and the attributes declared in this interface will be
	echoed in the rendered version.

	We inherit a ``mimeType`` attribute from our parent interface; this
	should be the ``mimeType`` of the container being pointed to.
	"""

	ntiid = schema.TextLine(title="The NTIID of the embedded container itself.")

####
# Indexing
####

class IRenderedBookIndexer(IRenderedBookTransformer):

	def transform(book, name):
		"""
		Perform the book index operation.

		:param book: The :class:`IRenderedBook`.
		:param name: indexer name
		"""
		
class IContentIndexer(interface.Interface):
	"""
	Creates an index using the contents in a given book
	"""

	def index(book, indexdir=None):
		"""
		The book to index

		:param book: The :class:`IRenderedBook`.
		:param indexdir: Output directory
		"""

class IBookIndexer(IContentIndexer):
	"""
	Creates an index of the content inside a given book
	"""

class IVideoTranscriptIndexer(IContentIndexer):
	"""
	Creates an index for the video transcripts associated with a given book
	"""

class INTICardIndexer(IContentIndexer):
	"""
	Creates an index for the nti cards associated with a given book
	"""

####
# Extractors
####

class IRenderedBookExtractor(IRenderedBookTransformer):
	pass
		

from zope.interface import registry
from zope.component import getGlobalSiteManager

class JobComponents(registry.Components):
	"""
	A component registry (IComponentLookup) that automatically attempts to
	find things using the current job name first when no name is given.

	TODO: In the future, this might also consider the provider.

	"""

	def __init__(self, jobname=None, **kwargs):
		self._jobname = jobname
		assert self._jobname
		super(JobComponents, self).__init__(**kwargs)
		if not self.__bases__:
			self.__bases__ = (getGlobalSiteManager(),)

	# TODO: Could probably do some meta programming and avoid duplicating the similar patterns
	def queryUtility(self, provided, name='', default=None):
		result = default
		if name == '':
			result = super(JobComponents, self).queryUtility(provided, self._jobname, default=default)
			if result is not default:
				return result

		return super(JobComponents, self).queryUtility(provided, name=name, default=default)

	def queryAdapter(self, obj, interface, name='', default=None):
		result = default
		if name == '':
			result = super(JobComponents, self).queryAdapter(obj, interface, name=self._jobname, default=default)
			if result is not default:
				return result
		return super(JobComponents, self).queryAdapter(obj, interface, name=name, default=default)

	def queryMultiAdapter(self, objects, interface, name='', default=None):
		result = default
		if name == '':
			result = super(JobComponents, self).queryMultiAdapter(objects, interface, name=self._jobname, default=default)
			if result is not default:
				return result
		return super(JobComponents, self).queryMultiAdapter(objects, interface, name=name, default=default)
