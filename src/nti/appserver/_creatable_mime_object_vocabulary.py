#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implements vocabularies that limit what a user can create.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import component
from zope import interface

from zope.componentvocabulary.vocabulary import UtilityVocabulary

from zope.schema.interfaces import IVocabularyFactory

from pyramid import httpexceptions as hexc
from pyramid.threadlocal import get_current_request

from nti.dataserver.users import User

from nti.externalization.interfaces import IMimeObjectFactory
from nti.externalization.interfaces import IExternalizedObjectFactoryFinder
from nti.externalization.internalization import default_externalized_object_factory_finder

from .interfaces import ICreatableObjectFilter

# TODO: zope.schema.vocabulary provides a vocab registry
# Should we make use of that? Especially since these registries
# can be ZCA utilities

class _CreatableMimeObjectVocabulary(UtilityVocabulary):
	"""
	A vocabulary that reports the names (MIME types) of installed
	:class:`nti.externalization.interfaces.IMimeObjectFactory` objects.
	"""
	nameOnly = False
	interface = IMimeObjectFactory

	def __init__(self, context):
		super(_CreatableMimeObjectVocabulary, self).__init__(context)
		for subs in component.subscribers((context,), ICreatableObjectFilter):
			self._terms = subs.filter_creatable_objects(self._terms)

@interface.implementer(ICreatableObjectFilter)
class _SimpleRestrictedContentObjectFilter(object):

	RESTRICTED = ('application/vnd.nextthought.canvasurlshape',  # images
				  'application/vnd.nextthought.redaction',
				  'application/vnd.nextthought.friendslist',
				  'application/vnd.nextthought.media',
				  'application/vnd.nextthought.embeddedaudio',
				  'application/vnd.nextthought.embeddedmedia',
				  'application/vnd.nextthought.embeddedvideo',
				  'application/vnd.nextthought.forums.ace')

	def __init__(self, context=None):
		pass

	def filter_creatable_objects(self, terms):
		for name in self.RESTRICTED:
			terms.pop(name, None)
		return terms

@interface.implementer(ICreatableObjectFilter)
class _ImageAndRedactionRestrictedContentObjectFilter(_SimpleRestrictedContentObjectFilter):

	RESTRICTED = ('application/vnd.nextthought.canvasurlshape',  # images
				  'application/vnd.nextthought.redaction',
				  'application/vnd.nextthought.media',
				  'application/vnd.nextthought.embeddedaudio',
				  'application/vnd.nextthought.embeddedmedia',
				  'application/vnd.nextthought.embeddedvideo',
				  'application/vnd.nextthought.forums.ace')

@interface.implementer(IVocabularyFactory)
class _UserCreatableMimeObjectVocabularyFactory(object):

	def __init__(self):
		pass

	def __call__(self, user):
		return _CreatableMimeObjectVocabulary(user)

@interface.implementer(IExternalizedObjectFactoryFinder)
def _user_sensitive_factory_finder(ext_object):
	vocabulary = None

	# TODO: This process is probably horribly expensive and should be cached
	# install zope.testing hook to clean up the cache
	request = get_current_request()
	if request:
		try:
			auth_user_name = request.authenticated_userid
		except AssertionError:
			# Some test cases call us with bad header values, causing
			# repoze.who.api.request_classifier and paste.httpheaders to incorrectly
			# blow up
			logger.debug("Failed to get authenticated userid. If this is not a test case, this is a problem")
			auth_user_name = None

		if auth_user_name:
			auth_user = User.get_user(auth_user_name)
			if auth_user:
				name = "Creatable External Object Types"
				vocabulary = component.getUtility(IVocabularyFactory, name)(auth_user)

	factory = default_externalized_object_factory_finder(ext_object)
	if vocabulary is None or factory is None:
		return factory

	if factory not in vocabulary and component.IFactory.providedBy(factory):
		# If it's not in the vocabulary, don't let it be created.
		# We make a pass for legacy 'Class' based things when a MimeType was not
		# sent in (so we found the Class object, not the MimeType).
		# This is potentially as small security hole, but the things that are blocked are
		# not found by Class at this time.
		raise hexc.HTTPForbidden(_("Cannot create that type of object:") + str(factory))

	return factory

_user_sensitive_factory_finder.find_factory = _user_sensitive_factory_finder

@interface.implementer(IExternalizedObjectFactoryFinder)
def _user_sensitive_factory_finder_factory(externalized_object):
	return _user_sensitive_factory_finder
