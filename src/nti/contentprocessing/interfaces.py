# -*- coding: utf-8 -*-
"""
Content processing interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from nti.utils.schema import Number
from nti.utils.schema import Object
from nti.utils.schema import ListOrTuple

class IContentTranslationTable(interface.Interface):
	"""marker interface for content translationt table"""

class IContentTokenizer(interface.Interface):

	def tokenize(data):
		"""tokenize the specifeid text data"""

class INgramComputer(interface.Interface):
	minsize = schema.Int(title="Min ngram size.", required=True)
	maxsize = schema.Int(title="Max ngram size", required=False)

	def compute(text):
		"""compute the ngrams for the specified text"""

class IWordSimilarity(interface.Interface):

	def compute(a, b):
		"""compute a similarity ratio for the specified words"""

	def rank(word, terms, reverse=True):
		"""return the specified terms based on the distance to the specified word"""


class IWordTokenizerExpression(interface.Interface):
	"""marker interface for word tokenizer regular expression"""

class IWordTokenizerPattern(interface.Interface):
	"""marker interface for word tokenizer regular expression pattern"""

class IPunctuationCharExpression(interface.Interface):
	"""marker interface for punctuation regular expression"""

class IPunctuationCharExpressionPlus(interface.Interface):
	"""marker interface for punctuation + space regular expression"""

class IPunctuationCharPattern(interface.Interface):
	"""marker interface for punctuation regular expression pattern"""

class IPunctuationCharPatternPlus(interface.Interface):
	"""marker interface for punctuation + space regular expression pattern"""

class IAlchemyAPIKey(interface.Interface):
	alias = interface.Attribute("Key name or alias")
	value = interface.Attribute("The actual key value")


####
# Metadata extraction
####

from nti.contentfragments import schema as frg_schema
from zope.mimetype.interfaces import mimeTypeConstraint

class IImageMetadata(interface.Interface):
	"""
	Holds information about a particular image.
	"""

	url = schema.TextLine( title="The URL to resolve the image" )

	width = Number( title="The width in pixels of the image",
					required=False )
	height = Number( title="The height in pixels of the image",
					 required=False )

class IContentMetadata(interface.Interface):
	"""
	Metadata extracted from existing content.
	Each of the attributes is filled in based on the best
	possible extraction and each may be missing or empty.
	"""

	title = frg_schema.PlainTextLine(title="The title of the content",
									 required=False,
									 default='')
	description = frg_schema.PlainText(title="A short description of the content",
									   required=False,
									   default='' ) # TODO: Size limits?
	creator = frg_schema.PlainTextLine(title="A description of the creator",
									   description="Possibly one or more names or even an organization.",
									   required=False,
									   default='' )

	images = ListOrTuple( Object(IImageMetadata),
						  title="Any images associated with this content, typically thumbnails",
						  default=())

	mimeType = schema.TextLine(
		title="The Mime Type of the content",
		constraint=mimeTypeConstraint,
		required=False )

	contentLocation = schema.TextLine( title="The canonical URL of the content",
									   description=("After metadata extraction, we may have obtained"
													" a canonical URL for the content, different from"
													" the source location. For permanent storage and use"
													" this is the value to use, not the source location."),
										required=False )

	sourceLocation = schema.TextLine( title="The location of the source content",
									  description=("The unprocessed, original location of the content"
									  				" used to find the metadata. May be a local file"
													" path or a URL."),
									  required=False )
	sourcePath = schema.TextLine( title="A local file path to the content",
								  description=("If the content was a local file, or"
											   " had to be downloaded to a temporary file"
											   " that was preserved following metadata processing,"
											   " this will be the path to that file."),
								  required=False)

class IContentMetadataExtractorArgs(interface.Interface):
	"""
	Arguments for extracting content metadata.
	"""

	stream = interface.Attribute( "A file-like object for reading the content" )
	bidirectionalstream = interface.Attribute( "A file-like object for reading the content, supports seeking" )
	bytes = interface.Attribute("Raw bytes of the content.")
	text = interface.Attribute("Decoded text of the content.")

class IContentMetadataExtractor(interface.Interface):
	"""
	Intended to be registered as named utilities with the name of the mimetype
	they handle.
	"""

	def extract_metadata( args ):
		"""
		Called with an :class:`IContentMetadataExtractorArgs`.

		:return: An :class:`IContentMetadata`
		"""

class IContentMetadataURLHandler(interface.Interface):
	"""
	Intended to be registered as named utilities having the name of
	a URL scheme.
	"""

	def __call__( url ):
		"""
		Called with a string giving the URL.

		:return: An :class:`IContentMetadata`.
		"""
