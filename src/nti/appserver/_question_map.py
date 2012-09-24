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

import simplejson

from zope import interface
from zope import component
from zope.lifecycleevent.interfaces import IObjectCreatedEvent

import nti.externalization.internalization

from . import interfaces as app_interfaces
from nti.contentfragments import interfaces as cfg_interfaces
from nti.contentlibrary import interfaces as lib_interfaces

def _ntiid_object_hook( k, v, x ):
	"""
	In this one, rare, case, we are reading things from external
	sources and need to preserve an NTIID value.
	"""
	if 'NTIID' in x and not getattr( v, 'ntiid', None ):
		v.ntiid = x['NTIID']
		v.__name__ = v.ntiid
	if 'value' in x and 'Class' in x and x['Class'] == 'LatexSymbolicMathSolution' and x['value'] != v.value:
		# We started out with LatexContentFragments when we wrote these,
		# and if we re-convert when we read, we tend to over-escape
		# One thing we do need to do, though, is replace long dashes with standard minus signs
		v.value = cfg_interfaces.LatexContentFragment( x['value'].replace( '\u2212', '-') )

	return v

@interface.implementer( app_interfaces.IFileQuestionMap )
class QuestionMap(dict):

	def __init__( self ):
		super(QuestionMap,self).__init__()
		self.by_file = {}

	def __process_assessments( self, assessment_item_dict, containing_filename, hierarchy_entry, level_ntiid=None ):
		for k, v in assessment_item_dict.items():
			__traceback_info__ = k, v

			factory = nti.externalization.internalization.find_factory_for( v )
			assert factory is not None
			obj = factory()
			nti.externalization.internalization.update_from_external_object( obj, v, require_updater=True, notify=False, object_hook=_ntiid_object_hook )
			obj.ntiid = k
			self[k] = obj

			obj.__name__ = k
			obj.__parent__ = level_ntiid

			if containing_filename:
				self.by_file[containing_filename].append( obj )
				# Hack in ACL support. We are piggybacking off of
				# IDelimitedEntry's support in authorization_acl.py
				def read_contents_of_sibling_entry( sibling_name ):
					return hierarchy_entry.read_contents_of_sibling_entry( sibling_name )

				# FIXME: This is so very, very wrong
				obj.filename = containing_filename
				obj.read_contents_of_sibling_entry = read_contents_of_sibling_entry
				interface.alsoProvides( obj, lib_interfaces.IFilesystemEntry )

	def _from_index_entry(self, index, hierarchy_entry, nearest_containing_key=None, nearest_containing_ntiid=None ):
		key_for_this_level = nearest_containing_key
		if index.get( 'filename' ):
			key_for_this_level = hierarchy_entry.make_sibling_key( index['filename'] )
			factory = list
			if key_for_this_level in self.by_file:
				# Across all indexes, every filename key should be unique.
				# We rely on this property when we lookup the objects to return
				# We make an exception for index.html, due to a duplicate bug in
				# old versions of the exporter, but we ensure we can't put any questions on it
				if index['filename'] == 'index.html':
					factory = tuple
					logger.warning( "Duplicate 'index.html' entry in %s; update content", hierarchy_entry )
				else: # pragma: no cover
					raise ValueError( key_for_this_level, "Found a second entry for the same file" )
			self.by_file[key_for_this_level] = factory()


		# JAM: This is very odd. Each level of the tree uses its own key
		# to store the assessment items found in each of its children. At one time we had a situation
		# where too many 'filename'-less intervening levels caused the chain to get broken and the
		# leaf questions to effectively be lost. We are now carrying the nearest containing key around,
		# so that's no longer a problem, but now we may be returning too many items?
		level_ntiid = index.get( 'NTIID' ) or nearest_containing_ntiid
		for item in index['Items'].values():
			self.__process_assessments( item.get( "AssessmentItems", {} ), key_for_this_level, hierarchy_entry, level_ntiid )

			if 'Items' in item:
				self._from_index_entry( item, hierarchy_entry, nearest_containing_key=key_for_this_level, nearest_containing_ntiid=level_ntiid )


@component.adapter(lib_interfaces.IContentPackage,IObjectCreatedEvent)
def add_assessment_items_from_new_content( title, event ):
	"""
	Assessment items have their NTIID as their __name__, and the NTIID of their primary
	container within this context as their __parent__ (that should really be the hierarchy entry)
	"""
	question_map = component.getUtility( app_interfaces.IFileQuestionMap )
	if question_map is None: #pragma: no cover
		return

	logger.info( "Adding assessment items from new content %s %s", title, event )

	asm_index_text = title.read_contents_of_sibling_entry( 'assessment_index.json' )
	_populate_question_map_from_text( question_map, asm_index_text, title )

def _populate_question_map_from_text( question_map, asm_index_text, title ):
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
