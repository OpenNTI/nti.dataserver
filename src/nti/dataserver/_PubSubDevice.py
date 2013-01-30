#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A simple deamon to run a ZMQ Pub/Sub device. Both socket
sides are in 'bind' mode and accept connections from
arbitrary producers/consumers.

This is deprecated now in favor of Redis Pub/Sub, but the entry
point must remain for compatibility with existing configs.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import os

try:
	from gevent_zeromq import zmq # If things crash, remove core.so
	from zmq.devices import Device
except ImportError:
	zmq = None
	Device = None


def __main__( flag_file, pub_addr, sub_addr ):
	if zmq is None or Device is None:
		print( "ZMQ not installed, exiting.")
		return

	with open( flag_file, 'w' ) as f:
		print( os.getpid, file=f )

	try:
		pd = Device( zmq.FORWARDER, zmq.SUB, zmq.PUB )
		pd.setsockopt_in( zmq.SUBSCRIBE, "" )
		pd.bind_in( sub_addr )
		pd.bind_out( pub_addr )
		pd.start()
	finally:
		os.remove( flag_file )


def main():
	__main__( sys.argv[1], sys.argv[2], sys.argv[3] )

if __name__ == '__main__':
	main()
