import os
import sys
import argparse

from server_tests_runner import runner

def main(args = None):
	
	if not args:
		args = sys.argv[1:]
		
	parser = argparse.ArgumentParser(prog='Intergration Tests')
	parser.add_argument('-uc', '--use_coverage', help='use coverage', action='store_true', default = False)
	parser.add_argument('-cr', '--coverage_report', help='create coverage report', action='store_true', default = False)
	opts = parser.parse_args(args)

	use_coverage = True if opts.use_coverage else False
	coverage_report = True if opts.coverage_report else False
	
	dirname = os.path.dirname( __file__ )
	dirname = dirname or '.'
	runner( path = os.path.join( dirname, "servertests/integration"), use_coverage=use_coverage, coverage_report=coverage_report)

if __name__ == '__main__':
	main()
