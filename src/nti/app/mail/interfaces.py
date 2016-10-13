#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.externalization.representation import WithRepr

from nti.schema.field import Bool
from nti.schema.field import ValidText
from nti.schema.field import ValidTextLine as TextLine
from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties

class IEmail(interface.Interface):
	"""
	A generic email object.
	"""
	Copy = Bool(title="Whether the email author will receive a copy.",
				default=False)

	NoReply = Bool(title="Whether the email will have a NoReply reply address",
				   default=False)

	Subject = TextLine(title="The subect line of the email.", required=False)

	Body = ValidText(title="The body of the message.", required=True)

@WithRepr
@interface.implementer(IEmail)
class Email(SchemaConfigured):
	createDirectFieldProperties(IEmail)

	__external_class_name__ = "Email"
	mime_type = mimeType = 'application/vnd.nextthought.email'
