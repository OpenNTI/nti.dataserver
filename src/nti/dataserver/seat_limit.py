from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.dataserver.interfaces import ISeatLimit

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

logger = __import__('logging').getLogger(__name__)

@interface.implementer(ISeatLimit)
class AbstractSeatLimit(SchemaConfigured):

    createDirectFieldProperties(ISeatLimit)
