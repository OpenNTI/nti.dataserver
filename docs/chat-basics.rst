===============================
 Realtime Communication Basics
===============================

Realtime communication for clients of the dataserver is accomplished
through the use of `SocketIO`_. This handles all the transport level
details, leaving only the higher protocols to us. All clients of the
dataserver are expected to establish and maintain a SocketIO session
using their user credentials. Particular protocols may have other
initialization requirements before they can be used
(in particular, see the :doc:`chat-protocol`).

In general, all protocols are specified in terms of SocketIO events
carrying JSON object payloads. The other SocketIO communication
primitives are not used. Protocols define a family of events all
having the same prefix (SocketIO namespaces are not used). Events can
be unprovoked from dataserver to client, or unprovoked from client to
server; some of those events return a value from the server to the
client. For those events documented as returning something, you must
request acknowledgment of the event. The return value will be
delivered in the ack to the message ID assigned to the event. (In
javascript, you need merely supply a callback function to `emit` to
make this happen; the callback will receive the return value.)

.. _SocketIO: http://socket.io
