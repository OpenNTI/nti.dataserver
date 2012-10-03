#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces defining the invitation system. The key class for
creating and working with invitations is :class:`IInvitation`.
The key class for registering, querying and responding to invitations is :class:`IInvitations`.
An implementation of this class should be registered as a persistent utility in the site.

$Id$
"""

# Regarding existing work: There's a Plone product, but it's very specific to plone and works
# only for initial registration.

# There's z3ext.principal.invite, which is interesting and possibly applicable,
# but doesn't seem to be available anymore. Some inspiration from it, though.
# See http://pydoc.net/z3ext.principal.invite/0.4.0/z3ext.principal.invite.interfaces

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import interface
from zope.interface.interfaces import ObjectEvent, IObjectEvent
from zope import schema

from zope.schema import ValidationError

from zope.annotation import interfaces as an_interfaces
from nti.dataserver import interfaces as nti_interfaces
from zope.container import interfaces as cnt_interfaces



class IInvitation(cnt_interfaces.IContained,
				  nti_interfaces.ICreated,
				  nti_interfaces.ILastModified,
				  an_interfaces.IAnnotatable):
	"""
	An invitation from one user of the system (or the system itself)
	for another user to be able to do something.

	Invitations are initially created and registered with an
	:class:`IInvitations` utility. At some time in the future, someone
	who was invited may accept the invitation. The process of
	accepting the invitation is considered to run at the credential
	level of the creator of the invitation (thus allowing accepting
	the invitation to do things like join a group of the creator).

	Invitations may expire after a period of time and/or be good for only
	a certain number of uses. They may have a predicate that determines they are
	applicable only to certain users (for example, a list of invited users).
	"""

	# TODO: What descriptive properties, if any?
	code = interface.Attribute( "A unique code that identifies this invitation within its IInvitations container." )

	def accept( user ):
		"""
		TODO
		"""

class IObjectInvitation(IInvitation):
	"""
	An invitation relating to a specific object.
	"""

	object_int_id = interface.Attribute('The global intid for the object the invitation refers to.')
	object = interface.Attribute('Object')

class IInvitations(interface.Interface):

	def registerInvitation(invitation):
		"""
		Registers the given invitation with this object. This object is responsible for
		assigning the invitation code and taking ownership of the invitation.
		"""

	# def removeObject(id):
	# 	""" remove invitations for object """

	# def getInvitationsByObject(object, type=None):
	# 	""" invitations by object """

	# def getInvitationsByOwner(owner, type=None):
	# 	""" invitations by owner """

	# def getInvitationsByPrincipal(principal, type=None):
	# 	""" invitations by principal """

	# def search(**kw):
	# 	""" search invitations """


class IInvitationEvent(IObjectEvent):
	"""
	An event specifically about an invitation.
	"""
	object = schema.Object(IInvitation,
						   title="The invitation." )


class IInvitationAcceptedEvent(IInvitationEvent):
	"""
	An invitation has been accepted.
	"""
	user = schema.Object(nti_interfaces.IUser,
						 title="The user that accepted the invitation." )


@interface.implementer(IInvitationAcceptedEvent)
class InvitationAcceptedEvent(ObjectEvent):
	pass

class InvitationValidationError(ValidationError):
	"""
	A problem relating to the validity of an attempted action on
	an invitation.
	"""

class InvitationCodeError(InvitationValidationError):
	__doc__ = _('The invitation code is not valid.')


class InvitationExpiredError(InvitationValidationError):
	__doc__ = _('The invitation code has expired.')
