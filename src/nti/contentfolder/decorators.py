#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
... $Id: decorators.py 113941 2017-05-31 22:36:04Z carlos.sanchez $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.contentfolder.interfaces import INamedContainer

from nti.externalization.interfaces import IExternalObjectDecorator

from nti.externalization.singleton import Singleton

logger = __import__('logging').getLogger(__name__)


@component.adapter(INamedContainer)
@interface.implementer(IExternalObjectDecorator)
class _NamedContainerDecorator(Singleton):

    def decorateExternalObject(self, original, external):
        external['name'] = original.filename
