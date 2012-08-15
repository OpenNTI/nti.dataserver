#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of the assessment question map and supporting
functions to maintain it.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os.path
import simplejson

from zope import interface
from zope import component

import nti.externalization.internalization

from . import interfaces as app_interfaces
from nti.contentfragments import interfaces as cfg_interfaces
from nti.contentlibrary import interfaces as lib_interfaces

@interface.implementer( app_interfaces.IFileQuestionMap )
class QuestionMap(dict):

	def __init__( self ):
		super(QuestionMap,self).__init__()
		self.by_file = {}

	def _from_index_entry(self, index, hierarchy_entry):
		filename = None
		if index.get( 'filename' ):
			filename = hierarchy_entry.make_sibling_key( index['filename'] )
		for item in index['Items'].values():
			for k, v in item['AssessmentItems'].items():
				__traceback_info__ = k, v

				factory = nti.externalization.internalization.find_factory_for( v )
				assert factory is not None
				obj = factory()
				nti.externalization.internalization.update_from_external_object( obj, v, require_updater=True )
				obj.ntiid = k
				if filename:
					self.by_file.setdefault( filename, [] ).append( obj )
					# Hack in ACL support. We are piggybacking off of
					# IDelimitedEntry's support in authorization_acl.py
					def read_contents_of_sibling_entry( sibling_name ):
						try:
							return open( os.path.join( os.path.dirname( filename ), sibling_name ), 'r' ).read()
						except (OSError,IOError):
							return None

					# FIXME: This is so very, very wrong
					obj.filename = filename
					obj.read_contents_of_sibling_entry = read_contents_of_sibling_entry
					interface.alsoProvides( obj, lib_interfaces.IFilesystemEntry )

				self[k] = obj
			if 'Items' in item:
				self._from_index_entry( item, hierarchy_entry )


@component.adapter(lib_interfaces.IContentPackage,component.interfaces.IObjectEvent)
def add_assessment_items_from_new_content( title, event ):
	question_map = component.getUtility( app_interfaces.IFileQuestionMap )
	if question_map is None: #pragma: no cover
		return

	asm_index_text = title.read_contents_of_sibling_entry( 'assessment_index.json' )
	if asm_index_text:
		asm_index_text = unicode(asm_index_text)
		# In this one specific case, we know that these are already
		# content fragments (probably HTML content fragments)
		# If we go through the normal adapter process from string to
		# fragment, we will wind up with sanitized HTML, which is not what
		# we want, in this case
		# TODO: Needs specific test cases
		def hook(o):
			return dict( (k,cfg_interfaces.UnicodeContentFragment(v) if isinstance(v, unicode) else v) for k, v in o )

		index = simplejson.loads( asm_index_text,
								  object_pairs_hook=hook )
		try:
			question_map._from_index_entry( index, title )
		except (interface.Invalid, ValueError): # pragma: no cover
			# Because the map is updated in place, depending on where the error
			# was, we might have some data...that's not good, but it's not a show stopper either,
			# since we shouldn't get content like this out of the rendering process
			logger.exception( "Failed to load assessment items, invalid assessment_index for %s", title )
