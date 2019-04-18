#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.schema.interfaces import IVocabulary
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.interfaces import IVocabularyRegistry

from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.vocabularyregistry.factory import DefaultVocabularyFactory

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields


ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


class VocabularyViewMixin(object):

    def _raise_error(self, message, error=hexc.HTTPUnprocessableEntity):
        raise_json_error(self.request,
                         error,
                         { 'message': message, },
                         None)

    @Lazy
    def site(self):
        return getSite()

    @Lazy
    def site_manager(self):
        return self.site.getSiteManager()

    @Lazy
    def _params(self):
        return self.readInput()

    def _get_name(self):
        name = self._params.get('name')
        if isinstance(name, basestring):
            name = name.strip()
            if name:
                return name

        self._raise_error(u'name must be non-empty string.') 

    def _get_terms(self):
        terms = self._params.get('terms')
        if not isinstance(terms, (list or tuple)):
            self._raise_error(u'terms should be an array of strings.')

        _res = []
        for x in terms:
            if not isinstance(x, basestring) or not x.strip():
                self._raise_error(u"'%s' is not non-empty string." % x)
            _res.append(x.strip())

        if not _res:
            self._raise_error("terms can not be empty.")

        return _res

    def create_vocabulary(self, name, terms):
        vocabulary = SimpleVocabulary([SimpleTerm(x) for x in terms])
        vocabulary.__name__ = name
        vocabulary.__parent__ = self.site_manager
        return vocabulary

    def create_vocabulary_factory(self, name):
        factory = DefaultVocabularyFactory()
        factory.__name__ = name
        factory.__parent__ = self.site_manager
        return factory

    def register_vocabulary(self, name, vocabulary):
        self.site_manager.registerUtility(vocabulary,
                                          provided=IVocabulary,
                                          name=name)
        return vocabulary

    def register_vocabulary_factory(self, name, factory):
        self.site_manager.registerUtility(factory,
                                          provided=IVocabularyFactory,
                                          name=name)
        return factory

    def unregister_vocabulary(self, vocabulary):
        self.site_manager.unregisterUtility(vocabulary,
                                            provided=IVocabulary,
                                            name=vocabulary.__name__)

    def unregister_vocabulary_factory(self, factory):
        self.site_manager.unregisterUtility(factory,
                                            provided=IVocabularyFactory,
                                            name=factory.__name__)

    def _get_local_utility(self, name, iface=IVocabulary):
        if not name:
            return None
        obj = component.queryUtility(iface, name=name)
        if obj is not None \
            and getattr(obj, '__name__', None) == name \
            and getattr(obj, '__parent__', None) == self.site_manager:
            return obj
        return None

    def _get_local_vocabulary(self, name):
        return self._get_local_utility(name, iface=IVocabulary)

    def _get_local_vocabulary_factory(self, name):
        return self._get_local_utility(name, iface=IVocabularyFactory)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='POST',
             permission=nauth.ACT_CREATE,
             context=IVocabularyRegistry)
class VocabularyCreationView(AbstractAuthenticatedView,
                             ModeledContentUploadRequestUtilsMixin,
                             VocabularyViewMixin):
    """
    Create and register new IVocabulary and IVocabularyFactory utilities in the current site.
    """

    def _reRegister(self, name, terms):
        # Unregister if possible
        vocabulary = self._get_local_vocabulary(name=name)
        if vocabulary is not None:
            self.unregister_vocabulary(vocabulary)

        factory = self._get_local_vocabulary_factory(name=name)
        if factory is not None:
            self.unregister_vocabulary_factory(factory)

        # Register
        vocabulary = self.create_vocabulary(name=name, terms=terms)
        self.register_vocabulary(name, vocabulary)

        factory = self.create_vocabulary_factory(name=name)
        self.register_vocabulary_factory(name, factory)

        return vocabulary

    def __call__(self):
        name = self._get_name()
        terms = self._get_terms()
        return self._reRegister(name, terms)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='PUT',
             permission=nauth.ACT_UPDATE,
             context=IVocabulary)
class VocabularyUpdateView(VocabularyCreationView):
    """
    Replace the current vocabulary if it was created for the current site,
    otherwise create a new vocabulary for the current site.
    """
    def __call__(self):
        name = getattr(self.context, '__name__', None)
        terms = self._get_terms()
        return self._reRegister(name, terms)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='DELETE',
             permission=nauth.ACT_DELETE,
             context=IVocabulary)
class VocabularyDeleteView(AbstractAuthenticatedView,
                           VocabularyViewMixin):
    """
    Delete this IVocabulary if it was created in the current site,
    otherwise raise 403 forbidden.
    """
    def __call__(self):
        name = getattr(self.context, '__name__', None)

        vocabulary = self._get_local_vocabulary(name=name)
        if vocabulary is None:
            self._raise_error("Only persistent vocabulary that created in current site can be deleted.",
                              error=hexc.HTTPForbidden)
        self.unregister_vocabulary(vocabulary)

        factory = self._get_local_vocabulary_factory(name=name)
        if factory is not None:
            self.unregister_vocabulary_factory(factory)

        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='GET',
             permission=nauth.ACT_READ,
             context=IVocabulary)
class VocabularyGetView(AbstractAuthenticatedView):
    """
    Read an IVocabulary, which may be created in current or its parent site.
    """
    def __call__(self):
        return self.context
