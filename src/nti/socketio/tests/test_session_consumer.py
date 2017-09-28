#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import contains
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property

from zope import component
from zope import interface

from nti.chatserver import _handler as chat_handler

from nti.chatserver.interfaces import IChatserver

from nti.chatserver import messageinfo

from nti.dataserver.users.users import User

from nti.socketio.dataserver_session import Session

from nti.socketio.interfaces import ISocketIOSocket
from nti.socketio.interfaces import ISocketEventHandler
from nti.socketio.interfaces import SocketEventHandlerClientError

from nti.socketio.protocol import SocketIOProtocolFormatter1

from nti.socketio.session_consumer import SessionConsumer
from nti.socketio.session_consumer import UnauthenticatedSessionError

from nti.dataserver.tests import mock_dataserver


class MockSocketIO(object):

    def __init__(self):
        # verification
        self.data = []
        self.acks = []
        self.events = []
        self.args = None
        # mocking
        self.session = self
        self.owner = 'MockOwner'
        self.session_id = 'MockSessionId'
        self.handler = None
        self.internalize_function = None

    def send_event(self, name, *args):
        SocketIOProtocolFormatter1().make_event(name, *args)
        self.events.append((name, args))

    def send(self, data):
        self.data.append(data)

    def ack(self, mid, data):
        SocketIOProtocolFormatter1().make_ack(mid, data)
        self.acks.append((mid, data))

    def new_protocol(self, unused_h=None): 
        return self
    socket = property(new_protocol)

    def incr_hits(self): pass


class TestSessionConsumer(mock_dataserver.DataserverLayerTest):

    cons = None
    handler = None
    socket = None

    def setUp(self):
        super(TestSessionConsumer, self).setUp()
        self.cons = SessionConsumer()
        self.evt_handlers = {'chat': [self]}
        
        def _handlers(*unused_args):
            return self.evt_handlers
        self.cons._create_event_handlers = _handlers
        self.socket = MockSocketIO()

    def test_bad_messages(self):
        assert_that(self.cons(self.socket, None),  # Socket death
                    is_(False))
        assert_that(self.cons(self.socket, {}),  # Non-'event'
                    is_(False))
        assert_that(self.cons(self.socket, {'type': 'event'}),  # unhandled
                    is_(False))

    def test_unauth_session(self):
        with self.assertRaises(UnauthenticatedSessionError):
            Session().queue_message_from_client(None)

    def test_create_event_handlers(self):
        # There's no IChatserver registered, so this is all you get
        interface.alsoProvides(self.socket, ISocketIOSocket)

        @component.adapter(ISocketIOSocket)
        @interface.implementer(ISocketEventHandler)
        class MockChat(object):

            def __init__(self, sock):
                self.socket = sock

        class MockChatServer(object):
            pass
        o = MockChatServer()
        interface.directlyProvides(o, IChatserver)
        # NOTE: This is slightly unsafe in the shared configuration and might
        # leak
        component.provideUtility(o)
        component.provideSubscriptionAdapter(MockChat)

        del self.cons._create_event_handlers
        handlers = self.cons._create_event_handlers(self.socket)
        assert_that(handlers, has_entry('', has_item(is_(MockChat))))

        MockChat.event_prefix = 'chat'
        self.cons._create_event_handlers.invalidate(self.cons, self.socket)
        handlers = self.cons._create_event_handlers(self.socket)

        assert_that(handlers, has_entry('chat', has_item(is_(MockChat))))

        component.getGlobalSiteManager().unregisterUtility(o)

    def _auth_user(self):
        User.create_user(self.ds, username=u'foo@bar')

    @mock_dataserver.WithMockDSTrans
    def test_auth_user(self):
        self._auth_user()

    def test_kill(self):

        class X(object):
            pass

        class Y(object):
            destroyed = False
            def destroy(self): 
                self.destroyed = True

        y = Y()
        self.evt_handlers = {'chat': [X()], 'y': [y]}

        self.cons.kill(self.socket)
        assert_that(y, has_property('destroyed', True))

    @mock_dataserver.WithMockDSTrans
    def test_send_non_default_input_data(self):
        # Authenticate
        self._auth_user()

        class X(object):
            im_class = None
            obj = None
            theEvent = None
        x = X()
        # Make the event handler look like a bound
        # method of another class

        def theEvent(obj):
            x.obj = obj
        theEvent.im_class = chat_handler._ChatHandler
        x.theEvent = theEvent
        self.evt_handlers['chat'] = [x]
        self.cons(self.socket, {'type': 'event',
                                'name': 'chat_theEvent',
                                'args': ({'Class': 'MessageInfo', 'Creator': u'foo', 'body': [u'baz']},)})

        assert_that(x.obj, is_(messageinfo.MessageInfo))

    @mock_dataserver.WithMockDSTrans
    def test_namespace_event(self):
        # Authenticate
        self._auth_user()

        # Dispatch chat event
        def h(arg):
            self.socket.args = arg
        self.handler = h
        self.cons(self.socket, {'type': 'event',
                                'name': 'chat_handler', 'args': ("The arg",)})

        assert_that(self.socket, has_property('args', 'The arg'))

    @mock_dataserver.WithMockDSTrans
    def test_ack_event(self):
        # Authenticate
        self._auth_user()

        # Dispatch chat event
        def h(arg):
            self.socket.args = arg
            return "The result"

        self.handler = h
        self.cons(self.socket, {'id': "1", 'type': 'event',
                                'name': 'chat_handler', 'args': ("The arg",)})

        assert_that(self.socket, has_property('args', 'The arg'))
        assert_that(self.socket.acks, contains(('1', ["The result"])))

    @mock_dataserver.WithMockDSTrans
    def test_exception_event(self):
        # Authenticate
        self._auth_user()

        # Dispatch chat event
        def h(arg):
            raise ValueError("The error")

        self.handler = h
        self.cons(self.socket, {'type': 'event',
                                'name': 'chat_handler', 'args': ("The arg",)})

        assert_that(self.socket.events, 
                    contains(('server-error', 
                              ('{"code": "ValueError", "error-type": "server-error", "message": "The error"}',))))

    @mock_dataserver.WithMockDSTrans
    def test_ack_event_exception(self):
        # Authenticate
        self._auth_user()

        # Dispatch chat event
        def h(arg):
            raise SocketEventHandlerClientError("A client error")

        self.handler = h
        self.cons(self.socket, {'id': "1", 'type': 'event',
                                'name': 'chat_handler', 'args': ("The arg",)})

        assert_that(self.socket.acks, 
                    contains(('1',
                             [{'error-type': 'client-error', 
                               'message': u'A client error', 
                               'code': 'SocketEventHandlerClientError'}])))
