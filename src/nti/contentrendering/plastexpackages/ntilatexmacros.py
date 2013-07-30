#!/usr/bin/env python
# -*- coding: utf-8 -*-

# All of these have too many public methods
#pylint: disable=R0904
# "Method __delitem__ is abstract in Node and not overridden"
#pylint: disable=W0223

from __future__ import print_function, unicode_literals, absolute_import

import hashlib
import os
import simplejson

from zope import component
from zope import interface

from plasTeX import Base, Command, Environment

from plasTeX.Base import Crossref
from plasTeX.Base import TextCommand
from plasTeX.Renderers import render_children

from nti.contentrendering import plastexids
from nti.contentrendering import interfaces as crd_interfaces
from nti.contentrendering.jsonpbuilder import _JSONPWrapper
from nti.contentrendering.plastexpackages import interfaces
from nti.contentrendering.plastexpackages._util import LocalContentMixin
from nti.contentrendering.plastexpackages.graphicx import includegraphics
from nti.contentrendering.resources import interfaces as resource_interfaces
from nti.ntiids import ntiids

from nti.contentfragments import interfaces as cfg_interfaces

from zope.cachedescriptors.property import readproperty

logger = __import__('logging').getLogger(__name__)

# Monkey patching time
# SAJ: The following are set to render properly nested HTML.
Base.figure.forcePars = False
Base.minipage.blockType = True
Base.parbox.blockType = True
Base.centerline.blockType = True
Base.hrule.blockType = True

class _OneText(Base.Command):
	args = 'text:str'

	def invoke( self, tex ):
		return super(_OneText, self).invoke( tex )

class _Ignored(Base.Command):
	unicode = ''
	def invoke( self, tex ):
		return []

# SAJ: Sectioning commands for custom rendering treatment
class chaptertitlesuppressed( Base.chapter ):
	pass

class sectiontitlesuppressed( Base.section ):
	pass

#TODO do pagerefs even make sense in our dom?
#Try to find an intelligent page name for the reference
#so we don't have to render the link text as '3'
class pageref(Crossref.pageref):

	#we would hope to generate the pagename attribute in
	#the invoke method but since it is dependent on the page
	#splits used at render time we define a function to be called
	#from the page template
	def getPageNameForRef(self):
		#Look up the dom tree until we find something
		#that would create a file
		fileNode = self.idref['label']
		while not getattr(fileNode, 'title', None) and getattr(fileNode, 'parentNode', None):
			fileNode = fileNode.parentNode

		if hasattr(fileNode, 'title'):
			return getattr(fileNode.title, 'textContent', fileNode.title)

		return None


class ntinavlist(Base.List):
	pass

###############################################################################
# The following block of commands concern general resource handling
###############################################################################

@interface.implementer(resource_interfaces.IRepresentableContentUnit,
		       resource_interfaces.IRepresentationPreferences)
class DeclareMediaResource( Base.Command ):
	"""This command is extremely experimental and should be avoided for now."""
	args = 'src:str label:id'
	resourceTypes = ( 'jsonp', )

	def invoke( self, tex ):
		result = super(DeclareMediaResource, self).invoke( tex )
		self.attributes['src'] = os.path.join( self.ownerDocument.userdata.getPath('working-dir'), self.attributes['src'])
		return result

###############################################################################
# The following block of commands concern media resource handling
###############################################################################

@interface.implementer(resource_interfaces.IRepresentableContentUnit,
		       resource_interfaces.IRepresentationPreferences)
class mediatranscript(Base.Command):
	args = 'src:str type:str lang:str purpose:str'
	resourceTypes = ( 'jsonp', )
	blockType = True

	transcript_mime_type = 'text/plain'

	def invoke( self, tex ):
		result = super(mediatranscript, self).invoke( tex )
		self.attributes['src'] = os.path.join( self.ownerDocument.userdata.getPath('working-dir'), self.attributes['src'])
		return result

	def digest(self, tokens):
		res = super(mediatranscript, self).digest(tokens)

		if self.attributes['type'] == 'webvtt':
			self.transcript_mime_type = 'text/vtt'

		return res

class ntiincludevideo(_OneText):
	args = 'video_url'

	def invoke( self, tex ):
		result = super(ntiincludevideo, self).invoke( tex )

		# Set the id of the element
		source = self.source
		_id = hashlib.md5(source.strip().encode('utf-8')).hexdigest()
		setattr( self, "@id", _id )
		setattr( self, "@hasgenid", True )

		# change youtube view links to embed
		self.attributes['video_url'] = self.attributes['video_url'].textContent.replace( "/watch?v=", '/embed/' )
		self.attributes['width'] = 640
		self.attributes['height'] = 360
		_t = self.attributes['video_url'].split('/')
		if 'youtube' in _t[2]:
			self.attributes['service'] = 'youtube'
			self.attributes['video_id'] = _t[len(_t)-1].split('?')[0]
			self.attributes['poster'] = '//img.youtube.com/vi/' + self.attributes['video_id'] + '/0.jpg'
			self.attributes['thumbnail'] = '//img.youtube.com/vi/' + self.attributes['video_id'] + '/1.jpg'
		return result

class ntivideoname(Command):
	unicode = ''

class ntivideo(LocalContentMixin, Base.Float, plastexids.NTIIDMixin):
	args = '[ options:dict ]'
	counter = 'ntivideo'
	blockType = True
	_ntiid_cache_map_name = '_ntivideo_ntiid_map'
	_ntiid_allow_missing_title = False
	_ntiid_suffix = 'ntivideo.'
	_ntiid_title_attr_name = 'ref'
	_ntiid_type = 'NTIVideo'

	mimeType = "application/vnd.nextthought.ntivideo"
	itemprop = "presentation-video"

	creator = None
	title = 'No Title'
	subtitle = None
	closed_caption = None
	num_sources = 0

	# A Float subclass to get \caption handling
	class caption(Base.Floats.Caption):
		counter = 'figure'

	class ntivideosource( Command ):
		args = '[ options:dict ] service:str id:str'
		blockType = True

		poster = None
		thumbnail = None
		width = 640
		height = 480
		priority = 0

		def digest(self, tokens):
			"""Handle creating the necessary datastructures for each video type."""
			super(ntivideo.ntivideosource, self).digest(tokens)

			options = self.attributes['options'] or {}

			self.priority = self.parentNode.num_sources
			self.parentNode.num_sources += 1

			self.src = {}
			if self.attributes['service']:
				if self.attributes['service'] == 'youtube':
					self.service = 'youtube'
					self.src['other'] = self.attributes['id']
					self.width = 640
					self.height = 360
					self.poster = '//img.youtube.com/vi/' + self.attributes['id'] + '/0.jpg'
					self.thumbnail = '//img.youtube.com/vi/' + self.attributes['id'] + '/1.jpg'
				elif self.attributes['service'] == 'html5':
					self.service = 'html5'
					self.src['mp4'] = self.attributes['id'] + '.mp4'
					self.src['webm'] = self.attributes['id'] + '.webm'
					self.poster = self.attributes['id'] + '-poster.jpg'
					self.thumbnail = self.attributes['id'] + '-thumb.jpg'
				else:
					logger.warning('Unknown video type: %s', self.attributes['type'])

	def digest(self, tokens):
		res = super(ntivideo, self).digest(tokens)
		if self.macroMode == self.MODE_BEGIN:
			options = self.attributes.get( 'options', {} ) or {}
			__traceback_info__ = options, self.attributes

			if 'show-card' in options:
				self.itemprop = 'presentation-card'

			if not getattr(self, 'title', ''):
				raise ValueError("Must specify a title using \\caption")

			if 'creator' in options:
				self.creator = options['creator']
		return res

	@readproperty
	def description(self):
		texts = []
		for child in self.allChildNodes:
			# Try to extract the text children, ignoring the caption and label, etc
			if child.nodeType == self.TEXT_NODE and (child.parentNode == self or child.parentNode.nodeName == 'par'):
				texts.append( unicode( child ) )

		return cfg_interfaces.IPlainTextContentFragment( cfg_interfaces.ILatexContentFragment( ''.join( texts ).strip() ) )

	@readproperty
	def video_sources(self):
		sources = self.getElementsByTagName( 'ntivideosource' )
		output = render_children( self.renderer, sources )
		return cfg_interfaces.HTMLContentFragment( ''.join( output ).strip() )


	@readproperty
	def transcripts(self):
		sources = self.getElementsByTagName( 'mediatranscript' )
		output = render_children( self.renderer, sources )
		return cfg_interfaces.HTMLContentFragment( ''.join( output ).strip() )

class ntivideoref(Base.Crossref.ref):
	pass

class ntilocalvideoname(Command):
		unicode = ''

class ntilocalvideo( Base.Environment ):
	args = '[ options:dict ]'
	counter = "ntilocalvideo"
	blockType=True

	def invoke(self, tex):
		_t = super(ntilocalvideo, self).invoke(tex)
		if 'options' not in self.attributes or not self.attributes['options']:
			self.attributes['options'] = {}
		return _t

	def digest(self, tex):
		super(ntilocalvideo, self).digest(tex)
		video = self.getElementsByTagName( 'ntiincludelocalvideo' )[0]
		self.src = {}
		self.src['mp4'] = video.attributes['src'] + u'.mp4'
		self.src['webm'] = video.attributes['src'] + u'.webm'
		self.title = video.attributes['title']
		self.poster = video.attributes['poster']
		if 'width' in video.attributes['options']:
			self.width = video.attributes['options']['width']
		if 'height' in video.attributes['options']:
			self.height = video.attributes['options']['height']
		self.id = video.id

	class ntiincludelocalvideo( Base.Command ):
		args = '[ options:dict ] src title poster'


class ntiincludeannotationgraphics(includegraphics):
	pass

class ntiincludenoannotationgraphics(includegraphics):
	pass

class ntipagenum(_OneText):
	pass

class ntiglossaryterm(Base.Command):
	args = 'term self'

class ntiimagehref(Base.Command):
	args = 'img url'

class textsuperscript(Base.Command):
	args = 'self'

class textsubscript(Base.Command):
	args = 'self'

# Custom text treatments
class modified(TextCommand):
	pass

# The sidebar environment is to be the base class for other side types such as those from AoPS.
class sidebar(Environment):
	args = 'title'
	blockType = True

# The following 'text' symbols are 'Predefined' LaTeX 2e commands

class textcopyright(Base.Command):
	unicode = u'\u00A9'

class textgreater(Base.Command):
	unicode = u'\u003E'

class textless(Base.Command):
	unicode = u'\u003C'

class textregistered(Base.Command):
	unicode = u'\u00AE'

class texttrademark(Base.Command):
	unicode = u'\u2122'

# The following 'text' symbols are from the textcomp package.

class textapprox(Base.Command):
	unicode = u'\u2248'

class textdegree(Base.Command):
	unicode = u'\u00B0'

class textdiv(Base.Command):
	unicode = u'\u00F7'

class textminus(Base.Command):
	unicode = u'\u2212'

class textpm(Base.Command):
	unicode = u'\u00B1'

class textrightarrow(Base.Command):
	unicode = u'\u2192'

class textsmiley(Base.Command):
	unicode = u'\u263A'

class texttimes(Base.Command):
	unicode = u'\u00D7'

# The following 'text' commands are custom and specific to NTI
class textangle(Base.Command):
	unicode = u'\u2220'

class textcong(Base.Command):
	unicode = u'\u2245'

class textge(Base.Command):
	unicode = u'\u2265'

class textle(Base.Command):
	unicode = u'\u2264'

class textneq(Base.Command):
	unicode = u'\u2260'

class textparallel(Base.Command):
	unicode = u'\u2016'

class textsurd(Base.Command):
	unicode = u'\u221A'

class textperp(Base.Command):
	unicode = u'\u22A5'

class textinfty(Base.Command):
	unicode = u'\u221E'

class textprime(Base.Command):
	unicode = u'\u2032'

class textsim(Base.Command):
	unicode = u'\u007E'

class textsquare(Base.Command):
	unicode = u'\u25A1'

class texttriangle(Base.Command):
	unicode = u'\u25B3'

class textdoublehyphen(Command):
	unicode = u'\u002D' + u'\u002D'

# Currency symbols
class yen(Base.Command):
	unicode = u'\xA5'

class eur(Base.Command):
	macroName = 'EUR'
	unicode = u'\u20AC'

class euro(Base.Command):
	unicode = u'\u20AC'

class textcent(Base.Command):
	unicode = u'\xA2'

# Handle pdfLatex primatives
class pdfminorversion(Command):
	args = 'version:int'

# Handle latex commands that make no sense in a web layout
class flushbottom(Command):
	args = ''

class nobreak(Base.Command):
	args = 'self'

class vfrac(Base.Command):
	args = 'nom denom'

# Videos
class ntivideorollname(Base.Command):
	pass

class ntivideoroll(Base.Environment,plastexids.NTIIDMixin):
	counter = "ntivideoroll"
	blockType = True
	_ntiid_cache_map_name = '_ntivideoroll_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'ntivideoroll.'
	_ntiid_title_attr_name = 'ref'
	_ntiid_type = 'NTIVR'

# Image collections
class ntiimagecollectionname(Base.Command):
	pass

class ntiimagecollection(Base.Environment,plastexids.NTIIDMixin):
	counter = "ntiimagecollection"
	blockType = True
	_ntiid_cache_map_name = '_ntiimagecollection_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'ntiimagecollection.'
	_ntiid_title_attr_name = 'ref'
	_ntiid_type = 'NTIIC'

class ntipreviouspage(Base.Command):
	pass

# Cards
class nticardname(Base.Command):
	pass

@interface.implementer(crd_interfaces.IEmbeddedContainer)
class nticard(LocalContentMixin,Base.Float,plastexids.NTIIDMixin):
	"""
	Implementation of the Card environment. There should be an ``includegraphics`` specifying
	a thumbnail as a child of this node (unless ``auto`` is used). The text contents of this node will form
	the card description.

	.. note::
		This environment is **NOT** intended for subclassing.

	Possible options include:

	creator
		The creator of the content

	auto
		If present and "true", then we will attempt to spider the ``href``
		to extract Twitter card or `Facebook OpenGraph <http://opengraphprotocol.org>`_ data from it; this allows
		you to skip specifying an image and description.
	"""
	args = 'href:str <options:dict>'
	# Note the options dict is in <>, and uses the default comma separator, which means
	# values cannot have commas (that's why href, which may be an NTIID is its own argument).
	# See also ntiassessment.naqsolution.

	# A Float subclass to get \caption handling
	class caption(Base.Floats.Caption):
		counter = 'figure'

	# Only classes with counters can be labeled, and \label sets the
	# id property, which in turn is used as part of the NTIID (when no NTIID is set explicitly)
	counter = 'nticard'
	blockType = True
	_ntiid_cache_map_name = '_nticard_ntiid_map'
	_ntiid_allow_missing_title = False
	_ntiid_suffix = 'nticard.'
	_ntiid_title_attr_name = 'ref' # Use our counter to generate IDs if no ID is given
	_ntiid_type = 'NTICard'

	#: From IEmbeddedContainer
	mimeType = "application/vnd.nextthought.nticard"

	creator = None
	href = None
	type = 'summary'
	image = None
	#: Derived from the href property. If the href itself specifies
	#: a complete NTIID, then it will have that value. Otherwise,
	#: one will be computed from the href; if the href is a absolute
	#: URL, then the computed NTIID will be the same whereever the URL
	#: is linked to, allowing this NTIID to be used as a ``containerId``
	target_ntiid = None

	_href_override = None


	def _pdf_to_thumbnail(self, pdf_path, page=1, height=792, width=612):
		from nti.contentrendering.contentthumbnails import _create_thumbnail_of_pdf
		return _create_thumbnail_of_pdf( pdf_path, page=page, height=height, width=width )


	def _auto_populate(self):
		from nti.contentprocessing.metadata_extractors import get_metadata_from_content_location
		metadata = get_metadata_from_content_location( self._href_override or self.href )
		if metadata is not None:
			self.title = metadata.title or self.title
			self.description = metadata.description or self.description
			self.href = metadata.contentLocation or self.href
			self.creator = metadata.creator or self.creator

			# Just enough to go with our template
			class Image(object):
				def __init__( self, image ):
					self.image = image
			class Dimen(object):
				def __init__(self,px):
					self.px = px

			if metadata.mimeType == 'application/pdf':
				# Generate and use the real thing
				thumb_file = self._pdf_to_thumbnail( metadata.sourcePath )
				include = includegraphics()
				include.attributes['file'] = thumb_file
				include.argSource = r'[width=93pt,height=120pt]{%s}' % thumb_file
				include.style['width'] = "93px"
				include.style['height'] = "120px"
				self.appendChild( include )
			elif metadata.images and (metadata.images[0].width and metadata.images[0].height):
				# Yay, got the real size already
				self.image = Image( metadata.images[0] )
			elif metadata.images:
				# Download and save the image?
				# Right now we are downloading it for size purposes (which may not be
				# needed) but we could choose to cache it locally
				import requests
				from plone.namedfile import NamedImage
				import urlparse
				val = metadata.images[0].url
				response = requests.get( val )
				filename = urlparse.urlparse( val ).path.split('/')[-1]
				named_image = NamedImage( data=response.content, filename=filename )
				width, height = named_image.getImageSize()

				self.image = Image(named_image)
				self.image.image.url = val
				self.image.image.height = Dimen(height)
				self.image.image.width = Dimen(width)


	def invoke( self, tex ):
		res = super(nticard,self).invoke( tex )
		# Resolve local files to full paths with the same algorithm that
		# includegraphics uses
		if ('href' in self.attributes
			and '//' not in self.attributes['href'] # not a HTTP[S] url
			and not self.attributes['href'].startswith('tag:') ): # not an NTIID
			from nti.contentrendering.plastexpackages.graphics import _locate_image_file

			the_file = _locate_image_file( self, tex, self.attributes['href'],
										   includegraphics.packageName,
										   [], # No extensions to search: must be complete filename or path
										   query_extensions=False)
			if the_file:
				self._href_override = the_file
		return res

	def digest(self, tokens):
		res = super(nticard,self).digest(tokens)
		if self.macroMode == self.MODE_BEGIN:
			options = self.attributes.get( 'options', {} ) or {}
			__traceback_info__ = options, self.attributes
			if 'href' not in self.attributes or not self.attributes['href']:
				raise ValueError( "Must provide href argument" )
			self.href = self.attributes['href']

			if 'auto' in options and options['auto'].lower() == 'true':
				self._auto_populate()

			if not getattr(self, 'title', ''):
				raise ValueError("Must specify a title using \\caption")


			if 'creator' in options:
				self.creator = options['creator']

			images = self.getElementsByTagName( 'includegraphics' )
			if images:
				# Must leave the image in the dom so it can be found by the resourceDB
				#images[0].parentNode.removeChild( images[0] )
				self.image = images[0]

			from nti.ntiids.ntiids import is_valid_ntiid_string

			if is_valid_ntiid_string( self.href ):
				self.target_ntiid = self.href
			else:
				from nti.ntiids.ntiids import make_ntiid, TYPE_UUID
				from hashlib import md5
				# TODO: Hmm, what to use as the provider? Look for a hostname in the
				# URL?
				self.target_ntiid = make_ntiid( provider='NTI',
												nttype=TYPE_UUID,
												specific=md5(self.href).hexdigest() )
		return res


	@readproperty
	def description(self):
		texts = []
		for child in self.allChildNodes:
			# Try to extract the text children, ignoring the caption and label, etc
			if child.nodeType == self.TEXT_NODE and (child.parentNode == self or child.parentNode.nodeName == 'par'):
				texts.append( unicode( child ) )

		return cfg_interfaces.IPlainTextContentFragment( cfg_interfaces.ILatexContentFragment( ''.join( texts ).strip() ) )

###############################################################################
# The following block of commands concern representing related readings
###############################################################################

class relatedworkname(Base.Command):
	pass

class relatedwork(LocalContentMixin, Base.Environment, plastexids.NTIIDMixin):
	args = '[ options:dict ]'

	# Only classes with counters can be labeled, and \label sets the
	# id property, which in turn is used as part of the NTIID (when no NTIID is set explicitly)
	counter = 'relatedwork'
	blockType = True
	_ntiid_cache_map_name = '_relatedwork_ntiid_map'
	_ntiid_allow_missing_title = False
	_ntiid_suffix = 'relatedwork.'
	_ntiid_title_attr_name = 'ref' # Use our counter to generate IDs if no ID is given
	_ntiid_type = 'RelatedWork'

	#: From IEmbeddedContainer
	mimeType = "application/vnd.nextthought.relatedwork"
	targetMimeType = "application/vnd.nextthought.content"
	icon = None
	iconResource = None

	class worktitle(Base.Command):
		args = 'title:str'

		def digest(self, tokens):
			tok = super(relatedwork.worktitle,self).digest(tokens)
			self.parentNode.title = self.attributes['title']
			return tok

	class workcreator(Base.Command):
		args = 'creator:str'

		def digest(self, tokens):
			tok = super(relatedwork.workcreator,self).digest(tokens)
			self.parentNode.creator = self.attributes['creator']
			return tok

	class worksource(Base.Command):
		args = 'uri:str'

		def digest(self, tokens):
			tok = super(relatedwork.worksource,self).digest(tokens)
			self.parentNode.uri = self.attributes['uri']
			return tok

	def digest(self, tokens):
		tok = super(relatedwork,self).digest(tokens)

		if ntiids.is_valid_ntiid_string( self.uri ):
			self.targetMimeType = 'application/vnd.nextthought.content'
			ntiid_specific = ntiids.get_specific( self.uri )
			self.icon = '/'.join([u'..', ntiid_specific.split('.')[0], 'icons', 'chapters', 'generic_book.png'])
		else:
			self.targetMimeType = 'application/vnd.nextthought.externallink'

		icons = self.getElementsByTagName('includegraphics')
		if icons:
			self.iconResource = icons[0]
		return tok

	@readproperty
	def description(self):
		texts = []
		for child in self.allChildNodes:
			# Try to extract the text children, ignoring the caption and label, etc
			if child.nodeType == self.TEXT_NODE and (child.parentNode == self or child.parentNode.nodeName == 'par'):
				texts.append( unicode( child ) )

		return cfg_interfaces.IPlainTextContentFragment( cfg_interfaces.ILatexContentFragment( ''.join( texts ).strip() ) )

class relatedworkref(Base.Crossref.ref):
	args = '[ options:dict ] label:idref uri:str desc:str'

	def digest(self, tokens):
		tok = super(relatedworkref, self).digest(tokens)

		options = self.attributes.get( 'options', {} ) or {}
		if 'category' in options:
			self.category = options['category']
		else:
			self.category = 'required'

		# SAJ: If the value is not one of the two we support force it to one.
		if self.category != 'related' and self.category != 'additional':
			self.category = 'required'

		self.uri = self.attributes['uri']
		self.description = self.attributes['desc']
		self.relatedwork = self.idref['label']
		return tok

###############################################################################
# The following block of commands concern representing forum discussions.
###############################################################################

class ntidiscussionname(Base.Command):
	pass

class ntidiscussionref(Base.Crossref.ref):
	pass

class ntidiscussion(Base.Environment):
	args = '[ options:dict ] '

	# Only classes with counters can be labeled, and \label sets the
	# id property, which in turn is used as part of the NTIID (when no NTIID is set explicitly)
	counter = 'ntidiscussion'
	blockType = True

	targetMimeType = "application/vnd.nextthought.discussion"
	iconResource = None
	title = ''
	subtitle = ''
	topic_ntiid = ''

	class discussiontitle(Base.Command):
		args = 'title:str'

		def digest(self, tokens):
			tok = super(ntidiscussion.discussiontitle,self).digest(tokens)
			self.parentNode.title = self.attributes['title']
			return tok

	class discussionsubtitle(Base.Command):
		args = 'subtitle:str'

		def digest(self, tokens):
			tok = super(ntidiscussion.discussionsubtitle,self).digest(tokens)
			self.parentNode.subtitle = self.attributes['subtitle']
			return tok

	class topicntiid(Base.Command):
		args = 'ntiid:str'

		def digest(self, tokens):
			tok = super(ntidiscussion.topicntiid,self).digest(tokens)
			self.parentNode.topic_ntiid = self.attributes['ntiid']
			return tok

	def digest(self, tokens):
		tok = super(ntidiscussion,self).digest(tokens)

		icons = self.getElementsByTagName('includegraphics')
		if icons:
			self.iconResource = icons[0]
		return tok

def ProcessOptions( options, document ):
	document.context.newcounter( 'ntilocalvideo' )
	document.context.newcounter( 'ntivideo' )
	document.context.newcounter( 'ntivideoroll' )
	document.context.newcounter( 'ntiimagecollection' )
	document.context.newcounter( 'nticard' )
	document.context.newcounter( 'relatedwork' )
	document.context.newcounter( 'ntidiscussion' )

@interface.implementer(interfaces.IRelatedWorkExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _RelatedWorkExtractor(object):

	def __init__( self, book=None ):
		# Usable as either a utility factory or an adapter
		pass

	def transform( self, book ):
		lesson_els = book.document.getElementsByTagName( 'courselesson' )
		related_els = book.document.getElementsByTagName( 'relatedwork' )
		dom = book.toc.dom
		if lesson_els or related_els:
			self._process_lessons(dom, lesson_els)
			self._process_related(dom, related_els)
			dom.childNodes[0].setAttribute('xmlns:content', "http://www.nextthought.com/toc")
			book.toc.save()

	def _process_lessons(self, dom, els):
		for el in els:
			ref_els = el.getElementsByTagName('relatedworkref')
			if ref_els:
				lesson_el = None

				# Determine which topic represents the lesson
				topic_els = dom.getElementsByTagName('topic')
				for topic_el in topic_els:
					if topic_el.getAttribute('ntiid') == el.ntiid:
						lesson_el = topic_el

				for ref_el in ref_els:
					if ref_el.relatedwork.iconResource is not None:
						icon = ref_el.relatedwork.iconResource.image.url
					elif ref_el.relatedwork.icon is not None:
						icon = ref_el.relatedwork.icon
					else:
						icon = ''

					toc_el = dom.createElement('content:related')
					toc_el.setAttribute('label', ref_el.relatedwork.title)
					toc_el.setAttribute('creator', ref_el.relatedwork.creator)
					toc_el.setAttribute('href', ref_el.uri)
					toc_el.setAttribute('type', ref_el.relatedwork.targetMimeType)
					toc_el.setAttribute('icon', icon)
					toc_el.setAttribute('desc', ref_el.description)
					toc_el.setAttribute('section', ref_el.category)
					lesson_el.appendChild(toc_el)
					lesson_el.appendChild(dom.createTextNode(u'\n'))

	def _process_related(self, dom, els):
		for el in els:
			if el.iconResource is not None:
				icon = el.iconResource.image.url
			elif el.icon is not None:
				icon = el.icon
			else:
				icon = ''

			toc_el = dom.createElement('content:related')
			toc_el.setAttribute('label', el.title)
			toc_el.setAttribute('creator', el.creator)
			toc_el.setAttribute('href', el.uri)
			toc_el.setAttribute('type', el.targetMimeType)
			toc_el.setAttribute('icon', icon)
			toc_el.setAttribute('desc', el.description)
			dom.childNodes[0].appendChild(toc_el)
			dom.childNodes[0].appendChild(dom.createTextNode(u'\n'))

@interface.implementer(interfaces.IDiscussionExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _DiscussionExtractor(object):

	def __init__( self, book=None ):
		# Usable as either a utility factory or an adapter
		pass

	def transform( self, book ):
		lesson_els = book.document.getElementsByTagName( 'courselesson' )
		dom = book.toc.dom
		if lesson_els:
			self._process_lessons(dom, lesson_els)
			book.toc.save()

	def _process_lessons(self, dom, els):
		for el in els:
			discussion_els = el.getElementsByTagName('ntidiscussion')
			discussionref_els = el.getElementsByTagName('ntidiscussionref')
			if discussion_els or discussionref_els:
				lesson_el = None

				# Determine which topic represents the lesson
				topic_els = dom.getElementsByTagName('topic')
				for topic_el in topic_els:
					if topic_el.getAttribute('ntiid') == el.ntiid:
						lesson_el = topic_el

				for discussion_el in discussion_els:
					lesson_el = None

					# Determine which topic represents the lesson
					topic_els = dom.getElementsByTagName('topic')
					for topic_el in topic_els:
						if topic_el.getAttribute('ntiid') == el.ntiid:
							lesson_el = topic_el

					if discussion_el.iconResource is not None:
						icon = discussion_el.iconResource.image.url
					else:
						icon = ''

					toc_el = dom.createElement('object')
					toc_el.setAttribute('label', discussion_el.title)
					toc_el.setAttribute('title', discussion_el.subtitle)
					toc_el.setAttribute('ntiid', discussion_el.topic_ntiid)
					toc_el.setAttribute('mimeType', discussion_el.targetMimeType)
					toc_el.setAttribute('icon', icon)
					lesson_el.appendChild(toc_el)
					lesson_el.appendChild(dom.createTextNode(u'\n'))

				for discussionref_el in discussionref_els:
					lesson_el = None

					# Determine which topic represents the lesson
					topic_els = dom.getElementsByTagName('topic')
					for topic_el in topic_els:
						if topic_el.getAttribute('ntiid') == el.ntiid:
							lesson_el = topic_el

					if discussionref_el.idref['label'].iconResource is not None:
						icon = discussionref_el.idref['label'].iconResource.image.url
					else:
						icon = ''

					toc_el = dom.createElement('object')
					toc_el.setAttribute('label', discussionref_el.idref['label'].title)
					toc_el.setAttribute('title', discussionref_el.idref['label'].subtitle)
					toc_el.setAttribute('ntiid', discussionref_el.idref['label'].topic_ntiid)
					toc_el.setAttribute('mimeType', discussionref_el.idref['label'].targetMimeType)
					toc_el.setAttribute('icon', icon)
					lesson_el.appendChild(toc_el)
					lesson_el.appendChild(dom.createTextNode(u'\n'))

@interface.implementer(interfaces.INTIVideoExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _NTIVideoExtractor(object):

	def __init__( self, book=None ):
		# Usable as either a utility factory or an adapter
		pass

	def transform( self, book ):
		lesson_els = book.document.getElementsByTagName( 'courselesson' )
		video_els = book.document.getElementsByTagName( 'ntivideo' )
		outpath = os.path.expanduser(book.contentLocation)
		dom = book.toc.dom
		if lesson_els or video_els:
			self._process_lessons(dom, lesson_els)
			self._process_videos(dom, video_els, outpath)
			book.toc.save()

	def _process_lessons(self, dom, els):
		for el in els:
			video_els = el.getElementsByTagName('ntivideoref')
			if video_els:
				lesson_el = None

				# Determine which topic represents the lesson
				topic_els = dom.getElementsByTagName('topic')
				for topic_el in topic_els:
					if topic_el.getAttribute('ntiid') == el.ntiid:
						lesson_el = topic_el

				for video_el in video_els:
					lesson_el = None

					# Determine which topic represents the lesson
					topic_els = dom.getElementsByTagName('topic')
					for topic_el in topic_els:
						if topic_el.getAttribute('ntiid') == el.ntiid:
							lesson_el = topic_el

					poster = ''
					source_els = video_el.idref['label'].getElementsByTagName('ntivideosource')
					if source_els:
						poster = source_els[0].poster

					toc_el = dom.createElement('object')
					if hasattr(video_el.idref['label'].title, 'textContent'):
						toc_el.setAttribute('label', video_el.idref['label'].title.textContent)
					else:
						toc_el.setAttribute('label', video_el.idref['label'].title)
					toc_el.setAttribute('poster', poster)
					toc_el.setAttribute('ntiid', video_el.idref['label'].ntiid)
					toc_el.setAttribute('mimeType', video_el.idref['label'].mimeType)
					lesson_el.appendChild(toc_el)
					lesson_el.appendChild(dom.createTextNode(u'\n'))

	def _process_videos(self, dom, els, outpath):
		video_index = {}
		filename = 'video_index.json'
		for el in els:
			video = self._process_video(el)
			video_index[video['ntiid']] = video

		# Write the normal version
		with open(os.path.join(outpath, filename), "wb") as fp:
			simplejson.dump(video_index, fp, indent=2)

		# Write the JSONP version
		with open(os.path.join(outpath, filename+'p'), "wb") as fp:
			fp.write('jsonpReceiveContent(')
			simplejson.dump({'ntiid': dom.childNodes[0].getAttribute('ntiid'), 'Content-Type': 'application/json', 'Content-Encoding': 'json', 'content': video_index, 'version': '1'}, fp)
			fp.write(');')

		toc_el = dom.createElement('reference')
		toc_el.setAttribute('href', filename)
		toc_el.setAttribute('type', 'application/vnd.nextthought.videoindex')

		dom.childNodes[0].appendChild(toc_el)
		dom.childNodes[0].appendChild(dom.createTextNode(u'\n'))

	def _process_video(self, video):
		entry = {}
		entry['ntiid'] = video.ntiid
		entry['creator'] = video.creator
		if hasattr(video.title, 'textContent'):
			entry['title'] = video.title.textContent
		else:
			entry['title'] = video.title
		entry['description'] = video.description
		entry['mimeType'] = video.mimeType
		entry['closedCaptions'] = video.closed_caption
		entry['sources'] = []
		entry['transcripts'] = []

		for source in video.getElementsByTagName('ntivideosource'):
			val = {}
			val['poster'] = source.poster
			val['thumbnail'] = source.thumbnail
			val['height'] = source.height
			val['width'] = source.width
			val['service'] = source.service
			val['source'] = []
			val['type'] = []
			if source.service == 'html5':
				val['source'].append(source.src['mp4'])
				val['type'].append('video/mp4')
				val['source'].append(source.src['webm'])
				val['type'].append('video/webm')
			elif source.service == 'youtube':
				val['source'].append(source.src['other'])
				val['type'].append('video/youtube')
			entry['sources'].append(val)

		for transcript in video.getElementsByTagName('mediatranscript'):
			val = {}
			val['src'] = transcript.raw.url
			val['srcjsonp'] = transcript.wrapped.url
			val['type'] = transcript.transcript_mime_type
			val['lang'] = transcript.attributes['lang']
			val['purpose'] = transcript.attributes['purpose']
			entry['transcripts'].append(val)

		return entry

@interface.implementer(interfaces.IHackExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _HackExtractor(object):

	def __init__( self, book=None ):
		# Usable as either a utility factory or an adapter
		pass

	def transform( self, book ):
		if book.jobname == 'CLC3403_LawAndJustice':
			logger.warn('Applying SUPER hack!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			hack_el = book.toc.dom.createElement('object')
			hack_el.setAttribute('label', 'Quiz 1')
			hack_el.setAttribute('mimeType', 'application/vnd.nextthought.naquestionset')
			hack_el.setAttribute('gotoNtiid', 'tag:nextthought.com,2011-10:OU-HTML-CLC3403_LawAndJustice.sec:QUIZ_01.01')
			hack_el.setAttribute('ntiid', 'tag:nextthought.com,2011-10:NTI-NAQ-CLC3403_LawAndJustice.naquestionset.questionset1')
			hack_el.setAttribute('correct', '7')
			hack_el.setAttribute('incorrect', '2')

			lesson_els = book.document.getElementsByTagName( 'courselesson' )
			if lesson_els:
				topic_els = book.toc.dom.getElementsByTagName('topic')
				for topic_el in topic_els:
					if lesson_els[0].ntiid == topic_el.getAttribute('ntiid'):
						topic_el.appendChild(hack_el)
						topic_el.appendChild(book.toc.dom.createTextNode(u'\n'))
						book.toc.save()
					elif lesson_els[1].getAttribute('target-ntiid') == topic_el.getAttribute('ntiid'):
						topic_el.appendChild(hack_el)
						topic_el.appendChild(book.toc.dom.createTextNode(u'\n'))
						book.toc.save()

