#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interface definitions relating to capabilities.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.security import interfaces as zsec_interfaces

class ICapability(zsec_interfaces.IPermission):
	"""
	A capability is a type of umbrella permission. Although it is an
	actual permission, it is not typically used directly in an ACL; rather,
	it is checked and applied at a higher level. A single capability
	may imply several other permissions or it may not directly imply any.

	Capabilities and permissions share the same namespace, so be careful
	to avoid collisions.

	"""

#: A :class:`zope.schema.interfaces.IVocabularyTokenized` vocabulary
#: will be available as a registered vocabulary under this name
VOCAB_NAME = 'nti.appserver.capabilities.vocabulary'
