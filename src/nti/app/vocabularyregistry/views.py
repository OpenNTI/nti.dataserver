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

from zope.component.hooks import site as current_site

from zope.event import notify

from zope.schema.interfaces import IVocabulary

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.vocabularyregistry.traversal import VocabulariesPathAdapter
from nti.app.vocabularyregistry.vocabulary import Term as SimpleTerm
from nti.app.vocabularyregistry.vocabulary import Vocabulary as SimpleVocabulary

from nti.app.vocabularyregistry.utils import install_named_utility

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.site import unregisterUtility

from nti.site.interfaces import IHostPolicyFolder

from nti.traversal.traversal import find_interface

logger = __import__('logging').getLogger(__name__)


class VocabularyViewMixin(object):

    def _raise_error(self, message, error=hexc.HTTPUnprocessableEntity):
        raise_json_error(self.request,
                         error,
                         { 'message': message, },
                         None)

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
        """
        Here we don't do any dedup or sorting, just keep what they are,
        and will raise error if duplicated terms happen when initializing the vocabulary,
        Since we don't know which position the duplicated term should be.
        """
        terms = self._params.get('terms')
        if not isinstance(terms, (list or tuple)):
            self._raise_error(u'terms should be an array of strings.')

        _res = []
        for x in terms:
            if not isinstance(x, basestring) or not x.strip():
                self._raise_error(u"'%s' is not non-empty string." % x)
            _res.append(x.strip())

        # Allow empty terms for now.
        #if not _res:
        #    self._raise_error("terms can not be empty.")

        return _res

    def _get_local_utility(self, name, iface, site, site_manager=None):
        site_manager = site_manager or site.getSiteManager()
        obj = component.queryUtility(iface, name=name, context=site)
        if obj is None or getattr(obj, '__parent__', None) != site_manager:
            return None
        return obj

    def register_vocabulary(self, name, terms, site_manager):
        obj = SimpleVocabulary([SimpleTerm(x) for x in terms])
        install_named_utility(obj,
                              utility_name=name,
                              provided=IVocabulary,
                              local_site_manager=site_manager)
        return obj

    def unregister_vocabulary(self, name, site, site_manager=None, iface=IVocabulary):
        site_manager = site_manager or site.getSiteManager()
        obj = self._get_local_utility(name, iface,
                                      site=site,
                                      site_manager=site_manager)
        if obj is not None:
            del site_manager[obj.__name__]
            unregisterUtility(site_manager,
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
    Should always unregister the existing vocabulary,
    and re-register a new one in appropriate site.
    """
    def __call__(self):
        name = self.context.__name__
        terms = self._get_terms()
        current_terms = set(x.token for x in self.context)
        new_term_set = set(terms)
        logger.info("Updating vocabulary (added=%s) (removed=%s)",
                    sorted(new_term_set - current_terms),
                    sorted(current_terms - new_term_set))

        target_site = find_interface(self.context, IHostPolicyFolder)
        with current_site(target_site):
            site_manager = target_site.getSiteManager()
            self.unregister_vocabulary(name,
                                       site=target_site,
                                       site_manager=site_manager)
            try:
                vocabulary = self.register_vocabulary(name, terms, site_manager)
                notify(ObjectModifiedFromExternalEvent(vocabulary))
                return vocabulary
            except ValueError as e:
                self._raise_error(str(e))


# Disable the deletion view for now.
#@view_config(route_name='objects.generic.traversal',
#             renderer='rest',
#             request_method='DELETE',
#             permission=nauth.ACT_DELETE,
#             context=IVocabulary)
class VocabularyDeleteView(AbstractAuthenticatedView,
                           VocabularyViewMixin):
    """
    Delete this IVocabulary if it was created in the current site.
    """
    def __call__(self):
        name = self.context.__name__
        target_site = find_interface(self.context, IHostPolicyFolder)
        with current_site(target_site):
            site_manager = target_site.getSiteManager()
            self.unregister_vocabulary(name,
                                       site=target_site,
                                       site_manager=site_manager)
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


@view_config(route_name='objects.generic.traversal',
             renderer='templates/vocab_list.pt',
             request_method='GET',
             permission=nauth.ACT_UPDATE,
             context=VocabulariesPathAdapter)
class VocabularyListView(AbstractAuthenticatedView):

    def _search(self):
        val = self.request.params.get('search') or ''
        val = val.strip()
        return val.lower() if val else None

    def _predicate(self, vocab_name, search=None):
        return not search or search in vocab_name.lower()

    def get_items(self, search=None):
        currentSiteManager = component.getSiteManager()
        items = []
        total = 0
        for x in component.getUtilitiesFor(IVocabulary):
            total += 1
            if not self._predicate(x[0], search):
                continue

            parent = getattr(x[1], '__parent__', None)
            persisted = bool(parent is not None)
            inherited = bool(parent is not None and parent is not currentSiteManager)
            items.append({'name': x[0],
                          'total_terms': len(x[1]),
                          'href': self.request.resource_url(self.context, x[0], '@@details'),
                          'editable': persisted,
                          'inherited': inherited})
        return (items, total)

    def __call__(self):
        search = self._search()
        items, total = self.get_items(search=search)
        items = sorted(items, key=lambda x: x['name'])
        return {'vocabularies': items,
                'search': search or '',
                'raw_url': self.request.resource_url(self.context),
                'Total': total,
                'ItemCount': len(items)}


@view_config(route_name='objects.generic.traversal',
             renderer='templates/vocab_details.pt',
             request_method='GET',
             permission=nauth.ACT_UPDATE,
             context=IVocabulary,
             name="details")
class VocabularyDetailsView(AbstractAuthenticatedView):

    def __call__(self):
        policy = find_interface(self.context, IHostPolicyFolder)
        siteManager = policy.getSiteManager()
        save_link = self.request.resource_url(self.context) if self.context.__parent__ is siteManager else None
        list_link = self.request.resource_url(siteManager, 'Vocabularies')
        terms = [x for x in self.context]
        return {'name': self.context.__name__,
                'terms': terms,
                'total_terms': len(terms),
                'list_link': list_link,
                'save_link': save_link}
