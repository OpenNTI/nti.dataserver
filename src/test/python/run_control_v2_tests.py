import os
from server_tests_runner import runner

def main():
	runner(os.path.dirname( __file__ ) + "/servertests/control/v2")

if __name__ == '__main__':
	main()
