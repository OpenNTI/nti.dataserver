from __future__ import print_function, unicode_literals

from zope import component

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

import logging
logger = logging.getLogger( __name__ )

@component.adapter( nti_interfaces.IModeledContent, nti_interfaces.IObjectFlaggedEvent )
def flag_object( obj, event ):
	username = event.username
	entity = Entity.get_entity(username)
	if entity is not None:
		pass