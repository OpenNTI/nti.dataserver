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

def _make_ntiid( document, local, local_prefix='', nttype='HTML' ):
	local = unicode(local)
	local = local.replace( ' ', '_' ).replace( '-', '_' ).replace('?','_').lower()
	provider = document.config.get( "NTI", "provider" )

	return 'tag:nextthought.com,2011-10:%s-%s-%s.%s%s' % (provider, nttype, document.userdata['jobname'], local_prefix, local)


@deprecate("Prefer the section element ntiid attribute")
def nextID(self, suffix=''):
	ntiid = getattr(self, 'NTIID', -1)

	ntiid = ntiid + 1

	setattr(self, 'NTIID', ntiid)
	return _make_ntiid( self,  ntiid, suffix )




# SectionUtils is the (a) parent of chapter, section, ..., paragraph, as well as document
from plasTeX.Base.LaTeX.Sectioning import SectionUtils

def _ntiid_get_local_part_title(self):
	title = None
	attr = getattr( self, '_ntiid_title_attr_name', 'title' )
	if (hasattr(self, attr) or not getattr( self, '_ntiid_allow_missing_title', False)):
		title = getattr(self, attr)
		if title \
		  and getattr(title, 'textContent', title):
			# Sometimes title is a string, sometimes its a TexFragment
			if hasattr(title, 'textContent'):
				title = title.textContent
	return title

def _preferred_local_part(self):
	"""
	Look for and return the "local" part of an NTIID, based on the preferred
	value for the object. Typically, this will be the `title` of the element,
	but this may be overridden. Takes into account duplicates.
	:raises AttributeError: If the element has no title.
	"""
	local = None
	document = self.ownerDocument
	title = getattr(self, '_ntiid_get_local_part', None )
	if title:
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

	return local

def _section_ntiid(self):

	# If an NTIID was specified in the source, use that
	if hasattr(self, 'attributes') and 'NTIID' in self.attributes:
		return self.attributes['NTIID']

	# Use a cached value if one exists
	if hasattr(self,"@NTIID"):
		return getattr(self, "@NTIID")

	document = self.ownerDocument
	# Use an ID if it exists and WAS NOT generated
	# (see plasTeX/__init__.py; also relied on in Renderers/__init__.py)
	local = None
	if not hasattr( self, "@hasgenid" ) and getattr( self, "@id", None ):
		local = getattr( self, "@id" )
	if local is None:
		local = _preferred_local_part(self) # not idempotent, has side effects, call only once
	if not local:
		# Hmm. An untitled element that is also not
		# labeled. This is most likely a paragraph. What can we do for a persistent
		# name? Does it even matter?
		logger.warn("Falling back to generated NTIID for %s (%s)", type(self), repr(self)[:50])
		with hiding_warnings():
			setattr(self, "@NTIID", nextID(document, getattr( self, '_ntiid_suffix', '')))
		return getattr(self, "@NTIID")

	ntiid = _make_ntiid( document, local,
						 getattr( self, '_ntiid_suffix', '' ),
						 getattr( self, '_ntiid_type', 'HTML' )	)
	setattr( self, "@NTIID", ntiid )
	return ntiid

def _section_ntiid_filename(self):
	if not hasattr(self, 'config'):
		return

	override = getattr( self, '@filenameoverride', None )
	if override:
		return override

	level = getattr(self, 'splitlevel',	self.config['files']['split-level'])

	# If our level doesn't invoke a split, don't return a filename
	# (This is duplicated from Renderers)
	if self.level > level:
		return
	# It's confusing to have the filenames be valid
	# URLs (tag:) themselves. See Filenames.py and Config.py
	bad_chars = self.config['files']['bad-chars']
	bad_chars_replacement = self.config['files']['bad-chars-sub']
	ntiid = self.ntiid
	if ntiid:
		for bad_char in bad_chars:
			ntiid = ntiid.replace( bad_char, bad_chars_replacement )
		return ntiid



def _set_section_ntiid_filename( self, value ):
	setattr( self, '@filenameoverride', value )


def _catching(f, computing='NTIID'):
	@functools.wraps(f)
	def y(*args):
		try:
			return f(*args)
		except Exception:
			logger.exception("Failed to compute %s for %s (%s)", computing, type(self), repr(self)[:50] )
			raise
	return y

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
NTIIDMixin.filenameoverride = property(_section_ntiid_filename,_set_section_ntiid_filename)
NTIIDMixin._ntiid_get_local_part = property(_ntiid_get_local_part_title)


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

	if first_non_blank_child is not None and first_non_blank_child.nodeName == 'label' and 'label' in first_non_blank_child.attributes:
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

class StableIDMixin(object):
	"""
	Attempts to generate more stable IDs for elements. Can be used when elements
	have source text or may have a label child.
	"""
	pass
StableIDMixin.id = property(_catching(_par_id_get, 'id'),plasTeX.Macro.id.fset) # TODO: Different counters for this than _par_used_ids?

def patch_all():
	"""
	Performs all the patching.
	In particular, this causes paragraph elements to generate better IDs
	and sections to generate more appropriate filenames.
	"""
	plasTeX.Base.par.id = property(_catching(_par_id_get, 'id' ),plasTeX.Base.par.id.fset)
	plasTeX.Base.Array.id = property(_catching(_par_id_get, 'id'), plasTeX.Base.Array.id.fset)
	from plasTeX.Packages.graphicx import includegraphics
	includegraphics.id =  property(_catching(_par_id_get, 'id'),includegraphics.id.fset) # TODO: Different counters for this than _par_used_ids?
	SectionUtils.ntiid = property(_catching(_section_ntiid))
	SectionUtils.filenameoverride = property(_catching(_section_ntiid_filename), _catching(_set_section_ntiid_filename))
	SectionUtils._ntiid_get_local_part = property(_catching(_ntiid_get_local_part_title))
	plasTeX.TeXDocument.nextNTIID = nextID # Non-desctructive patch
