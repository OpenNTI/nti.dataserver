#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.base.deprecation import moved


def _patch():
    """
    move old modules that contained persitent objects to their
    new location. DO NOT Remove
    """
    moved("nti.contentsearch._content_utils", "nti.contentsearch._deprecated")
    moved("nti.contentsearch._discriminators", "nti.contentsearch._deprecated")
    moved("nti.contentsearch._indexmanager", "nti.contentsearch._deprecated")
    moved("nti.contentsearch._repoze_index", "nti.contentsearch._deprecated")
    moved("nti.contentsearch._whoosh_schemas", "nti.contentsearch._deprecated")
    moved("nti.contentsearch.content_types", "nti.contentsearch._deprecated")
    moved("nti.contentsearch.discriminators", "nti.contentsearch._deprecated")
    moved("nti.contentsearch.indexmanager", "nti.contentsearch._deprecated")
    moved("nti.contentsearch.repoze_adpater", "nti.contentsearch._deprecated")
    moved("nti.contentsearch.whoosh_schemas", "nti.contentsearch._deprecated")
    moved("nti.contentsearch.whoosh_searcher", "nti.contentsearch._deprecated")
    moved("nti.contentsearch.whoosh_storage", "nti.contentsearch._deprecated")


_patch()
del _patch


def patch():
    pass
