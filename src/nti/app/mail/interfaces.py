#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from zope import interface

from nti.externalization.representation import WithRepr

from nti.schema.field import Bool
from nti.schema.field import ValidText
from nti.schema.field import ValidTextLine as TextLine

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured


class IEmail(interface.Interface):
    """
    A generic email object.
    """
    Copy = Bool(title=u"Whether the email author will receive a copy.",
                default=False)

    NoReply = Bool(title=u"Whether the email will have a NoReply reply address",
                   default=False)

    Subject = TextLine(title=u"The subect line of the email.", required=False)

    Body = ValidText(title=u"The body of the message.", required=True)


@WithRepr
@interface.implementer(IEmail)
class Email(SchemaConfigured):
    createDirectFieldProperties(IEmail)

    __external_class_name__ = "Email"
    mime_type = mimeType = 'application/vnd.nextthought.email'
