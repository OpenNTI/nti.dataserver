#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A entry point to help us ensure that we are loading rqworkers

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys

from rq import Queue
from rq import Worker
from rq.scripts import rqworker

from redis.exceptions import ConnectionError

from nti.dataserver.utils import run_with_dataserver

class NTIWorker(Worker):
	
	def fork_and_perform_job(self, job):
		"""
		perform the actual work and passes it a job w/o a fork
		"""
		self._horse_pid = os.getpid()
		self.main_work_horse(job)
		
	def main_work_horse(self, job):
		self._is_horse = True
		self.log = logger
		success = self.perform_job(job)
		return success
	
	def work(self, burst=False):  # noqa
		try:
			result = super(NTIWorker, self).work(burst=burst)
			return result
		finally:
			self.register_death()

def _run_worker():
	args = rqworker.parse_args()

	if args.path:
		sys.path = args.path.split(':') + sys.path

	settings = {}
	if args.config:
		settings = rqworker.read_config_file(args.config)

	rqworker.setup_default_arguments(args, settings)

	# Worker specific default arguments
	if not args.queues:
		args.queues = settings.get('QUEUES', ['default'])

	if args.pid:
		with open(os.path.expanduser(args.pid), "w") as fp:
			fp.write(str(os.getpid()))

	rqworker.setup_loghandlers_from_args(args)
	rqworker.setup_redis(args)

	rqworker.cleanup_ghosts()

	logger.info("Starting Worker %s(%s)" % (os.getpid(), args.name))
	try:
		queues = list(map(Queue, args.queues))
		w = NTIWorker(queues, name=args.name)
		w.work(burst=args.burst)
	except ConnectionError as e:
		print(e)
		sys.exit(1)

def main():
	exe = sys.argv[0]
	args = sys.argv[1:]
	if not args:
		raise Exception('Specify a dataserver environment root directory')

	env_dir = args[0]
	sys.argv = [exe] + args[1:]
	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages= ('nti.appserver',),
						function=lambda: _run_worker())
	sys.exit(0)


if __name__ == '__main__':
	main()
