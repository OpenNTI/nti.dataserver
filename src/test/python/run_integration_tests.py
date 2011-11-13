import os
from server_tests_runner import runner

def main():
	dirname = os.path.dirname( __file__ )
	dirname = dirname or '.'
	runner( path = os.path.join( dirname, "servertests/integration"), use_coverage=True)

if __name__ == '__main__':
	main()
