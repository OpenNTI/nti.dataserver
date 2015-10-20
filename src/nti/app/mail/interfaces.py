#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.common.representation import WithRepr

from nti.schema.field import Bool
from nti.schema.field import ValidTextLine as TextLine
from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties

class IEmail(interface.Interface):
	"""
	A generic email object.
	"""
	NoReply = Bool(title="Whether the email will have a NoReply reply address",
				default=False)

	Subject = TextLine(title="The subect line of the email.", required=False)

	Body = TextLine(title="The body of the message.", required=True)

@interface.implementer( IEmail )
@WithRepr
class Email(SchemaConfigured):
	createDirectFieldProperties( IEmail )

	__external_class_name__ = "Email"
	mime_type = mimeType = 'application/vnd.nextthought.email'
