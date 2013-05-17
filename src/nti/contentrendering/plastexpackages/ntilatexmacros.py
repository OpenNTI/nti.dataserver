#!/usr/bin/env python
# -*- coding: utf-8 -*-

# All of these have too many public methods
#pylint: disable=R0904
# "Method __delitem__ is abstract in Node and not overridden"
#pylint: disable=W0223

from __future__ import print_function, unicode_literals, absolute_import

import hashlib

from zope import interface

from plasTeX import Base, Command, Environment

from plasTeX.Base import Crossref
from plasTeX.Base import TextCommand

from nti.contentrendering import plastexids
from nti.contentrendering import interfaces as crd_interfaces
from nti.contentrendering.plastexpackages._util import LocalContentMixin
from nti.contentrendering.plastexpackages.graphicx import includegraphics

from nti.contentfragments import interfaces as cfg_interfaces

from zope.cachedescriptors.property import readproperty

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
		import os
		import tempfile

		# A standard US page is 612x792 pts, height and width
		# need to be the same multiple of that to preserve aspect ratio
		# such as height=120, width=93
		# We generate a PNG of the complete thing at full size, and then
		# scale it to the various resource sizes when rendering
		# (TODO: Use pyPDF or gs itself to find the actual size of the first page?)
		GHOSTSCRIPT = os.environ.get("GHOSTSCRIPT", "gs")

		fd, output_file = tempfile.mkstemp( '.png', 'thumbnail' )
		# DEVICE=jpeg is another option; using png works better with the image renderer
		cmd = "%(GHOSTSCRIPT)s -dNOPAUSE -dSAFER -dBATCH -q " \
		  "-dFirstPage=%(page)d -dLastPage=%(page)d " \
		  "-dPDFFitPage -dTextAlphaBits=4 -dGraphicsAlphaBits=4 " \
		  " -sDEVICE=pngalpha -dJPEGQ=80 " \
		  " -dDEVICEWIDTH=%(width)d -dDEVICEHEIGHT=%(height)d " \
		  "-sOutputFile=%(output_file)s " \
		  " %(pdf_path)s " % locals() # TODO: make subprocess!
		# When we go with subprocess, note that gs can also take "-" as
		# the source path to read from stdin, if we already have it
		# in memory
		if os.system( cmd ):
			raise Exception( "Failed to run %s" % cmd )
		os.close(fd)
		return output_file

	def _pdf_populate(self, pdf_path):
		import pyPdf
		pdf = pyPdf.PdfFileReader( open( pdf_path, 'rb' ) )
		info = pdf.getDocumentInfo()
		# This dict is weird: [] and get() return different things,
		# with [] returning the strings we want
		if '/Title' in info and info['/Title']:
			self.title = info['/Title']
		if '/Author' in info and info['/Author']:
			self.creator = info['/Author']
		if '/Subject' in info and info['/Subject']:
			self.description = info['/Subject']

		thumb_file = self._pdf_to_thumbnail(pdf_path)
		include = includegraphics()
		include.attributes['file'] = thumb_file
		include.argSource = r'[width=93pt,height=120pt]{%s}' % thumb_file
		include.style['width'] = "93px"
		include.style['height'] = "120px"
		self.appendChild( include )

	def _dom_populate( self, dom ):
		if dom is None:
			return

		# Extract metadata. Need to handle OpenGraph
		# as well as twitter.
		# Here is a poor version of OpenGraph handling;
		# it is bade due to the hardcoded namespaces
		# NOTE: This can be done with rdflib, as it has built-in
		# RDFa handling (which OG is)
		for meta in dom.find('meta'):
			name = meta.get('property') or meta.get( 'name' )
			val = meta.get('content')
			if not name or not val:
				continue
			if name == 'og:title':
				self.title = val
			elif name == 'og:url':
				self.href = val
			elif name == 'og:image':
				# Download and save the image?
				# Right now we are downloading it for size purposes (which may not be
				# needed) but we could choose to cache it locally
				import requests
				from plone.namedfile import NamedImage
				import urlparse

				response = requests.get( val )
				filename = urlparse.urlparse( val ).path.split('/')[-1]
				named_image = NamedImage( data=response.content, filename=filename )
				width, height = named_image.getImageSize()
				# Just enough to go with our template
				class Image(object):
					def __init__( self, image ):
						self.image = image
				class Dimen(object):
					def __init__(self,px):
						self.px = px
				self.image = Image(named_image)
				self.image.image.url = val
				self.image.image.height = Dimen(height)
				self.image.image.width = Dimen(width)

			elif name in ('og:description', 'description'):
				self.description = cfg_interfaces.IPlainTextContentFragment( val )

	def _auto_populate(self):
		import pyquery
		if self._href_override:
			if self._href_override.endswith( '.pdf' ):
				self._pdf_populate(self.href)
			elif self._href_override.endswith( '.html' ):
				self._dom_populate( pyquery.PyQuery( filename=self._href_override ) )
			return

		import requests
		# Must use requests, not the url= argument, as
		# the default Python User-Agent is blocked (note: pyquery 1.2.4 starts using requests internally by default)
		# The custom user-agent string is to trick Google into sending UTF-8.
		response = requests.get( self.href,
								 headers={'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/537.1+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2"},
								 stream=True)
		if 'html' in response.headers.get( 'content-type', '' ):
			dom = pyquery.PyQuery( url=self.href, opener=lambda url, **kwargs: response.text )
			self._dom_populate( dom )
		elif 'pdf' in response.headers.get( 'content-type', '' ):
			import tempfile
			import os
			import shutil
			fd, pdf_path = tempfile.mkstemp( '.pdf', 'download' )
			pdf_file = os.fdopen( fd, 'wb' )
			# TODO: _pdf_populate pulls the whole thing into memory (which could be quite large) when it is read
			# (I think---confirm this), so we might want to use GS to chop it to just
			# one page first, if that preserves metadata.
			# Or can we use GS to get the metadata?
			# The pdfinfo command from poppler (poppler-utils in debian/amazon)
			# can get the metadata, that might be better
			shutil.copyfileobj( response.raw, pdf_file )
			pdf_file.close()
			self._pdf_populate( pdf_path )


	def invoke( self, tex ):
		res = super(nticard,self).invoke( tex )
		# Resolve local files to full paths with the same algorithm that
		# includegraphics uses
		if ('href' in self.attributes
			and '//' not in self.attributes['href'] # not a HTTP[S] url
			and not self.attributes['href'].startswith('tag:') ): # not an NTIID
			from .graphics import _locate_image_file

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

def ProcessOptions( options, document ):
	document.context.newcounter( 'ntilocalvideo' )
	document.context.newcounter( 'ntivideoroll' )
	document.context.newcounter( 'ntiimagecollection' )
	document.context.newcounter( 'nticard' )
