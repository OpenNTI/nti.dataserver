
from nti.tests import verifiably_provides
from nti.socketio import protocol
from nti.socketio import interfaces

from hamcrest import assert_that

def test_protocol_provides():
	assert_that( protocol.SocketIOProtocol( None ), verifiably_provides( interfaces.ISocketIOSocket ) )
