#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.schema import TextLine

from zope.viewlet.interfaces import IViewletManager

class INotableDataEmailViewletManager(IViewletManager):
    """
    Viewlet manager for notable data items in the push email.

    This should be a ``ConditionalViewletManager`` to support
    ordering and conditional inclusion of rows.
    """


class INotableDataEmailClassifier(interface.Interface):
    """
    An object that knows how to give a named category
    to some piece of notable data. These should be registered
    as adapters from the particular kind of data they support.

    Typically there should be a viewlet having the same name
    that can render the grouping in the email.
    """

    def classify(notable_data):
        """
        Return the name of the classification for the piece
        of data. If no classification is found, return nothing
        and the object will be ignored.
        """


class IMailTemplateProvider(interface.Interface):

    template = TextLine(title=u"Name of the template to use.")
