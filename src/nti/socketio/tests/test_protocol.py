#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

from nti.testing.matchers import verifiably_provides

import six

from nti.socketio.interfaces import ISocketIOSocket

from nti.socketio.protocol import JsonMessage
from nti.socketio.protocol import EventMessage
from nti.socketio.protocol import ConnectMessage
from nti.socketio.protocol import MessageMessage
from nti.socketio.protocol import SocketIOSocket
from nti.socketio.protocol import HeartbeatMessage
from nti.socketio.protocol import DisconnectMessage
from nti.socketio.protocol import SocketIOProtocolFormatter1

from nti.testing.base import AbstractTestBase


def test_protocol_provides():
    assert_that(SocketIOSocket(None),
                verifiably_provides(ISocketIOSocket))


class TestSocketIOProtocolFormatter1(AbstractTestBase):

    def setUp(self):
        self.protocol = SocketIOProtocolFormatter1()

    def test_makes_return_bytes(self):
        assert_that(self.protocol.make_event('name'), is_(str))
        assert_that(self.protocol.make_heartbeat(), is_(str))
        assert_that(self.protocol.make_noop(), is_(str))
        assert_that(self.protocol.make_ack('1', []), is_(str))
        assert_that(self.protocol.make_connect(''), is_(str))

    def test_make_invalid_event(self):
        with self.assertRaises(ValueError):
            self.protocol.make_event('')

        with self.assertRaises(ValueError):
            self.protocol.make_event(1)

        with self.assertRaises(ValueError):
            self.protocol.make_event('connect')

    def test_decode_disconnect(self):
        assert_that(self.protocol.decode('0::'),
                    is_(DisconnectMessage))
        assert_that(self.protocol.decode(b'0::'),
                    is_(DisconnectMessage))

    def _to_decode(self, s):
        if six.PY2:
            return (s, six.text_type(s), s.encode("utf-8"))
        else:
            return (s, s.encode("utf-8"))

    def test_decode_connect(self):
        for s in self._to_decode('1::tail'):
            msg = self.protocol.decode(s)
            assert_that(msg, is_(ConnectMessage))
            assert_that(msg, has_entry('data', 'tail'))

    def test_decode_heartbeat(self):
        for s in self._to_decode('2::tail'):
            msg = self.protocol.decode(s)
            assert_that(msg, is_(HeartbeatMessage))
            assert_that(msg, has_length(0))

    def test_decode_message(self):
        for s in self._to_decode('3:::data'):
            msg = self.protocol.decode(s)
            assert_that(msg, is_(MessageMessage))
            assert_that(msg, has_entry('data', 'data'))

    def test_decode_json(self):
        for decoder in (self.protocol.decode, lambda x: self.protocol.decode_multi(x)[0]):
            for s in self._to_decode('4:::{}'):
                msg = decoder(s)
                assert_that(msg, is_(JsonMessage))
                assert_that(msg, has_length(0))

    def test_decode_json_unicode(self):
        for decoder in (self.protocol.decode, lambda x: self.protocol.decode_multi(x)[0]):
            for s in (b'4:::{"str": "\xc3\xb6"}', ):  # umlaut o
                msg = decoder(s)
                assert_that(msg, is_(JsonMessage))
                assert_that(msg, has_length(1))

    def test_decode_event(self):
        for decoder in (self.protocol.decode, lambda x: self.protocol.decode_multi(x)[0]):
            for s in self._to_decode('5:::{"name": "foo", "args": []}'):
                msg = decoder(s)
                assert_that(msg, is_(EventMessage))
                assert_that(msg, has_entry('type', 'event'))
                assert_that(msg, has_entry('name', 'foo'))
                assert_that(msg, has_length(3))

            for s in self._to_decode('5:1+::{"name": "foo", "args": []}'):
                msg = decoder(s)
                assert_that(msg, is_(EventMessage))
                assert_that(msg, has_entry('type', 'event'))
                assert_that(msg, has_entry('name', 'foo'))
                assert_that(msg, has_length(4))
                assert_that(msg, has_entry('id', '1+'))

    def test_decode_exceptions(self):
        with self.assertRaises(ValueError) as cm:
            self.protocol.decode('')

        assert_that(cm.exception.args[0], is_('Must provide data'))

        with self.assertRaises(ValueError) as cm:
            self.protocol.decode(u'5:1+::{"args": []}')
        assert_that(cm.exception.args[0], is_('Improper event, missing name'))

        with self.assertRaises(ValueError) as cm:
            self.protocol.decode(u'5:1+::{"name": "foo"}')
        assert_that(cm.exception.args[0], is_('Improper event, missing args'))

        with self.assertRaises(ValueError) as cm:
            self.protocol.decode(u'5:1+::{"name": "connect"}')
        assert_that(cm.exception.args[0], is_('Improper event, reserved name'))

        with self.assertRaises(ValueError) as cm:
            self.protocol.decode('9')
        assert_that(cm.exception.message, is_('Unknown message type'))
        assert_that(cm.exception.args, is_(('Unknown message type', '9')))

    def test_decode_multi(self):
        ucode = u'5:1+::{"name": "foo", "args": []}'
        unicode_framed = u'\ufffd' + unicode(len(ucode)) + u'\ufffd' + ucode

        def decode(framed):
            msgs = self.protocol.decode_multi(framed)

            assert_that(msgs, has_length(1))
            msg = msgs[0]
            assert_that(msg, is_(EventMessage))
            assert_that(msg, has_entry('name', 'foo'))

        decode(unicode_framed)

        bts = b'5:1+::{"name": "foo", "args": []}'
        byte_framed = b'\xef\xbf\xbd' + str(len(bts)).encode('utf-8') + b'\xef\xbf\xbd' + bts
        decode(byte_framed)

        # Too short a length
        with self.assertRaises(ValueError):
            byte_framed = b'\xef\xbf\xbd' + b'5' + b'\xef\xbf\xbd' + bts
            decode(byte_framed)

        # Too long a length
        with self.assertRaises(ValueError):
            byte_framed = b'\xef\xbf\xbd' + str(len(bts) + 5).encode('utf-8') \
                        + b'\xef\xbf\xbd' + bts
            decode(byte_framed)

    def test_encode_multi(self):
        # A single item
        ucode = u'5:1+::{"name": "foo", "args": []}'
        assert_that(self.protocol.encode_multi([ucode]),
                    is_(ucode))

        # Multiple items
        unicode_framed = u'\ufffd' + unicode(len(ucode)) + u'\ufffd' + ucode
        bte_framed = unicode_framed.encode('utf-8')
        assert_that(self.protocol.encode_multi([ucode, ucode]),
                    is_(bte_framed + bte_framed))
