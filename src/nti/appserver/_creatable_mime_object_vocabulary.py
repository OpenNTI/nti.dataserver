#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implements vocabularies that limit what a user can create.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface
from zope import deferredimport

from zope.schema.interfaces import IVocabularyFactory

from pyramid import httpexceptions as hexc

from pyramid.threadlocal import get_current_request

from nti.appserver import MessageFactory as _

from nti.dataserver.users.users import User

from nti.externalization.interfaces import IExternalizedObjectFactoryFinder

from nti.externalization.internalization import default_externalized_object_factory_finder

logger = __import__('logging').getLogger(__name__)


deferredimport.initialize()
deferredimport.deprecatedFrom(
    "Moved to nti.dataserver.vocabulary",
    "nti.dataserver.vocabulary",
    "_CreatableMimeObjectVocabulary",
    "_SimpleRestrictedContentObjectFilter",
    "_ImageAndRedactionRestrictedContentObjectFilter",
    "_UserCreatableMimeObjectVocabularyFactory")


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
            logger.debug("Failed to get authenticated userid. If this is not a "
                         "test case, this is a problem")
            auth_user_name = None

        if auth_user_name:
            auth_user = User.get_user(auth_user_name)
            if auth_user:
                name = "Creatable External Object Types"
                factory = component.getUtility(IVocabularyFactory, name)
                vocabulary = factory(auth_user)

    factory = default_externalized_object_factory_finder(ext_object)
    if vocabulary is None or factory is None:
        return factory

    if factory not in vocabulary and component.IFactory.providedBy(factory):
        # If it's not in the vocabulary, don't let it be created.
        # We make a pass for legacy 'Class' based things when a MimeType was not
        # sent in (so we found the Class object, not the MimeType).
        # This is potentially as small security hole, but the things that are blocked are
        # not found by Class at this time.
        msg = _("Cannot create that type of object:") + str(factory)
        raise hexc.HTTPForbidden(msg)
    return factory
_user_sensitive_factory_finder.find_factory = _user_sensitive_factory_finder


@interface.implementer(IExternalizedObjectFactoryFinder)
def _user_sensitive_factory_finder_factory(unused_ext_obj):
    return _user_sensitive_factory_finder
