import os
from server_tests_runner import runner

def main():

	dirname = os.path.dirname( __file__ )
	if not dirname:
		dirname = '.'
	runner( os.path.join( dirname,  "servertests/generalpurpose") )

if __name__ == '__main__':
	main()
