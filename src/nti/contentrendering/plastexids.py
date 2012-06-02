#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions related to ID and NTIID generation within a PlasTeX DOM.

Some of these functions are destructive to existing objects and so
to use them you must specifically request it.

$Id$
"""
from __future__ import print_function, unicode_literals

import functools
import hashlib


import plasTeX
from plasTeX.Logging import getLogger
log = getLogger(__name__)
logger = log


from zope.deprecation import deprecate
from nti.deprecated import hiding_warnings


@deprecate("Prefer the section element ntiid attribute")
def nextID(self, suffix=''):
	ntiid = getattr(self, 'NTIID', -1)

	ntiid = ntiid + 1

	setattr(self, 'NTIID', ntiid)
	provider = self.config.get( "NTI", "provider" )
	return 'tag:nextthought.com,2011-10:%s-HTML-%s.%s%s' % (provider,self.userdata['jobname'], suffix, ntiid)



# SectionUtils is the (a) parent of chapter, section, ..., paragraph, as well as document
from plasTeX.Base.LaTeX.Sectioning import SectionUtils
def _section_ntiid(self):

	# If an NTIID was specified in the source, use that
	if hasattr(self, 'attributes') and 'NTIID' in self.attributes:
		return self.attributes['NTIID']

	# Use a cached value if one exists
	if hasattr(self,"@NTIID"):
		return getattr(self, "@NTIID")

	document = self.ownerDocument
	config = document.config
	# Use an ID if it exists and WAS NOT generated
	# (see plasTeX/__init__.py; also relied on in Renderers/__init__.py)
	if not hasattr( self, "@hasgenid" ) and getattr( self, "@id", None ):
		local = getattr( self, "@id" )
	elif (hasattr(self, 'title') or not getattr( self, '_ntiid_allow_missing_title', False)) \
	  and self.title \
	  and getattr(self.title, 'textContent', self.title):
		# Sometimes title is a string, sometimes its a TexFragment
		title = self.title
		if hasattr(self.title, 'textContent'):
			title = self.title.textContent
		# TODO: When we need to generate a number, if the object is associated
		# with a counter, could/should we use the counter?
		map_name = getattr( self, '_ntiid_cache_map_name', '_section_ntiids_map' )
		_section_ntiids_map = document.userdata.setdefault( map_name, {} )
		counter = _section_ntiids_map.setdefault( title, 0 )
		if counter == 0:
			local = title
		else:
			local = title + '.' + str(counter)
		_section_ntiids_map[title] = counter + 1
	else:
		# Hmm. An untitled element that is also not
		# labeled. This is most likely a paragraph. What can we do for a persistent
		# name? Does it even matter?
		logger.warn("Falling back to generated NTIID for %s (%s)", type(self), repr(self)[:50])
		with hiding_warnings():
			setattr(self, "@NTIID", nextID(document, getattr( self, '_ntiid_suffix', '')))
		return getattr(self, "@NTIID")

	# TODO: This is a half-assed approach to escaping
	local = local.replace( ' ', '_' ).replace( '-', '_' ).replace('?','_').lower()
	provider = config.get( "NTI", "provider" )
	ntiid = 'tag:nextthought.com,2011-10:%s-HTML-%s.%s' % (provider,document.userdata['jobname'], local)
	setattr( self, "@NTIID", ntiid )
	return ntiid

def _section_ntiid_filename(self):
	if not hasattr(self, 'config'):
		return

	level = getattr(self, 'splitlevel',	self.config['files']['split-level'])

	# If our level doesn't invoke a split, don't return a filename
	# (This is duplicated from Renderers)
	if self.level > level:
		return
	# It's confusing to have the filenames be valid
	# URLs (tag:) themselves. Escaping is required, but doesn't happen.
	return self.ntiid.replace( ':', '_' ) if self.ntiid else None


class NTIIDMixin(object):
	"""
	Adds the 'ntiid' property to an object (presumably a plasTeX Macro).

	You can define the '_ntiid_cache_map_name' property to influence
	the namespace of generated numbers.

	If the `title` of the element should be allowed to be absent, you can set the
	`_ntiid_allow_missing_title` property to True.

	"""
	pass
NTIIDMixin.ntiid = property(_section_ntiid)
NTIIDMixin.filenameoverride = property(_section_ntiid_filename)


# Attempt to generate stable IDs for paragraphs. Our current approach
# is to use a hash of the source. This is very, very fragile to changes
# in the text, but works well for reorganizing content. We should probably try to do
# something like a Soundex encoding
def _par_id_get(self):
	_id = getattr( self, "@id", self )
	if _id is not self: return _id

	if self.isElementContentWhitespace or not self.source.strip():
		return None

	document = self.ownerDocument
	source = self.source
	# A fairly common case is to have a label as a first child (maybe following some whitespace); in that case,
	# for all intents and purposes (in rendering) we want our external id to be the same
	# as the label value. However, we don't want to duplicate IDs in the DOM
	first_non_blank_child = None
	for child in self.childNodes:
		first_non_blank_child = child
		if child.nodeType != child.TEXT_NODE or child.textContent.strip():
			break

	if first_non_blank_child.nodeName == 'label' and 'label' in first_non_blank_child.attributes:
		setattr( self, "@id", None )
		return None

	if source and source.strip():
		_id = hashlib.md5(source.strip().encode('utf-8')).hexdigest()
	else:
		counter = document.userdata.setdefault( '_par_counter', 1 )
		_id = 'p%10d' % counter
		document.userdata['_par_counter'] = counter + 1

	used_pars = document.userdata.setdefault( '_par_used_ids', set() )
	while _id in used_pars:
		counter = document.userdata.setdefault( '_par_counter', 1 )
		_id = _id + '.' + str(counter)
		document.userdata['_par_counter'] = counter + 1
	used_pars.add( _id )

	setattr( self, "@id", _id )
	setattr( self, "@hasgenid", True )
	return _id

def patch_all():
	"""
	Performs all the patching.
	In particular, this causes paragraph elements to generate better IDs
	and sections to generate more appropriate filenames.
	"""
	plasTeX.Base.par.id = property(_par_id_get,plasTeX.Base.par.id.fset)
	def catching(f):
		@functools.wraps(f)
		def y(self):
			try:
				return f(self)
			except Exception:
				logger.exception("Failed to compute NTIID for %s (%s)", type(self), repr(self)[:50] )
				raise
		return y

	SectionUtils.ntiid = property(catching(_section_ntiid))
	SectionUtils.filenameoverride = property(catching(_section_ntiid_filename))
	plasTeX.TeXDocument.nextNTIID = nextID # Non-desctructive patch
