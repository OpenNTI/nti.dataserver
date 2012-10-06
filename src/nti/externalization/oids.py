#!/usr/bin/env python
"""
Functions for externalizing OIDs.
$Revision$
"""
from __future__ import print_function, absolute_import, unicode_literals

import six
import collections

from zope import component

from zope.container._zope_container_contained import isProxy as _isContainedProxy
from zope.container._zope_container_contained import getProxiedObject as _getContainedProxiedObject
from zope.proxy import removeAllProxies

from zope.security.management import system_user

from ZODB.interfaces import IConnection
from zc import intid as zc_intid

from nti.ntiids import ntiids
from . import integer_strings

def toExternalOID( self, default=None, add_to_connection=False, add_to_intids=False ):
	"""
	For a persistent object, returns its persistent OID in a pasreable
	external format (see :func:`fromExternalOID`). If the object has not been saved, and
	`add_to_connection` is `False` (the default) returns the `default`.

	:param add_to_connection: If the object is persistent but not yet added to a connection,
		setting this to true will attempt to add it to the nearest connection in
		its containment tree, thus letting it have an OID.
	:param add_to_intids: If we can obtain an OID for this object, but it does
		not have an intid, and an intid utility is available, then if this is
		``True`` (not the default) we will register it with the utility.
	"""
	oid = None
	if hasattr( self, 'toExternalOID' ):
		oid = self.toExternalOID( )
	elif hasattr(self, '_p_oid'):
		oid = getattr( self, '_p_oid' )
		jar = None
		if not oid and add_to_connection:
			try:
				jar = IConnection(self)
				jar.add( self )
				oid = getattr( self, '_p_oid' )
			except Exception as e:
				pass

		if oid:
			# The object ID is defined to be 8 charecters long. It gets
			# padded with null chars to get to that length; we strip
			# those out. Finally, it probably has chars that
			# aren't legal it UTF or ASCII, so we go to hex and prepend
			# a flag, '0x'
			oid = oid.lstrip(b'\x00')
			oid = '0x' + oid.encode('hex')
			jar = jar or getattr( self, '_p_jar', None )
			if jar:
				db_name = jar.db().database_name
				oid = oid + ':' + db_name.encode( 'hex' )

			intutility = component.queryUtility( zc_intid.IIntIds )
			if intutility:
				intid = intutility.queryId( self )
				if not intid and add_to_intids:
					intid = intutility.register( self )
				if intid is not None:
					if not jar:
						oid = oid + ':' # Ensure intid is always the third part
					oid = oid + ':' + integer_strings.to_external_string( intid )
	return oid or default

to_external_oid = toExternalOID

ParsedOID = collections.namedtuple('ParsedOID', ['oid', 'db_name', 'intid'] )

def fromExternalOID( ext_oid ):
	"""
	Given a string, as produced by :func:`toExternalOID`, parses it into its
	component parts.


	:param string ext_oid: As produced by :func:`toExternalOID`.

	:return: A three-tuple: ``(oid, dbname, intid)`` (:class:`ParsedOID`). Only the
		OID is guaranteed to be present; the other fields may be empty (``db_name``)
		or `None` (``intid``).

	"""
	# But, for legacy reasons, we accept directly the bytes given
	# in _p_oid, so we have to be careful with our literals here
	# to avoid Unicode[en|de]codeError
	__traceback_info__ = ext_oid
	parts = ext_oid.split( b':' ) if b':' in ext_oid else (ext_oid,)
	oid_string = parts[0]
	name_s = parts[1] if len(parts) > 1 else b""
	intid_s = str(parts[2]) if len(parts) > 2 else None

	# Translate the external format if needed
	if oid_string.startswith( b'0x' ):
		oid_string = oid_string[2:].decode( 'hex' )
		name_s = name_s.decode( 'hex' )
	# Recall that oids are padded to 8 with \x00
	oid_string = oid_string.rjust( 8, b'\x00' )
	__traceback_info__ = ext_oid, oid_string, name_s, intid_s
	if intid_s is not None:
		intid = integer_strings.from_external_string( intid_s )
	else:
		intid = None

	return ParsedOID( oid_string, name_s, intid )

from_external_oid = fromExternalOID

_ext_ntiid_oid = object()
def to_external_ntiid_oid( contained, default_oid=_ext_ntiid_oid, add_to_connection=False, add_to_intids=False ):
	"""
	:return: An NTIID string utilizing the object's creator and persistent
		id.
	:param default_oid: The default value for the externalization of the OID.
		If this is None, and no external OID can be found (using :func:`toExternalOID`),
		then this function will return None. (If not given, this method will return some non-persistent value)
	:param add_to_connection: If the object is persistent but not yet added to a connection,
		setting this to true will attempt to add it to the nearest connection in
		its containment tree, thus letting it have an OID.
	"""
	# We really want the external OID, but for those weird time we may not be saved we'll
	# allow the ID of the object, unless we are explicitly overridden
	# TODO: can we replace the contained proxy specific logic with the generic methods
	# from zope.proxy? zope.proxy.removeAllProxies?
	if _isContainedProxy(contained):
		contained = _getContainedProxiedObject( contained )
	contained = removeAllProxies( contained )
	oid = toExternalOID( contained,
						 default=(default_oid if default_oid is not _ext_ntiid_oid else str(id(contained))),
						 add_to_connection=add_to_connection,
						 add_to_intids=add_to_intids )
	if not oid:
		return None

	creator = getattr( contained, 'creator', system_user.id )
	return ntiids.make_ntiid( provider=(creator
										if isinstance( creator, six.string_types )
										else getattr( creator, 'username', system_user.id )),
								specific=oid,
								nttype=ntiids.TYPE_OID )
