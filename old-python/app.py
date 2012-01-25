#!/usr/bin/env python2.7

# FIXME: For reasons that aren't completely clear,
# this interferes with chat, specifically, access to
# just-created sessions. It's as if transactions don't
# get committed in a timely fashion...perhaps the zrpc
# greenlet doesn't get a chance to run? This is true
# both here and with python -m gevent.monkey ...
# With a great deal of care, it should be possible to get ZEO/zrpc
# imported and running and then patch (i.e., save a copy of the
# modules locally in those modules.)
#import gevent.monkey
#gevent.monkey.patch_all()

import logging
if __name__ == '__main__':
	logging.basicConfig( level=logging.WARN )
	logging.getLogger( 'nti' ).setLevel( logging.DEBUG )


import nti.appserver.standalone
def main():
	nti.appserver.standalone.run_main()

if __name__ == '__main__':
	main()

