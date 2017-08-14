#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
... $Id: decorators.py 113941 2017-05-31 22:36:04Z carlos.sanchez $
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.contentfolder.interfaces import INamedContainer

from nti.externalization.interfaces import IExternalObjectDecorator

from nti.externalization.singleton import SingletonDecorator


@component.adapter(INamedContainer)
@interface.implementer(IExternalObjectDecorator)
class _NamedContainerDecorator(object):

    __metaclass__ = SingletonDecorator

    def decorateExternalObject(self, original, external):
        external['name'] = original.filename
