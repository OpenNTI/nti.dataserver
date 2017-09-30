#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.container.contained import Contained

from zope.traversing.interfaces import IPathAdapter


@interface.implementer(IPathAdapter)
class SAMLPathAdapter(Contained):

    __name__ = 'saml'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context
