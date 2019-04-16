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

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.vocabularyregistry import VIEW_VOCABULARY_VALUE_ADD
from nti.app.vocabularyregistry import VIEW_VOCABULARY_VALUE_REMOVE

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.vocabularyregistry.interfaces import IVocabularyItem
from nti.dataserver.vocabularyregistry.interfaces import IVocabularyItemContainer

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields


ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='GET',
             permission=nauth.ACT_READ,
             context=IVocabularyItemContainer)
class GetVocabulariesView(AbstractAuthenticatedView):

    def _get_vocabulary_items(self, inherit):
        return [x for x in self.context.iterVocabularyItems(inherit=inherit)]

    def __call__(self):
        inherit = is_true(self.request.params.get('inherit', True))

        result = LocatedExternalDict()
        result.__name__ = self.context.__name__
        result.__parent__ = self.context.__parent__
        result[ITEMS] = items = self._get_vocabulary_items(inherit=inherit)
        result[ITEM_COUNT] = result[TOTAL] = len(items)
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='POST',
             permission=nauth.ACT_CREATE,
             context=IVocabularyItemContainer)
class CreateVocabularyView(AbstractAuthenticatedView,
                           ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        item = self.readCreateUpdateContentObject(self.remoteUser)
        self.request.response.status_int = 201
        try:
            return self.context.add_vocabulary_item(item)
        except KeyError:
            raise_json_error(self.request,
                             hexc.HTTPConflict,
                             {
                                 'message': u'Vocabulary exists.',
                             },
                             None)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='DELETE',
             permission=nauth.ACT_DELETE,
             context=IVocabularyItem)
class DeleteVocabularyView(AbstractAuthenticatedView):

    def __call__(self):
        container = self.context.__parent__
        container.delete_vocabulary_item(self.context)
        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='POST',
             permission=nauth.ACT_UPDATE,
             context=IVocabularyItem,
             name=VIEW_VOCABULARY_VALUE_ADD)
class AddValuesToVocabularyView(AbstractAuthenticatedView,
                                ModeledContentUploadRequestUtilsMixin):

    inputClass = list

    def __call__(self):
        external = self.readInput()
        self.context.add(external)
        return self.context


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='POST',
             permission=nauth.ACT_UPDATE,
             context=IVocabularyItem,
             name=VIEW_VOCABULARY_VALUE_REMOVE)
class RemoveValuesFromVocabularyView(AbstractAuthenticatedView,
                                     ModeledContentUploadRequestUtilsMixin):

    inputClass = list

    def __call__(self):
        external = self.readInput()
        self.context.remove(external)
        return self.context
