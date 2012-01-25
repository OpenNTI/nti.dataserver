#!/usr/bin/env /opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin/python

import os
import sys
import socket
import threading
import subprocess
import SocketServer
from datetime import datetime

import zdaemon.zdctl
from ZEO import runzeo

import coverage
from coverage.execfile import run_python_file

import app
from nti.dataserver import _daemonutils
from nti.dataserver import _PubSubDevice

##########################

_main_pid = None
_proc_coverage = None
_socket_server = None
_main_socket_port = 6060
_pids_file_name = 'coverage_run_pids.txt'
_crontroller_pids = 'controller_pids.txt'

COVERAGE_PATH = "/opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin/coverage"

##########################

def _clean(path):
	if path.endswith( '.pyc' ):
		path = path[0:-1]
	return path

def _clean_args(args):
	for i,a in enumerate(args or []):
		if _clean(a) == _clean(__file__):
			return args[i+1:]
	return args
		
##########################
	
def _get_rcfile():
	rcfile = 'ds_coverage_run.cfg'
	if not os.path.exists(rcfile):
		rcfile = os.path.join(os.path.dirname(__file__), '_coverage_run.cfg')
	return rcfile

def _create_and_start_coverage():
	global _proc_coverage
	
	_stop_and_save_coverage()
	
	rcfile = _get_rcfile()	
	_proc_coverage = coverage.coverage(config_file=rcfile)
	_proc_coverage.start()
	
def _stop_and_save_coverage():
	
	global _proc_coverage
	
	if _proc_coverage:
		try:
			_proc_coverage.stop()
			_proc_coverage.save()
			return True
		except:
			pass
	return False
	
def _start_coverage():
	global _proc_coverage
	
	try:
		_proc_coverage.start()
	except:
		_create_and_start_coverage()
	
def _report_coverage(do_html=True, do_xml=False):
	
	global _proc_coverage
	
	dt = datetime.now()
	s = "ds.%s.%s" % (os.getpid(), dt.strftime("%Y%m%d.%H%M"))
	
	if do_html:
		try:
			out_path = s + ".html"
			_proc_coverage.html_report(directory=out_path, ignore_errors=True)
		except:
			pass
	
	if do_xml:
		try:
			out_path = s + ".xml"
			_proc_coverage.xml_report(outfile=out_path, ignore_errors=True)
		except:
			pass
		
##########################

def _save_coverage_data_handler(request=None):
	result = _stop_and_save_coverage()
	
	if os.getpid() == _main_pid:
		for pid, ip, port in _read_pids_file():		
			if pid != _main_pid:
				result = _send_message(ip, port, "save") and result
				
	return result
				
def _start_coverage_data_handler(request=None):
	
	_start_coverage()
			
	if os.getpid() == _main_pid:
		for pid, ip, port in _read_pids_file():		
			if pid != _main_pid:
				_send_message(ip, port, "start")
			
def _combine_coverage_data_handler(request=None):
	result = True
	if os.getpid() == _main_pid:
		result = _save_coverage_data_handler(request)
		args = [COVERAGE_PATH, 'combine', "--rcfile=%s" % _get_rcfile()]
		result = subprocess.call(args) == 0 and result
	return result

def _report_coverage_data_handler(request=None, restart=True, do_html=True, do_xml=False):
	
	if os.getpid() == _main_pid:
		if _combine_coverage_data_handler(request):
					
			rcfile = _get_rcfile()
			
			dt = datetime.now()
			s = "ds." + dt.strftime("%Y%m%d.%H%M")
			
			if do_html:
				try:
					out_path = s + ".html"
					args = [COVERAGE_PATH, 'html', "--directory=%s" % out_path, "--rcfile=%s" % rcfile]
					subprocess.call(args)
				except:
					pass
			
			if do_xml:
				try:
					args = [COVERAGE_PATH, 'xml', "--rcfile=%s" % rcfile ]
					subprocess.call(args)
				except:
					pass
			
			if restart:
				_start_coverage_data_handler(request)
			
	elif _stop_and_save_coverage():
		_report_coverage(do_html, do_xml)
		if restart:
			_start_coverage()
		
		
def _stop_handler(request=None, save = True, report = True):
	"""
	stop the main process
	"""
	
	if report:
		_report_coverage_data_handler(request, False)
	elif save:
		_save_coverage_data_handler(request)
	
	if os.getpid() == _main_pid:
		_safe_server_shutdown()
		os.kill(os.getpid(), 2)
	
def _terminate_handler(request=None, report = True, save=True):
	"""
	tries to terminate all processes
	"""

	if os.getpid() == _main_pid:
		if report:
			_report_coverage_data_handler(request, False)
		elif save:
			_save_coverage_data_handler(request)
	
		for pid, ip, port in _read_pids_file():		
			if pid != _main_pid:
				_send_message(ip, port, "terminate")
			
	_safe_server_shutdown()
	os.kill(os.getpid(), 2)
			
##########################

def _read_pids_file(reverse = False, target_file=_pids_file_name):
	
	if not os.path.exists(target_file):
		return []
		
	with open(target_file, "r") as f:
		lines = f.readlines()
		
	if reverse:
		lines.reverse()
	
	result = []		
	for line in lines:
		pid, ip, port = line.split(":")
		result.append((int(pid), ip, int(port)))
		
	return result

def _terminate_from_file(source):
	result = _read_pids_file(source)
	for pid, ip, port in list(result):
		if port > 0:
			if _send_message(ip, port, 'terminate'):
				result.pop(0)
		else:
			try:
				os.kill(pid, 2)
				result.pop(0)
			except:
				pass
		
	return result
			
def _reset_pids_file():
	
	result = _terminate_from_file(_pids_file_name)
	
	with open( _pids_file_name, 'w+' ) as f:	
		for pid, ip, port in result:
			if _send_message(ip, port):
				s = "%s:%s:%s" % (pid, ip, port)
				print >> f, s
				
	with open( _crontroller_pids, 'w+' ) as f:
		pass
		
def _save_proc_info(ip=None, port=0, args=[], target_file=None):
	
	ip = ip or 'localhost'
	target_file = target_file or _pids_file_name
	
	with open( target_file, 'a+' ) as f:
		s = "%s:%s:%s" % (os.getpid(), ip, port)
		print >> f, s
	
	with open("ds.%s.pid" % os.getpid(), "w+") as f:
		s = "%s,%s" % (os.getpid(),  ' '.join(args or []))
		print >> f, s
		
##########################
	
def is_daemonutils(arg):
	return _clean(_daemonutils.__file__) == _clean(arg)

def is_zdaemon(arg):
	return _clean(zdaemon.zdctl.__file__) == _clean(arg)

def is_runzeo(arg):
	return _clean(runzeo.__file__) == _clean(arg)

def is_pubsubdevice(arg):
	return _clean(_PubSubDevice.__file__) == _clean(arg)

def is_app(arg):
	return _clean(app.__file__) == _clean(arg)

def is_traceable(arg):
	return not is_zdaemon(arg) or is_app(arg)

##########################
	
class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		data = self.request.recv(1024)
		if data == 'stop':
			_stop_handler(self.request)
		elif data == 'start':
			_start_coverage_data_handler(self.request)
		elif data == 'terminate-and-report':
			_terminate_handler(self.request, report=True)
		elif data == 'terminate':
			_terminate_handler(self.request, report=False)
		elif data == 'save':
			_save_coverage_data_handler(self.request)
		elif data == 'report':
			_report_coverage_data_handler(self.request)
		elif data == '0':
			pass
	
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	pass

def _set_socket_server(port = 0):
	global _socket_server
	_socket_server = ThreadedTCPServer(("localhost", port), ThreadedTCPRequestHandler)
	server_thread = threading.Thread(target=_socket_server.serve_forever)
	server_thread.daemon = True
	server_thread.start()
	return _socket_server.server_address
	
def _send_message(ip, port, message='0'):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		sock.connect((ip, port))
		sock.send(message)
		return True
	except:
		return False
	finally:
		sock.close()

def _safe_server_shutdown():
	global _socket_server
	if _socket_server:
		try:
			_socket_server.shutdown()
		except:
			pass
		
##########################

def main(args = None):
	
	global _main_pid
	
	if not args:
		args = sys.argv[1:]
	
	# make sure this file is not in the args	
	args = _clean_args(args)
		
	if args:
			
		# get the python file to run
				
		port = 0
		py_source = args[0]
		py_source_args = args[1:]
		
		if is_app(py_source):
			port = _main_socket_port
			os.chmod(__file__, 0755)
			_main_pid = os.getpid()
			_reset_pids_file()
			
		if is_traceable(py_source):
			ip, port = _set_socket_server(port)
			_save_proc_info(ip, port, args)
			_create_and_start_coverage()
		
		if is_zdaemon(py_source) or is_pubsubdevice(py_source):
			_save_proc_info(args=args, target_file=_crontroller_pids)
			
		try:
			if is_daemonutils(py_source):
				_daemonutils._run_main(args=py_source_args)
			elif is_pubsubdevice(py_source):
				_PubSubDevice.__main__(*py_source_args)
			elif is_zdaemon(py_source):
				zdaemon.zdctl.main(args=py_source_args)
			elif is_runzeo(py_source):
				runzeo.main(args=args[1:])
			elif is_app(py_source):
				sys.executable = _clean(__file__)
				app.main()
			else:
				run_python_file(py_source, args=py_source_args)
		except:
			pass
	
		print '%s exit' % os.getpid()	
			
if __name__ == '__main__':
	main()
	

