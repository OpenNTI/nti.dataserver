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

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.schema.interfaces import IVocabulary

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.vocabularyregistry import MessageFactory as _
from nti.app.vocabularyregistry.vocabulary import Term as SimpleTerm
from nti.app.vocabularyregistry.vocabulary import Vocabulary as SimpleVocabulary

from nti.app.vocabularyregistry.utils import install_named_utility

from nti.dataserver import authorization as nauth

from nti.site import unregisterUtility


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

    def _get_local_utility(self, name, iface):
        obj = component.queryUtility(iface, name=name, context=self.site)
        if obj is None or getattr(obj, '__parent__', None) != self.site_manager:
            return None
        return obj

    def register_vocabulary(self, name, terms):
        obj = SimpleVocabulary([SimpleTerm(x) for x in terms])
        install_named_utility(obj,
                              utility_name=name,
                              provided=IVocabulary,
                              local_site_manager=self.site_manager)
        return obj

    def unregister_vocabulary(self, name, iface=IVocabulary):
        obj = self._get_local_utility(name, iface)
        if obj is not None:
            del self.site_manager[obj.__name__]
            unregisterUtility(self.site_manager,
                              obj,
                              iface,
                              name=name)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='PUT',
             permission=nauth.ACT_UPDATE,
             context=IVocabulary)
class VocabularyUpdateView(AbstractAuthenticatedView,
                           ModeledContentUploadRequestUtilsMixin,
                           VocabularyViewMixin):
    """
    Replace the current vocabulary if it was created in the current site,
    otherwise create a new vocabulary for the current site.
    """
    def __call__(self):
        if self.context.__parent__ is not self.site_manager:
            self._raise_error(_("Only vocabulary created in the current site can be updated."), error=hexc.HTTPForbidden)
        name = self.context.__name__
        terms = self._get_terms()
        self.unregister_vocabulary(name)
        vocabulary = self.register_vocabulary(name, terms)
        return vocabulary


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='DELETE',
             permission=nauth.ACT_DELETE,
             context=IVocabulary)
class VocabularyDeleteView(AbstractAuthenticatedView,
                           VocabularyViewMixin):
    """
    Delete this IVocabulary if it was created in the current site.
    """
    def __call__(self):
        if self.context.__parent__ is not self.site_manager:
            self._raise_error(_("Only vocabulary created in the current site can be deleted."), error=hexc.HTTPForbidden)
        name = self.context.__name__
        self.unregister_vocabulary(name)
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
