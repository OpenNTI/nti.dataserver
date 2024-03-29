#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces supporting socket.io

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from zope.annotation.interfaces import IAnnotatable

from zope.configuration.fields import Bool

from zope.interface.common.mapping import IFullMapping

from zope.interface.common.interfaces import IStandardError

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from zope.schema import Int
from zope.schema import Field
from zope.schema import Choice
from zope.schema import Object
from zope.schema import TextLine

# pylint: disable=E0213,E0211

_socket_base = None
_writer_base = interface.Interface
_reader_base = interface.Interface


class ISocketIOMessage(IFullMapping):
    """
    A message read or written to socket io.
    """
    msg_type = Int(description=u"The numeric value of the message type, from 0 to 8",
                   readonly=True)


class ISocketIOProtocolFormatter(interface.Interface):
    """
    Functions for formatting messages appropriately for socket io.
    """

    def make_event(name, *args):
        """
        """

    def make_heartbeat():
        """ """

    def make_noop():
        """
        """

    def make_ack(msg_id, params):
        """ """

    def make_connect(data):
        """
        """

    def decode(data):
        """
        :return: A single :class:`ISocketIOMessage` object.
        """

    def decode_multi(data):
        """
        :return: A sequence of Message objects
        """

    def encode_multi(messages):
        """
        :param messages: A sequence of strings that have already been according
                to methods like :meth:`make_event`.
        :return: A byte string. If there was more than one message, this will be a framed
                string. Otherwise, it will be equivalent to the first object in messages.
        """


class ISocketIOWriter(_writer_base):
    """
    Defines the write-side of a socket (the ability to send messages to a client)
    """

    # externalize_function = schema.Field(
    # 	description="The function used to externalize data to send to the client. Defaults to creating strings of JSON.",
    # 	readonly=True)

    def ack(msg_id, params):
        """
        Sends an acknowledgment to a previously received message.
        This is the socket.io "client-handled" acknowledgement and is delivered
        to the waiting client callback.

        :param msg_id: The message ID to acknowledge. Arrived as the `id` field
                of an incoming message.
        :param params: The data to send with the acknowledgement. Will be externalized
                to a string.
        """

    def send(message):
        """
        Sends arbitrary message data to the connected client, or another client.

        :param message: The exact string of data to send. In general, this
                method should not be invoked by clients.
        """

    def send_event(name, *args):
        """
        Sends a named event with structured arguments to the connected client.

        :param string name: The name of the event to send.
        :param args: The arguments the client's event handler should get, in order.
                Will be externalized to strings using the externalize_function.
        """


class ISocketIOReader(_reader_base):
    """
    The read-side of a socket to a connected client.
    """

    # def receive():
    # 	"""
    # 	Waits for an incoming message and returns it.
    # 	"""


class ISocketIOSocket(ISocketIOReader, ISocketIOWriter):
    """
    A socket to a connected client that can be used to read and write messages.
    """


class ISocketIOTransport(interface.Interface):
    """
    The low-level interface that handles sending and receiving messages.
    An :class:`ISocketIOSocket` may have many different transports over its
    lifetime.
    """

    def connect(session, request_method):
        """
        Given a (newly-created) session and a WSGI request, connect the session
        to this transport.

        This method may be called to reconnect an already established session
        to a different transport during transport fallback.

        :return: This may return an iterable of greenlets; if so, then they must be joined
                on for the transport to run to completion before the WSGI request completes. It may instead return an
                :class:`pyramid.interfaces.IResponse` if the transport is synchronous, and that
                response is the value to be immediately returned to the client, terminating the
                WSGI request.
        """

    def kill():
        """
        Requests that this transport terminate any ongoing communication.
        """


class ISocketIOChannel(interface.Interface):
    """
    Something that represents a queued connection between client
    and server. A channel is a bidirectional stream of messages; no interpretation
    of the messages is done (the messages are strings of bytes).
    """

    def queue_message_from_client(msg):
        """
        A message, ``msg``, has arrived at the server and is ready to
        be processed.
        """

    def queue_message_to_client(msg):
        """
        A message, ``msg``, is ready to be sent to the remote client.
        """


SESSION_STATE_NEW = u"NEW"
SESSION_STATE_CONNECTED = u"CONNECTED"
SESSION_STATE_DISCONNECTING = u"DISCONNECTING"
SESSION_STATE_DISCONNECTED = u"DISCONNECTED"


class ISocketSession(ISocketIOChannel, IAnnotatable):
    """
    A higher-level abstraction on top of io channels containing some state.

    Because storing state with the session may be generally useful and is
    also distributed throughout the system, sessions are intended to be annotatable;
    implementations should probably be :class:`zope.annotation.interfaces.IAttributeAnnotatable`
    """

    heartbeat_is_transactional = Bool(
        u"Do you have to commit the transaction to update the heartbeat/disconnect time?")

    connected = Bool(title=u'Is the session known to be connected to a client?')

    owner = TextLine(title=u'The name of the user that owns this session.')

    socket = Object(ISocketIOSocket,
        			title=u"The :class:`ISocketIOSocket` this session is connected with")

    state = Choice(title=u"The state of the session",
                   values=(
                      SESSION_STATE_NEW, SESSION_STATE_CONNECTED,
                      SESSION_STATE_DISCONNECTING, SESSION_STATE_DISCONNECTED
                   ),
                   default=SESSION_STATE_NEW)

    def heartbeat():
        pass

    def kill(send_event=True):
        """
        Mark this session as disconnected if not already.

        :param bool send_event: If ``True`` (the default) when this method
                actually marks the session as disconnected, and the session had a valid
                owner, an :class:`SocketSessionDisconnectedEvent` will be sent.
        """


class ISocketSessionEvent(IObjectEvent):
    """
    An event fired relating to a socket session.
    In general, socket events will only be fired for sockets that have owners.
    """


class ISocketSessionConnectedEvent(IObjectEvent):
    """
    An event that is fired when a socket session establishes a connection for the first time.
    """


class ISocketSessionDisconnectedEvent(ISocketSessionEvent):
    """
    An event that is fired when a socket session disconnects.
    """


@interface.implementer(ISocketSessionEvent)
class SocketSessionEvent(interface.interfaces.ObjectEvent):
    pass


@interface.implementer(ISocketSessionConnectedEvent)
class SocketSessionConnectedEvent(SocketSessionEvent):
    pass


@interface.implementer(ISocketSessionDisconnectedEvent)
class SocketSessionDisconnectedEvent(SocketSessionEvent):
    pass


class ISocketSessionCreatedObjectEvent(IObjectEvent):
    """
    An event fired when a socket session is creating objects and preparing
    to distribute them to :class:`ISocketEventHandler` instances. This fires
    *before* any object events fired by the handlers or the process of
    updating the object from external data. Listeners for this event can
    use it to establish constraints and invariants around the incoming object, such
    as security proxying it.
    """

    session = Object(ISocketSession,
					 title=u"The session doing the creating.")

    message = Object(ISocketIOMessage,
					 title=u"The message being processed.")

    external_object = interface.Attribute(
        "The object value that will update the created object.")


@interface.implementer(ISocketSessionCreatedObjectEvent)
class SocketSessionCreatedObjectEvent(ObjectEvent):

    session = None
    message = None
    external_object = None

    def __init__(self, object, session=None, message=None, external_object=None):
        super(SocketSessionCreatedObjectEvent, self).__init__(object)
        self.session = session
        self.message = message
        self.external_object = external_object


class ISocketSessionClientMessageConsumer(interface.Interface):
    """
    A low-level event handler for messages that arrive on a socket
    from a client. In general, there may be one of these associated with a session,
    and it will decide how to handle client messages. The typical implementation,
    found in :mod:`nti.socketio.session_consumer` will route events as documented
    in :class:`ISocketEventHandler`.
    """

    def __call__(session, message):
        """
        Handle the ``message`` that has arrived from the client. Generally, this
        method should not raise un-retryable exceptions so that a
        transaction wrapped around this method can commit.

        :param session: The :class:`ISocketSession` that received the message.
        :param message: An :class:`ISocketIOMessage`.
        :return: Undefined.
        """


class ISocketEventHandler(interface.Interface):
    """
    Interface for things that want to handle socket
    events received from a connected user.

    The general contract for these objects is that they will have
    public methods corresponding to the events they wish to handle from
    the user. If the method returns a result that is not None, then if the
    user requested acknowledgement that result will be sent as the ack (if
    the user requested ack and the result was None, False will be returned).
    See :class:`ISocketEventHandlerClientError` for a description of error handling.

    These objects may be registered as subscription adapters for
    :class:`socketio.interfaces.ISocketIOSocket`. If there is duplication
    among the handlers for a particular event, all will be called in no
    defined order; the last non-None result will be used for ack.

    These object should generally not expect to store state beyond the current
    event's lifetime.

    """

    event_prefix = Field(
        title=u'If present, names the prefix which should be subtracted from all incoming events before searching for a handler.',
        description=u'For example, a prefix of chat and a method name of handle would match an event chat_handle',
        required=False)

    def destroy(session):
        """
        Adapters may optionally implement this method to be informed
        when the session is being killed.
        TODO: This should be a separate interface or event.
        """


class ISocketEventHandlerClientError(IStandardError):
    """
    Marker interface for exceptions that may optionally be raised
    by methods of an :class:`ISocketEventHandler`.

    If any registered handler raises an exception of any kind, no
    further handlers will be called, and the work done by all handlers
    up to that point will be rolled back using a savepoint.

    If the exception raised provides this interface, then the problem is
    due to client error, not a server bug or error (i.e., this is like an
    HTTP 40X response, as opposed to an HTTP 50X response). In that
    case, the object will be formatted in a specific way for sending to the client
    to let them know; otherwise a generic "server error" will be sent.

    In any case, if the client has requested an ACK for the message being processed,
    then the exception data is sent as the ack. Otherwise, it's sent as a generic
    event.
    """


@interface.implementer(ISocketEventHandlerClientError)
class SocketEventHandlerClientError(StandardError):
    """
    Default convenience implementation of :class:`ISocketEventHandlerClientError`.
    """


class ISocketSessionSettings(interface.Interface):
    """
    A configuration object to return socket session settings.
    """

    SessionCleanupAge = Int(title=u"Session cleanup age",
                            description=u"How old inactive sessions have to be before they are removed",
                            default=0,
                            required=False)

    SessionPingFrequency = Int(title=u"Session ping frequency",
                               description=u"How often the server pings the client",
                               default=5,
                               required=False)

    SessionServerHeartbeatUpdateFrequency = Int(title=u"Session heartbeat frequency update",
                                                description=u"How often the server updates session state when pinged",
                                                default=60,
                                                required=False)

    SessionServerHeartbeatTimeout = Int(title=u"Server heartbeat timeout",
                                        description=u"How long a client is silent (no pings) before we consider them inactive",
                                        default=120,
                                        required=False)
