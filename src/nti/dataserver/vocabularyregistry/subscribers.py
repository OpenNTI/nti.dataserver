#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=E1101,E1121

from zope import component

from zope.site.interfaces import INewLocalSite

from nti.dataserver.vocabularyregistry.vocabulary import VocabularyItemContainer

from nti.dataserver.vocabularyregistry.interfaces import VOCABULARY_CONTAINER_NAME
from nti.dataserver.vocabularyregistry.interfaces import IVocabularyItemContainer

from nti.site.localutility import install_utility

from nti.site.interfaces import IHostPolicySiteManager

logger = __import__('logging').getLogger(__name__)


@component.adapter(IHostPolicySiteManager, INewLocalSite)
def install_site_vocabulary_container(local_site_manager, unused_event=None):
    container = local_site_manager.get(VOCABULARY_CONTAINER_NAME)
    if container is None:
        logger.info('Installing vocabulary item container (%s)', local_site_manager.__parent__.__name__)
        container = VocabularyItemContainer()
        install_utility(container,
                        VOCABULARY_CONTAINER_NAME,
                        IVocabularyItemContainer,
                        local_site_manager)
    return container
