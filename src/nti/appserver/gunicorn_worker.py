# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""
Custom gevent-based worker class for gunicorn.

This module provides a custom GeventWorker subclass for gunicorn, with some
extra operational niceties.
"""

import os
import gc
import sys
import time
import signal
import logging
import traceback
import threading

import greenlet
import gevent.hub

from datetime import datetime

from gevent.monkey import get_original

from gunicorn.workers.ggevent import GeventPyWSGIWorker

logger = logging.getLogger("mozsvc.gunicorn_worker")

# Take references to un-monkey-patched versions of stuff we need.
# Monkey-patching will have already been done by the time we come to
# use these functions at runtime.
_real_sleep = get_original('time', 'sleep')
_real_get_ident = get_original('thread', 'get_ident')
_real_start_new_thread = get_original('thread', 'start_new_thread')

# The maximum amount of time that the eventloop can be blocked
# without causing an error to be logged.
DEFAULT_MAX_BLOCKING_TIME = 0.1
DEFAULT_LOOP_CALLBACK_INTERVAL = 5.0


# The maximum amount of memory the worker is allowed to consume, in KB.
# If it exceeds this amount it will (attempt to) gracefully terminate.
MAX_MEMORY_USAGE = os.environ.get("MOZSVC_MAX_MEMORY_USAGE", "").lower()
if MAX_MEMORY_USAGE:
    import psutil
    if MAX_MEMORY_USAGE.endswith("k"):
        MAX_MEMORY_USAGE = MAX_MEMORY_USAGE[:-1]
    MAX_MEMORY_USAGE = int(MAX_MEMORY_USAGE) * 1024
    # How frequently to check memory usage, in seconds.
    MEMORY_USAGE_CHECK_INTERVAL = 2
    # If a gc brings us back below this threshold, we can avoid termination.
    MEMORY_USAGE_RECOVERY_THRESHOLD = MAX_MEMORY_USAGE * 0.8


# The filename for dumping memory usage data.
MEMORY_DUMP_FILE = os.environ.get("MOZSVC_MEMORY_DUMP_FILE",
                                  "/tmp/mozsvc-memdump")


class MozSvcGeventWorker(GeventPyWSGIWorker):
    """
    Custom gunicorn worker with extra operational niceties.

    This is a custom gunicorn worker class, based on the standard gevent worker
    but with some extra operational- and debugging-related features:

        * a background thread that monitors execution by checking for:

            * blocking of the gevent event-loop, with tracebacks
              logged if blocking code is found.

            * overall memory usage, with forced-gc and graceful shutdown
              if memory usage goes beyond a defined limit.

        * a timeout enforced on each individual request, rather than on
          inactivity of the worker as a whole.

        * a signal handler to dump memory usage data on SIGUSR2.

    To detect eventloop blocking, the worker installs a greenlet trace
    function that increments a counter on each context switch.  A background
    (os-level) thread monitors this counter and prints a traceback if it has
    not changed within a configurable number of seconds.
    """

    def init_process(self):
        # pylint: disable=attribute-defined-outside-init
        # Check if we need a background thread to monitor memory use.
        needs_monitoring_thread = False
        if MAX_MEMORY_USAGE:
            self._last_memory_check_time = time.time()
            needs_monitoring_thread = True
        self._last_loop_log = time.time()

        self._looping_trace = os.environ.get('gevent_loop_trace', False)
        self._memory_trace = os.environ.get('gevent_memory_trace', False)
        self._switch_trace = os.environ.get('gevent_switch_trace', False)
        self._blocking_trace = os.environ.get('gevent_blocking_trace', False)

        self._max_blocking_time = os.environ.get('gevent_max_blocking_time',
                                                 DEFAULT_MAX_BLOCKING_TIME)
        self._max_blocking_time = float(self._max_blocking_time)

        self._loop_callback_interval = os.environ.get('gevent_loop_callback_interval',
                                                      DEFAULT_LOOP_CALLBACK_INTERVAL)
        self._loop_callback_interval = float(self._loop_callback_interval)

        # Set up a greenlet tracing hook to monitor for event-loop blockage,
        # but only if monitoring is both possible and required.
        if hasattr(greenlet, "settrace") and self._max_blocking_time > 0:
            # Grab a reference to the gevent hub.
            # It is needed in a background thread, but is only visible from
            # the main thread, so we need to store an explicit reference to it.
            self._active_hub = gevent.hub.get_hub()
            # Set up a trace function to record each greenlet switch.
            self._active_greenlet = None
            self._greenlet_switch_counter = 0
            greenlet.settrace(self._greenlet_switch_tracer)
            self._main_thread_id = _real_get_ident()
            needs_monitoring_thread = True

        # Create a real thread to monitor out execution.
        # Since this will be a long-running daemon thread, it's OK to
        # fire-and-forget using the low-level start_new_thread function.
        if needs_monitoring_thread:
            _real_start_new_thread(self._process_monitoring_thread, ())

        # Continue to superclass initialization logic.
        # Note that this runs the main loop and never returns.
        super(MozSvcGeventWorker, self).init_process()

    def init_signals(self):
        # Leave all signals defined by the superclass in place.
        super(MozSvcGeventWorker, self).init_signals()

        # Hook up SIGUSR2 to dump memory usage information.
        # This will be useful for debugging memory leaks and the like.
        signal.signal(signal.SIGUSR2, self._dump_memory_usage)
        if hasattr(signal, "siginterrupt"):
            signal.siginterrupt(signal.SIGUSR2, False)

    def handle_request(self, *args):
        # Apply the configured 'timeout' value to each individual request.
        # Note that self.timeout is set to half the configured timeout by
        # the arbiter, so we use the value directly from the config.
        with gevent.Timeout(self.cfg.timeout):
            return super(MozSvcGeventWorker, self).handle_request(*args)

    def _greenlet_switch_tracer(self, what, (origin, target)):  # pylint: disable=unused-argument
        """
        Callback method executed on every greenlet switch.

        The worker arranges for this method to be called on every greenlet
        switch.  It keeps track of which greenlet is currently active and
        increments a counter to track how many switches have been performed.
        """
        # pylint: disable=attribute-defined-outside-init
        # Increment the counter to indicate that a switch took place.
        # This will periodically be reset to zero by the monitoring thread,
        # so we don't need to worry about it growing without bound.
        self._active_greenlet = target
        self._greenlet_switch_counter += 1
        if self._switch_trace:
            now = datetime.now()
            now = now.strftime('%Y-%m-%d %H:%M:%S,%f')
            thread = threading.current_thread()
            print('%s [%s:%s] [%s] Switched greenlet context'
                  % (now, thread.ident, os.getpid(), thread.getName()))

    def _process_monitoring_thread(self):
        """
        Method run in background thread that monitors our execution.

        This method is an endless loop that gets executed in a background
        thread.  It periodically wakes up and checks:

            * whether the active greenlet has switched since last checked
            * whether memory usage is within the defined limit

        """
        # Find the minimum interval between checks.
        if MAX_MEMORY_USAGE:
            sleep_interval = MEMORY_USAGE_CHECK_INTERVAL
            if self._max_blocking_time and self._max_blocking_time < sleep_interval:
                sleep_interval = self._max_blocking_time
        else:
            sleep_interval = self._max_blocking_time
        # Run the checks in an infinite sleeping loop.
        try:
            while True:
                _real_sleep(sleep_interval)
                self._check_greenlet_blocking()
                self._check_memory_usage()
                self._log_loop_callbacks()
        except Exception:  # pylint: disable=broad-except
            # Swallow any exceptions raised during interpreter shutdown.
            # Daemonic Thread objects have this same behaviour.
            if sys is not None:
                raise

    def _check_greenlet_blocking(self):
        if not self._max_blocking_time or not self._blocking_trace:
            return
        # pylint: disable=attribute-defined-outside-init
        # If there have been no greenlet switches since we last checked,
        # grab the stack trace and log an error.  The active greenlet's frame
        # is not available from the greenlet object itself, we have to look
        # up the current frame of the main thread for the traceback.
        if self._greenlet_switch_counter == 0:
            active_greenlet = self._active_greenlet
            # The hub gets a free pass, since it blocks waiting for IO.
            if active_greenlet not in (None, self._active_hub):
                # pylint: disable=no-member,protected-access
                frame = sys._current_frames()[self._main_thread_id]
                stack = traceback.format_stack(frame)
                err_log = ["Greenlet blocked (cpu bound?)\n"] + stack
                logger.warn("".join(err_log))
        # Reset the count to zero.
        # This might race with it being incremented in the main thread,
        # but not often enough to cause a false positive.
        self._greenlet_switch_counter = 0

    def _log_loop_callbacks(self):
        if not self._looping_trace:
            return
        # pylint: disable=attribute-defined-outside-init
        elapsed = time.time() - self._last_loop_log
        if elapsed > self._loop_callback_interval:
            try:
                # pylint: disable=protected-access
                count = len(self._active_hub.loop._callbacks)
                if count:
                    logger.info("Gevent loop callback (count=%s)", count)
            except AttributeError:
                pass
            self._last_loop_log = time.time()

    def _check_memory_usage(self):
        if not MAX_MEMORY_USAGE or not self._memory_trace:
            return
        # pylint: disable=attribute-defined-outside-init
        elapsed = time.time() - self._last_memory_check_time
        if elapsed > MEMORY_USAGE_CHECK_INTERVAL:
            mem_usage = psutil.Process().memory_info().rss
            if mem_usage > MAX_MEMORY_USAGE:
                logger.info("memory usage %d > %d, forcing gc",
                            mem_usage, MAX_MEMORY_USAGE)
                # Try to clean it up by forcing a full collection.
                gc.collect()
                mem_usage = psutil.Process().memory_info().rss
                if mem_usage > MEMORY_USAGE_RECOVERY_THRESHOLD:
                    # Didn't clean up enough, we'll have to terminate.
                    logger.warn("memory usage %d > %d after gc, quitting",
                                mem_usage, MAX_MEMORY_USAGE)
                    self.alive = False
            self._last_memory_check_time = time.time()

    def _dump_memory_usage(self, *unused_args):
        """
        Dump memory usage data to a file.

        This method writes out memory usage data for the current process into
        a timestamped file.  By default the data is written to a file named
        /tmp/mozsvc-memdump.<pid>.<timestamp> but this can be customized
        with the environment variable "MOSVC_MEMORY_DUMP_FILE".

        If the "meliae" package is not installed or if an error occurs during
        processing, then the file "mozsvc-memdump.error.<pid>.<timestamp>"
        will be written with a traceback of the error.
        """
        now = int(time.time())
        try:
            import meliae
            filename = "%s.%d.%d" % (MEMORY_DUMP_FILE, os.getpid(), now)
            getattr(meliae, 'scanner').dump_all_objects(filename)
        except (ImportError, Exception):  # pylint: disable=broad-except
            filename = "%s.error.%d.%d" % (MEMORY_DUMP_FILE, os.getpid(), now)
            with open(filename, "w") as f:
                f.write("ERROR DUMPING MEMORY USAGE\n\n")
                traceback.print_exc(file=f)
