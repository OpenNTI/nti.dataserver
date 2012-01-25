import os
import sys
import shutil
import argparse

import app
import _coverage_run
		
def main(args = None):
	
	global process
	
	if not args:
		args = sys.argv[1:]
	
	parser = argparse.ArgumentParser(prog='NTI DataServer')
	parser.add_argument('-rc', '--rcfile', help='coverage configuration file')
	ns = parser.parse_args(args)
	
	app_path = os.path.dirname(_coverage_run.__file__)
	ns.rcfile = ns.rcfile or os.path.join(app_path, '_coverage_run.cfg')
	
	if not os.path.exists(ns.rcfile):
		ns.rcfile = os.path.join(app_path, '_coverage_run.cfg')
			
	# copy to temp so subprocesses can use it as a reference
	
	if not os.path.exists(ns.rcfile):
		shutil.copyfile(ns.rcfile, "ds_coverage_run.cfg")
	
	print "Current Process %s" % os.getpid()
	
	_coverage_run.main([app.__file__])
		
if __name__ == '__main__':
	main()

