# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML; helpers for registering factories
for QTI types.

$Id$
"""
from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import inspect

from zope import interface
from ZODB import loglevels
from zope.configuration import fields
from zope.component.factory import Factory
from zope.component import zcml as component_zcml

from .basic.elements import QTIElement
from . import interfaces as qti_interfaces

@interface.implementer(qti_interfaces.IQTIObjectFactory)
class _QTIObjectFactory(Factory):
	"""
	A factory meant to be registered as a named utility.
	"""

def _item_predicate(item):
	implemented = getattr(item, '__implemented__', None)
	implemented = implemented.flattened() if implemented else ()
	return 	inspect.isclass(item) and issubclass(item, QTIElement) and item != QTIElement and \
			qti_interfaces.IConcrete in implemented
			
class IRegisterInternalizationQTIFactoriesDirective(interface.Interface):
	"""
	The arguments needed for registering factories.
	"""
	module = fields.GlobalObject(title="Module to scan for QTI factories to add", required=True)
	
def registerQTIFactories(_context, module ):
	for name, item  in  inspect.getmembers(module, _item_predicate):
		__traceback_info__ = name, item

		key = name.lower()
		logger.log( loglevels.TRACE, "Registered QTI factory utility %s = %s (%s)", name, item, key)
		component_zcml.utility( _context,
								provides=qti_interfaces.IQTIObjectFactory,
								component=_QTIObjectFactory( item, interfaces=list(interface.implementedBy(item)) ),
								name=key )
