from unittest import defaultTestLoader
from unittest import TextTestRunner
from servertests.server import DataserverProcess

def runner(path, pattern="test*.py", use_coverage=False, coverage_report=False):
	
	suite = defaultTestLoader.discover(path, pattern)
	dsprocess = DataserverProcess()
	try:
		if use_coverage:
			dsprocess.startServerWithCoverage()
		else:
			dsprocess.startServer()
		
		runner = TextTestRunner(verbosity=2)
		for test in suite:
			runner.run(test)
			break
			
	finally:
		if use_coverage:
			dsprocess.terminateServerWithCoverage(report = coverage_report)
		else:
			dsprocess.terminateServer()
