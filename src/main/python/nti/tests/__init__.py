""" Tests for the dataserver. """

import os
import subprocess
import sys

def main():
	dirname = os.path.dirname( __file__ )
	if not dirname:
		dirname = '.'
	pardirname = os.path.join( dirname, '..' )
	pardirname = os.path.abspath( pardirname )
	for moddir in os.listdir( pardirname ):
		testfile = os.path.join( pardirname, moddir, 'tests', '__main__.py' )
		if os.path.exists( testfile ):
			print testfile
			env = dict(os.environ)
			path = list(sys.path)
			path.insert( 0, pardirname )
			env['PYTHONPATH'] = os.path.pathsep.join( path )
			subprocess.call( [sys.executable, testfile], env=env )

if __name__ == '__main__':
	main()

