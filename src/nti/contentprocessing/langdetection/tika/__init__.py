#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from .. import Language

from ..interfaces import ILanguageDetector

from .profile import LanguageProfile

from .identifier import initProfiles
from .identifier import LanguageIdentifier

_profiles_loaded = False
def loadProfiles():
    global _profiles_loaded
    if not _profiles_loaded:
        initProfiles()
        _profiles_loaded = True

@interface.implementer(ILanguageDetector)
class _TikaLanguageDetector(object):

    __slots__ = ()

    def __call__(self, content, **kwargs):
        loadProfiles()
        profile = LanguageProfile(content)
        iden = LanguageIdentifier(profile)
        result = Language(code=iden.language)
        return result
