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

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields


ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


from nti.site.utils import registerUtility
from nti.site.utils import unregisterUtility
from zope.schema.interfaces import IVocabulary
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm
from zope.component.hooks import getSite
from zope.cachedescriptors.property import Lazy

@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               permission=nauth.ACT_POST,
               context=IDataserverFolder)
class VocabulariesView(AbstractAuthenticatedView,
                       ModeledContentUploadRequestUtilsMixin):

    @Lazy
    def site(self):
        return getSite()

    @Lazy
    def site_manager(self):
        return self.site.getSiteManager()

    @view_config(name="test_add")
    def add_vocabulary(self):
        input = self.readInput()
        name = input['name']
        terms = input['terms']
        
        vocabulary = SimpleVocabulary([SimpleTerm(x) for x in iterms]);from IPython.core.debugger import Tracer;Tracer()()
        self.site_manager.registerUtility(vocabulary,
                                          provided=IVocabulary,
                                          name=name)
        return True


    @view_config(name="test_remove")
    def delete_vocabulary(self):
        name = self.readInput()['name']
        vocabulary = component.queryUtility(IVocabulary, name=name);from IPython.core.debugger import Tracer;Tracer()()
        if vocabulary is not None:
            self.site_manager.unregisterUtility(vocabulary,
                                                provided=IVocabulary,
                                                name=name)
        return True
