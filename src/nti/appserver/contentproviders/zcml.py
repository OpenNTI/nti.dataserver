#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZCML directives relating to content providers.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.component.zcml import adapter

from zope.configuration import fields

from zope.contentprovider.interfaces import IContentProvider

from nti.appserver.contentproviders.pyramid import PyramidRendererContentProviderFactory

from nti.schema.field import ValidTextLine


class IPyramidRendererDirective(interface.Interface):
    """
    Register a pyramid renderer template as a content provider.
    """

    template = ValidTextLine(
        title=u"The name of the template.",
        required=True,
        min_length=1)

    name = ValidTextLine(
        title=u"The name of the content provider.",
        required=False,
        min_length=1)

    for_ = fields.Tokens(
        title=u"Specifications to be adapted",
        description=u"This should be a list of interfaces or classes",
        required=False,
        value_type=fields.GlobalObject(missing_value=object())
    )


def registerPyramidRenderer(_context, template, name='', for_=None):
    factory = PyramidRendererContentProviderFactory(template)
    adapter(_context, (factory,), provides=IContentProvider, for_=for_, name=name)
