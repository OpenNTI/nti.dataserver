#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from zope.preference.interfaces import IPreferenceGroup

from zope.traversing.interfaces import IContainmentRoot

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class PreferencesNamespace(object):

    def __init__(self, ob, request):
        self.context = ob

    def traverse(self, name, ignore):
        root_group = IPreferenceGroup(self.context)
        root_group = root_group.__bind__(self.context)
        root_group.__name__ = '++preferences++'
        interface.alsoProvides(root_group, IContainmentRoot)
        return name and root_group[name] or root_group
