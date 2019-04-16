#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_renderers_edit_link_decorator import EditLinkDecorator

from nti.app.vocabularyregistry import VIEW_VOCABULARY_VALUE_ADD
from nti.app.vocabularyregistry import VIEW_VOCABULARY_VALUE_REMOVE

from nti.dataserver.authorization import is_admin

from nti.dataserver.vocabularyregistry.interfaces import IVocabularyItem

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.links.links import Link

logger = __import__('logging').getLogger(__name__)


@component.adapter(IVocabularyItem)
@interface.implementer(IExternalMappingDecorator)
class _VocabularyLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, result):
        return bool(self._is_authenticated and is_admin(self.remoteUser))

    def _do_decorate_external(self, context, result):
        links = result.setdefault(StandardExternalFields.LINKS, [])
        for rel in (VIEW_VOCABULARY_VALUE_ADD,
                    VIEW_VOCABULARY_VALUE_REMOVE):
            link = Link(context,
                        rel=rel,
                        method='POST',
                        elements=('@@%s' % rel,))
            links.append(link)
