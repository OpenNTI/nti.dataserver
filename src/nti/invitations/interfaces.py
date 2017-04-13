#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces defining the invitation system. The key class for
creating and working with invitations is :class:`IInvitation`.
The key class for registering, querying and responding to invitations is :class:`IInvitations`.
An implementation of this class should be registered as a persistent utility in the site.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.annotation.interfaces import IAnnotatable

from zope.container.constraints import contains

from zope.container.interfaces import IContainer
from zope.container.interfaces import IContained

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from zope.schema import ValidationError

from zope.security.management import system_user

from nti.base.interfaces import ICreated
from nti.base.interfaces import ILastModified

from nti.invitations import MessageFactory as _

from nti.property.property import alias

from nti.schema.field import Bool
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import ValidText
from nti.schema.field import ValidTextLine

SYSTEM_USER_NAME = getattr(system_user, 'title').lower()

class IInvitation(IContained,
                  ICreated,
                  ILastModified):
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

    code = ValidTextLine(title="A unique code that identifies this invitation.",
                         required=False)

    receiver = ValidTextLine(title="Invitation receiver (username or email).",
                             required=True)

    sender = ValidTextLine(title="Invitation sender.",
                           required=True, default=SYSTEM_USER_NAME)

    message = ValidText(title="Invitation message.", required=False)

    accepted = Bool(title="Accepted flag.", default=False, required=True)

    expiryTime = Number(title="The expiry timestamp.", 
                        required=True,
                        default=0)

    sent = Number(title="The sent timestamp.", required=False)
    sent.setTaggedValue('_ext_excluded_out', True)

    def is_email():
        """
        Returns true if the receiver is an email address
        """

    def is_expired():
        """
        Returns true if this invitation has expired
        """

    def is_accepted():
        """
        Returns true if the invitation has been accepted
        """


class IInvitationsContainer(IContained,
                            IContainer,
                            IAnnotatable):
    """
    A central registry of invitations. Intended to be used as a utility registered
    for the site.
    """
    contains(str('.IInvitation'))

    def add(invitation):
        """
        Registers the given invitation with this object. This object is responsible for
        assigning the invitation code and taking ownership of the invitation.
        """
    registerInvitation = add

    def remove(invitation):
        """
        Remove the given invitation with this object.
        """
    removeInvitation = remove

    def get_invitation_by_code(code):
        """
        Returns an invitation having the given code, or None if there is no
        such invitation.
        """
    getInvitationByCode = get_invitation_by_code

IInvitations = IInvitationsContainer  # BWC


class IInvitationEvent(IObjectEvent):
    """
    An event specifically about an invitation.
    """
    object = Object(IInvitation, title="The invitation.")


class IInvitationSentEvent(IInvitationEvent):
    """
    An invitation has been sent.
    """
    user = interface.Attribute("The user to whom the invitation is sent.")


@interface.implementer(IInvitationSentEvent)
class InvitationSentEvent(ObjectEvent):

    receiver = alias('user')

    def __init__(self, obj, user):
        super(InvitationSentEvent, self).__init__(obj)
        self.user = user


class IInvitationAcceptedEvent(IObjectModifiedEvent, IInvitationEvent):
    """
    An invitation has been accepted.
    """
    user = interface.Attribute("The user that accepted the invitation.")


@interface.implementer(IInvitationAcceptedEvent)
class InvitationAcceptedEvent(ObjectModifiedEvent):

    def __init__(self, obj, user):
        super(InvitationAcceptedEvent, self).__init__(obj)
        self.user = user


class InvitationValidationError(ValidationError):
    """
    A problem relating to the validity of an attempted action on
    an invitation.
    """

    def __init__(self, invitation=None):
        super(InvitationValidationError, self).__init__()
        self.invitation = invitation


class InvitationCodeError(InvitationValidationError):
    __doc__ = _('The invitation is not valid.')
    i18n_message = __doc__


class InvitationExpiredError(InvitationValidationError):
    __doc__ = _('The invitation has expired.')
    i18n_message = __doc__


class InvitationAlreadyAcceptedError(InvitationValidationError):
    __doc__ = _('Invitation already accepted.')
    i18n_message = __doc__


class InvitationActorError(InvitationValidationError):
    __doc__ = _('The invitation does not have actor.')
    i18n_message = __doc__


class IInvitationActor(interface.Interface):
    """
    An interface for a utility to act on an invitation
    """

    def accept(user, invitation):
        """
        Perform whatever action is required for the ``user`` to accept the invitation, including
        validating that the user is actually allowed to accept the invitation. Typically
        this means that this method has side effects.

        :param user User being invited
        :param invitation invitation object
        :return None/False if invitation was not accepted

        Once the invitation has been accepted, this should notify an :class:`IInvitationAcceptedEvent`.

        :raises InvitationExpiredError: If the invitation has expired.
        """
