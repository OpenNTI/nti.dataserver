#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Define NTI Latex Macros

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import hashlib

from zope import interface
from zope.cachedescriptors.property import readproperty

from plasTeX.Base import Crossref
from plasTeX.Base import TextCommand
from plasTeX.Renderers import render_children
from plasTeX import Base, Command, Environment
from plasTeX import TeXFragment

from nti.contentfragments import interfaces as cfg_interfaces

from nti.contentrendering import plastexids
from nti.contentrendering import interfaces as crd_interfaces
from nti.contentrendering.plastexpackages._util import LocalContentMixin
from nti.contentrendering.plastexpackages.graphicx import includegraphics
from nti.contentrendering.resources import interfaces as resource_interfaces

from nti.ntiids import ntiids

# Monkey patching time
# SAJ: The following are set to render properly nested HTML.
Base.hrule.blockType = True
Base.parbox.blockType = True
Base.figure.forcePars = False
Base.minipage.blockType = True
Base.centerline.blockType = True

# BWC
import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
	"Moved to nti.contentrendering.plastexpackages.eurosym",
	"nti.contentrendering.plastexpackages.eurosym",
	"eur",
	"euro")

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

# TODO: do pagerefs even make sense in our dom?
# Try to find an intelligent page name for the reference
# so we don't have to render the link text as '3'
class pageref(Crossref.pageref):
	# we would hope to generate the pagename attribute in
	# the invoke method but since it is dependent on the page
	# splits used at render time we define a function to be called
	# from the page template
	def getPageNameForRef(self):
		# Look up the dom tree until we find something
		# that would create a file
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
		self.attributes['src'] = os.path.join(
			self.ownerDocument.userdata.getPath('working-dir'), self.attributes['src'])
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
		self.attributes['src'] = os.path.join(
			self.ownerDocument.userdata.getPath('working-dir'), self.attributes['src'])
		return result

	def digest(self, tokens):
		res = super(mediatranscript, self).digest(tokens)

		if self.attributes['type'] == 'webvtt':
			self.transcript_mime_type = 'text/vtt'

		return res

class ntiincludevideo(_OneText):
	args = '[options:dict] video_url:url'

	def invoke( self, tex ):
		result = super(ntiincludevideo, self).invoke( tex )
		options = self.attributes.get('options', None) or {}

		# Set the id of the element
		source = self.source
		_id = hashlib.md5(source.strip().encode('utf-8')).hexdigest()
		setattr( self, "@id", _id )
		setattr( self, "@hasgenid", True )

		# change youtube view links to embed
		if hasattr(self.attributes['video_url'], 'source'):
			self.attributes['video_url'] = self.attributes['video_url'].source.replace(' ', '') \
										.replace('\\&', '&') \
										.replace('\\_', '_') \
										.replace('\\%', '%') \
										.replace(u'\u2013', u'--') \
										.replace(u'\u2014', u'---')

		self.attributes['video_url'] = self.attributes['video_url'].replace( "/watch?v=", '/embed/' )
		self.width = options.get('width') or u'640px'
		self.height = options.get('height') or unicode((int(self.width.replace('px',''))/640) * 360)+'px'
		_t = self.attributes['video_url'].split('/')
		if 'youtube' in _t[2]:
			# TODO: See https://github.com/coleifer/micawber
			# for handling this; our poster and thumbnail are just
			# guesses.
			self.attributes['service'] = 'youtube'
			self.attributes['video_id'] = _t[len(_t)-1].split('?')[0]
			self.attributes['poster'] = '//img.youtube.com/vi/' + self.attributes['video_id'] + '/0.jpg'
			self.attributes['thumbnail'] = '//img.youtube.com/vi/' + self.attributes['video_id'] + '/1.jpg'
		return result

# This command is a HACK to work around issues in the web app and pad with in-line
# Kaltura videos in the content.
class ntiincludekalturavideo(Command):
	args = '[ options:dict ] video_id:str'

	def digest(self, tokens):
		res = super(ntiincludekalturavideo, self).digest(tokens)

		options = self.attributes.get( 'options', {} ) or {}
		__traceback_info__ = options, self.attributes

		video = self.attributes.get( 'video_id' ).split(':')

		partner_id = video[0]
		subpartner_id = video[0] + u'00'
		uiconf_id = u'16401392'
		player_id = u'kaltura_player_' + video[1]
		entry_id = video[1]
		self.video_source = "https://cdnapisec.kaltura.com/p/%s/sp/%s/embedIframeJs/uiconf_id/%s/partner_id/%s?iframeembed=true&playerId=%s&entry_id=%s&flashvars[streamerType]=auto" % \
							(partner_id, subpartner_id, uiconf_id, partner_id, player_id, entry_id)
		self.width = u'640'
		self.height = u'390'

		return res

class ntimediaref(Base.Crossref.ref):
	args = '[options:dict] label:idref'

	def digest(self, tokens):
		tok = super(ntimediaref, self).digest(tokens)

		self._options = self.attributes.get('options', {}) or {}

		self.to_render = False
		if 'to_render' in self._options.keys():
			if self._options['to_render'] in [ u'true', u'True' ]:
				self.to_render = True

		return tok

	@readproperty
	def media(self):
		return self.idref['label']

	@readproperty
	def visibility(self):
		visibility = self._options.get('visibility') or None
		if visibility is None:
			return self.media.visibility
		return visibility

class ntimedia(LocalContentMixin, Base.Float, plastexids.NTIIDMixin):
	blockType = True
	args = '[ options:dict ]'

	_ntiid_title_attr_name = 'ref'
	_ntiid_allow_missing_title = False

	creator = None
	num_sources = 0
	title = 'No Title'
	closed_caption = None

	@readproperty
	def description(self):
		return None

	@readproperty
	def transcripts(self):
		return None

# audio

class ntiaudioname(Command):
	unicode = ''

class ntiaudio(ntimedia):

	counter = 'ntiaudio'

	_ntiid_type = 'NTIAudio'
	_ntiid_suffix = 'ntiaudio.'
	_ntiid_allow_missing_title = True
	_ntiid_cache_map_name = '_ntiaudio_ntiid_map'

	itemprop = "presentation-audio"
	mime_type = mimeType = "application/vnd.nextthought.ntiaudio"

	# A Float subclass to get \caption handling
	class caption(Base.Floats.Caption):
		counter = 'figure'

	class ntiaudiosource(Command):
		args = '[ options:dict ] service:str id:str'
		blockType = True

		priority = 0
		thumbnail = None

		def digest(self, tokens):
			"""
			Handle creating the necessary datastructures for each audio type.
			"""
			super(ntiaudio.ntiaudiosource, self).digest(tokens)

			self.priority = self.parentNode.num_sources
			self.parentNode.num_sources += 1

			self.src = {}
			if self.attributes['service']:
				if self.attributes['service'] == 'html5':
					self.service = 'html5'
					self.src['mp3'] = self.attributes['id'] + '.mp3'
					# self.src['m4a'] = self.attributes['id'] + '.m4a'
					self.src['wav'] = self.attributes['id'] + '.wav'
					# self.src['ogg'] = self.attributes['id'] + '.ogg'
					self.thumbnail = self.attributes['id'] + '-thumb.jpg'
				else:
					logger.warning('Unknown audio type: %s', self.attributes['service'])

	def digest(self, tokens):
		res = super(ntiaudio, self).digest(tokens)
		if self.macroMode == self.MODE_BEGIN:
			options = self.attributes.get('options', {}) or {}
			__traceback_info__ = options, self.attributes

			if 'show-card' in options:
				self.itemprop = 'presentation-card'

			if 'creator' in options:
				self.creator = options['creator']

			self.visibility = u'everyone'
			if 'visibility' in options.keys():
				self.visibility = options['visibility']

		return res

	@readproperty
	def description(self):
		texts = []
		for child in self.allChildNodes:
			# Try to extract the text children, ignoring the caption and label, etc
			if 	child.nodeType == self.TEXT_NODE and \
				(child.parentNode == self or child.parentNode.nodeName == 'par'):
				texts.append(unicode(child))

		return _incoming_sources_as_plain_text(texts)

	@readproperty
	def audio_sources(self):
		sources = self.getElementsByTagName('ntiaudiosource')
		output = render_children(self.renderer, sources)
		return cfg_interfaces.HTMLContentFragment(''.join(output).strip())

	@readproperty
	def transcripts(self):
		sources = self.getElementsByTagName('mediatranscript')
		output = render_children(self.renderer, sources)
		return cfg_interfaces.HTMLContentFragment(''.join(output).strip())

class ntiaudioref(ntimediaref):
	pass

# video

class ntivideoname(Command):
	unicode = ''

class ntivideo(ntimedia):

	counter = 'ntivideo'
	_ntiid_type = 'NTIVideo'
	_ntiid_suffix = 'ntivideo.'
	_ntiid_cache_map_name = '_ntivideo_ntiid_map'

	itemprop = "presentation-video"
	mimeType = "application/vnd.nextthought.ntivideo"

	subtitle = None

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

			# options = self.attributes['options'] or {}

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
				elif self.attributes['service'] == 'kaltura':
					self.service = 'kaltura'
					self.src['other'] = self.attributes['id']
					partnerId, entryId = self.attributes['id'].split(':')
					self.poster = '//www.kaltura.com/p/' + partnerId + '/thumbnail/entry_id/' + entryId + '/width/1280/'
					self.thumbnail = '//www.kaltura.com/p/' + partnerId + '/thumbnail/entry_id/' + entryId + '/width/640/'
				elif self.attributes['service'] == 'vimeo':
					self.service = 'vimeo'
					self.src['other'] = self.attributes['id']
				else:
					logger.warning('Unknown video type: %s', self.attributes['service'])

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

			self.visibility = u'everyone'
			if 'visibility' in options.keys():
				self.visibility = options['visibility']

		return res

	@readproperty
	def description(self):
		texts = []
		for child in self.allChildNodes:
			# Try to extract the text children, ignoring the caption and label, etc
			if 	child.nodeType == self.TEXT_NODE and \
				(child.parentNode == self or child.parentNode.nodeName == 'par'):
				texts.append( unicode( child ) )

		return _incoming_sources_as_plain_text( texts )

	@readproperty
	def poster(self):
		sources = self.getElementsByTagName( 'ntivideosource' )
		return sources[0].poster

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

class ntivideoref(ntimediaref):
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

class ntifancyhref(Base.Command):
	args = 'url:str:source self class'

class textsuperscript(Base.Command):
	args = 'self'

class textsubscript(Base.Command):
	args = 'self'

# Custom text treatments
class modified(TextCommand):
	pass

# The following are LaTeX 2e escape commands

class backslash(Base.Command):
	unicode = u'\u005C'

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

# Command to add descriptions to some NTI objects
class ntidescription(Base.Command):
	args = 'content:str:source'

# Media collection
class ntimediacollection(Base.Command):
	pass

class ntimediacollection(Base.Environment,plastexids.NTIIDMixin):
	args = '[options] <title:str:source>'
	blockType = True

	def digest(self, tokens):
		tok = super(ntimediacollection,self).digest(tokens)

		self.options = self.attributes.get( 'options', {} ) or {}
		self.title = self.attributes.get('title')

		return tok

	@readproperty
	def description(self):
		description = u''
		descriptions = self.getElementsByTagName('ntidescription')
		if descriptions:
			description = descriptions[0].attributes.get('content')
		return description


# Videos
class ntivideorollname(Base.Command):
	pass

class ntivideoroll(ntimediacollection):
	counter = "ntivideoroll"
	_ntiid_cache_map_name = '_ntivideoroll_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'ntivideoroll.'
	_ntiid_title_attr_name = 'ref'
	_ntiid_type = 'NTIVR'

# Image collections
class ntiimagecollectionname(Base.Command):
	pass

class ntiimagecollection(ntimediacollection):
	counter = "ntiimagecollection"
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

def _incoming_sources_as_plain_text(texts):
	"""
	Given the source of text nodes in a sequence, convert
	them to a single string that should be viewable as plain text.
	"""
	# They come in from latex, so by definition they are latex content
	# fragments. But they probably don't implement the interface.
	# If we try to convert them, they will be assumed to be a
	# plain text string and we will try to latex escape them, which would
	# be wrong. So directly instantiate the prime class.
	# NOTE: Actually, the callers of this are converting the children to
	# unicode() in a rendering context, which actually should
	# properly render them...to HTML. So really this is probably
	# incoming HTML.
	latex_string = cfg_interfaces.LatexContentFragment( ''.join( texts ).strip() )
	# TODO: The latex-to-plain conversion is essentially a no-op.
	# We can probably do better
	return cfg_interfaces.IPlainTextContentFragment( latex_string )

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
			if 	child.nodeType == self.TEXT_NODE and \
				(child.parentNode == self or child.parentNode.nodeName == 'par'):
				texts.append( unicode( child ) )

		return _incoming_sources_as_plain_text( texts )

###############################################################################
# The following block of commands concern representing related readings
###############################################################################

class relatedworkname(Base.Command):
	pass

@interface.implementer(crd_interfaces.IEmbeddedContainer)
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
	target_ntiid = None
	_description = None
	_uri = u''

	class worktitle(Base.Command):
		args = 'title'

		def digest(self, tokens):
			tok = super(relatedwork.worktitle,self).digest(tokens)
			self.parentNode.title = self.attributes['title']
			return tok

	class workcreator(Base.Command):
		args = 'creator'

		def digest(self, tokens):
			tok = super(relatedwork.workcreator,self).digest(tokens)
			self.parentNode.creator = self.attributes['creator']
			return tok

	class worksource(Base.Command):
		args = 'uri:url'

		def digest(self, tokens):
			tok = super(relatedwork.worksource,self).digest(tokens)
			self.attributes['uri'] =  self.attributes['uri'].source.replace( ' ', '' ).replace( '\\&', '&' ).replace( '\\_', '_' ).replace( '\\%', '%' ).replace(u'\u2013', u'--').replace(u'\u2014', u'---')
			return tok

	class worksourceref(Base.Crossref.ref):
		args = 'target:idref'

	def digest(self, tokens):
		tok = super(relatedwork,self).digest(tokens)

		options = self.attributes.get( 'options', {} ) or {}
		self.visibility = 'everyone'
		if 'visibility' in options.keys():
			self.visibility = options['visibility']

		self.target_ntiid = None
		self.targetMimeType = None

		icons = self.getElementsByTagName('includegraphics')
		if icons:
			self.iconResource = icons[0]

		return tok

	@readproperty
	def description(self):
		if self._description is None:
			self._description = TeXFragment()
			self._description.parentNode = self
			self._description.ownerDocument = self.ownerDocument
			node_types = ['label', 'worktitle', 'workcreator', 'worksource', 'worksourceref', 'includegraphics']
			for child in self.childNodes:
				if child.nodeName not in node_types:
					self._description.appendChild(child)
		return self._description

	@readproperty
	def uri(self):
		if not self._uri:
			worksources = self.getElementsByTagName('worksource')
			if worksources:
				self._uri = worksources[0].attributes.get('uri')
			else:
				worksources = self.getElementsByTagName('worksourceref')
				if worksources:
					if hasattr(worksources[0].idref['target'], 'ntiid'):
						self._uri = worksources[0].idref['target'].ntiid
		return self._uri

	def gen_target_ntiid(self):
		from nti.ntiids.ntiids import is_valid_ntiid_string

		uri = self.uri
		if is_valid_ntiid_string( uri ):
			self.target_ntiid = uri
			self.targetMimeType = 'application/vnd.nextthought.content'
			ntiid_specific = ntiids.get_specific( uri )
			self.icon = '/'.join([u'..', ntiid_specific.split('.')[0], 'icons', 'chapters', 'generic_book.png'])

		else:
			from nti.ntiids.ntiids import make_ntiid, TYPE_UUID
			from hashlib import md5
			# TODO: Hmm, what to use as the provider? Look for a hostname in the
			# URL?
			self.target_ntiid = make_ntiid( provider='NTI',
											nttype=TYPE_UUID,
											specific=md5(uri).hexdigest() )
			self.targetMimeType = 'application/vnd.nextthought.externallink'

class relatedworkrefname(Base.Command):
	pass

@interface.implementer(crd_interfaces.IEmbeddedContainer)
class relatedworkref(Base.Crossref.ref, plastexids.NTIIDMixin):
	args = '[ options:dict ] label:idref uri:url desc < NTIID:str >'

	counter = 'relatedworkref'
	blockType = True
	_ntiid_cache_map_name = '_relatedworkref_ntiid_map'
	_ntiid_allow_missing_title = False
	_ntiid_suffix = 'relatedworkref.'
	_ntiid_title_attr_name = 'label'
	_ntiid_type = 'RelatedWorkRef'

	#: From IEmbeddedContainer
	mimeType = "application/vnd.nextthought.relatedworkref"
	_targetMimeType = None
	_target_ntiid = None

	def digest(self, tokens):
		tok = super(relatedworkref, self).digest(tokens)

		self._options = self.attributes.get( 'options', {} ) or {}
		self.label = self.attributes.get('label')

		self._uri = self.attributes['uri']
		if hasattr(self._uri, 'source'):
			self._uri = self._uri.source.replace(' ', '') \
										.replace('\\&', '&') \
										.replace('\\_', '_') \
										.replace('\\%', '%') \
										.replace(u'\u2013', u'--') \
										.replace(u'\u2014', u'---')
		self.relatedwork = self.idref['label']
		self._description = None

		# Remove the empty NTIID key so auto NTIID generation works

		# SAJ: It is a hack to have this code here. The code in
		# contentrendering.platexids should account for the possibility that the
		# value of the 'NTIID' key could be 'None', however I have not evaluated what
		# undesired side affects might come from changing the code in
		# contentrendering.plastexids.
		if 'NTIID' in self.attributes and self.attributes['NTIID'] is None:
			del self.attributes['NTIID']

		self._target_ntiid = None

		return tok

	@readproperty
	def category(self):
		return self._options.get('category') or u'required'

	@readproperty
	def description(self):
		description = self.attributes.get('desc')
		if len(description.childNodes) == 0:
			return self.relatedwork.description
		return description

	@readproperty
	def icon(self):
		if self.relatedwork.iconResource is not None:
			return self.relatedwork.iconResource.image.url
		elif self.relatedwork.icon is not None:
			return self.relatedwork.icon
		else:
			return ''

	@readproperty
	def target_ntiid(self):
		if self._target_ntiid is None:
			self.gen_target_ntiid()
		return self._target_ntiid

	@readproperty
	def targetMimeType(self):
		if self._targetMimeType is None:
			self.gen_target_ntiid()
		return self._targetMimeType

	@readproperty
	def uri(self):
		if self._uri == '' or self._uri is None:
			return self.relatedwork.uri
		return self._uri

	@readproperty
	def visibility(self):
		visibility = self._options.get('visibility')
		if visibility == '' or visibility is None:
			return self.relatedwork.visibility
		return visibility

	def gen_target_ntiid(self):
		from nti.ntiids.ntiids import is_valid_ntiid_string

		uri = self.uri
		if is_valid_ntiid_string( uri ):
			self._target_ntiid = uri
			self._targetMimeType = 'application/vnd.nextthought.content'
		else:
			from nti.ntiids.ntiids import make_ntiid, TYPE_UUID
			from hashlib import md5
			# TODO: Hmm, what to use as the provider? Look for a hostname in the
			# URL?
			self._target_ntiid = make_ntiid( provider='NTI',
											nttype=TYPE_UUID,
											specific=md5(uri).hexdigest() )
			self._targetMimeType = 'application/vnd.nextthought.externallink'

###############################################################################
# The following block of commands concern representing forum discussions.
###############################################################################

class ntidiscussionname(Base.Command):
	pass

class ntidiscussionref(Base.Crossref.ref):

	@readproperty
	def discussion(self):
		return self.idref['label']


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
		args = 'title'

		def digest(self, tokens):
			tok = super(ntidiscussion.discussiontitle,self).digest(tokens)
			self.parentNode.title = self.attributes['title']
			return tok

	class discussionsubtitle(Base.Command):
		args = 'subtitle'

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

class ntisequenceitem(LocalContentMixin, Base.Environment):
	args = '[options:dict]'

	def invoke(self, tex):
		res = super(ntisequenceitem, self).invoke(tex)
		if 'options' not in self.attributes or not self.attributes['options']:
			self.attributes['options'] = {}
		return res

	def digest(self, tokens):
		tok = super(ntisequenceitem, self).digest(tokens)
		if self.macroMode != Base.Environment.MODE_END:
			options = self.attributes.get('options', {}) or {}
			__traceback_info__ = options, self.attributes
			for k, v in options.items():
				setattr(self, k, v)
		return tok

class ntisequence(LocalContentMixin, Base.List):
	args = '[options:dict]'

	def invoke(self, tex):
		res = super(ntisequence, self).invoke(tex)
		if 'options' not in self.attributes or not self.attributes['options']:
			self.attributes['options'] = {}
		return res

	def digest(self, tokens):
		tok = super(ntisequence, self).digest(tokens)
		if self.macroMode != Base.Environment.MODE_END:
			_items = self.getElementsByTagName('ntisequenceitem')
			assert len(_items) >= 1

			options = self.attributes.get('options', {}) or {}
			__traceback_info__ = options, self.attributes
			for k, v in options.items():
				setattr(self, k, v)
		return tok

class ntisequenceref(Base.Crossref.ref):
	args = '[options:dict] label:idref'


class ntidirectionsblock(Base.Command):
	args = 'directions example lang_code:str:source'
	blockType = True

# The sidebar environment is to be the base class for other side types such as those from AoPS.
class sidebar(Environment, plastexids.NTIIDMixin):
	args = 'title'
	blockType = True

	counter = 'sidebar'
	_ntiid_cache_map_name = '_sidebar_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'sidebar.'
	_ntiid_title_attr_name = 'title'
	_ntiid_type = 'HTML:NTISidebar'
	embedded_doc_cross_ref_url = property(plastexids._embedded_node_cross_ref_url)


class flatsidebar(sidebar):
	pass

class audiosidebar(sidebar):
	args = 'audioref'

class ntigraphicsidebar(sidebar):
	args = 'title graphic_class:str:source'

class ntiidref(Base.Crossref.ref):
	"""
	Used for producing a cross-document link, like a normal
	ref, but output as an NTIID.
	"""
	macroName = 'ntiidref'

@interface.implementer(resource_interfaces.IRepresentableContentUnit,
		       resource_interfaces.IRepresentationPreferences)
class ntifileview(Command, plastexids.NTIIDMixin):
	args = '[options:dict] src:str:source self class'
	resourceTypes = ( 'html_wrapped', )

	counter = 'fileview'
	_ntiid_cache_map_name = '_fileview_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'fileview.'
	_ntiid_title_attr_name = 'src'
	_ntiid_type = 'HTML:FileView'

	def invoke( self, tex ):
		result = super(ntifileview, self).invoke( tex )
		self.attributes['src'] = os.path.join(
			self.ownerDocument.userdata.getPath('working-dir'), self.attributes['src'])
		self.attributes['presentation'] = 'popup'
		return result

def ProcessOptions( options, document ):
	document.context.newcounter('ntiaudio')
	document.context.newcounter('ntivideo')
	document.context.newcounter('ntilocalvideo')
	document.context.newcounter('ntivideoroll')
	document.context.newcounter('ntiimagecollection')
	document.context.newcounter('nticard')
	document.context.newcounter('relatedwork')
	document.context.newcounter('relatedworkref', initial=-1)
	document.context.newcounter('ntidiscussion')
	document.context.newcounter('sidebar')
	document.context.newcounter('fileview')

from plasTeX.interfaces import IOptionAwarePythonPackage
interface.moduleProvides(IOptionAwarePythonPackage)
