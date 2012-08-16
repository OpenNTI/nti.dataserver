#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implements vocabularies that limit what a user can create.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope.schema import interfaces as sch_interfaces
from zope.componentvocabulary.vocabulary import UtilityVocabulary

from pyramid import security as psec
from pyramid.threadlocal import get_current_request
from pyramid import httpexceptions as hexc

from nti.externalization import interfaces as ext_interfaces
from . import interfaces as app_interfaces

from nti.externalization.internalization import default_externalized_object_factory_finder

from nti.dataserver import users

# TODO: zope.schema.vocabulary provides a vocab registry
# Should we make use of that?

class _CreatableMimeObjectVocabulary(UtilityVocabulary):
	"""
	A vocabulary that reports the names (MIME types) of installed
	:class:`nti.externalization.interfaces.IMimeObjectFactory` objects.
	There
	"""
 	nameOnly = False
 	interface = ext_interfaces.IMimeObjectFactory

 	def __init__( self, context ):
 		super(_CreatableMimeObjectVocabulary,self).__init__( context )
		term_filter = component.queryAdapter(context, app_interfaces.ICreatableObjectFilter, context=context)
		if term_filter:
			self._terms = term_filter.filter_creatable_objects( self._terms )

@interface.implementer(app_interfaces.ICreatableObjectFilter)
class _SimpleRestrictedContentObjectFilter(object):

	RESTRICTED = ('application/vnd.nextthought.canvasurlshape', #images
				  'application/vnd.nextthought.redaction' )

	def __init__( self, context=None ):
		pass

	def filter_creatable_objects( self, terms ):
		for name in self.RESTRICTED:
			terms.pop( name, None )
		return terms

@interface.implementer(sch_interfaces.IVocabularyFactory)
class _UserCreatableMimeObjectVocabularyFactory(object):

	def __init__( self ):
		pass

	def __call__( self, user ):
		return _CreatableMimeObjectVocabulary( user )

@interface.implementer(ext_interfaces.IExternalizedObjectFactoryFinder)
def _user_sensitive_factory_finder( ext_object ):
	vocabulary = None

	# TODO: This process is probably horribly expensive and should be cached
	# install zope.testing hook to clean up the cache
	request = get_current_request()
	if request:
		try:
			auth_user_name = psec.authenticated_userid( request )
		except AssertionError:
			# Some test cases call us with bad header values, causing
			# repoze.who.api.request_classifier and paste.httpheaders to incorrectly
			# blow up
			logger.exception( "Failed to get authenticated userid. If this is not a test case, this is a problem" )
			auth_user_name = None

		if auth_user_name:
			auth_user = users.User.get_user( auth_user_name )
			if auth_user:
				vocabulary = component.getUtility( sch_interfaces.IVocabularyFactory, "Creatable External Object Types" )( auth_user )


	factory = default_externalized_object_factory_finder( ext_object )
	if vocabulary is None or factory is None:
		return factory

	if factory not in vocabulary and component.IFactory.providedBy( factory ):
		# If it's not in the vocabulary, don't let it be created.
		# We make a pass for legacy 'Class' based things when a MimeType was not
		# sent in (so we found the Class object, not the MimeType).
		# This is potentially as small security hole, but the things that are blocked are
		# not found by Class at this time.
		raise hexc.HTTPForbidden("Cannot create that type of object:" + str(factory))

	return factory

_user_sensitive_factory_finder.find_factory = _user_sensitive_factory_finder


@interface.implementer(ext_interfaces.IExternalizedObjectFactoryFinder)
def _user_sensitive_factory_finder_factory( externalized_object ):
	return _user_sensitive_factory_finder
