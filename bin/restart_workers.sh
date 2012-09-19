#!/bin/bash

workers=`ps -eaf | grep 'gunicorn: worker' | awk '{print $2}'`
# Sending QUIT to a worker asks for a graceful
# shutdown, waiting for up to the 'graceful_timeout' value
# Sending HUP to the master causes it to spawn new workers,
# and then gracefully ask the old ones to die
# The objective of sleeping between killing workers
# is so that they don't all boot at once, which can lead
# to DB conflicts and too much load on the machine
for worker in $workers; do
	kill -s QUIT $worker
	sleep 20
done
