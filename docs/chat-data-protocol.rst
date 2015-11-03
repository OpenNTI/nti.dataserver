====================================
 Data Change Notifications Protocol
====================================

Once a dataserver session is initiated, the client is automatically
enrolled in the ``data_`` protocol namespace. With this protocol, the
server informs the connected client of changes to data it is
interested in.

This protocol defines a single event:


Data Events
-----------

``data_noticeIncomingChange( change )``
  Sent when there is a data change, such as something
  shared with you. The sole argument is a :class:`.IStreamChangeEvent`.
