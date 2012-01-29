#!/usr/bin/env python2.7

"""
A simple deamon to run a Pub/Sub device. Both socket
sides are in 'bind' mode and accept connections from
arbitrary producers/consumers.
"""

import os

from gevent_zeromq import zmq # If things crash, remove core.so

from zmq.devices import Device

def __main__( flag_file, pub_addr, sub_addr ):

	with open( flag_file, 'w' ) as f:
		print >> f, os.getpid()

	try:
		pd = Device( zmq.FORWARDER, zmq.SUB, zmq.PUB )
		pd.setsockopt_in( zmq.SUBSCRIBE, "" )
		pd.bind_in( sub_addr )
		pd.bind_out( pub_addr )
		pd.start()
	finally:
		os.remove( flag_file )


def main():
	import sys
	__main__( sys.argv[1], sys.argv[2], sys.argv[3] )

if __name__ == '__main__':
	main()




