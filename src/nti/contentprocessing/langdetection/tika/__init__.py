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
from .. import interfaces as ld_interfaces

from .profile import LanguageProfile
from .identifier import initProfiles
from .identifier import LanguageIdentifier

@interface.implementer(ld_interfaces.ILanguageDetector)
class _TikaLanguageDetector(object):

    _profiles_loaded = False

    def _load(self):
        if not self._profiles_loaded:
            initProfiles()
            self._profiles_loaded = True

    def __call__(self, content, **kwargs):
        self._load()
        profile = LanguageProfile(content)
        iden = LanguageIdentifier(profile)
        result = Language(code=iden.language)
        return result
