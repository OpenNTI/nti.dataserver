# Passenger Setup #

Phusion passenger is a load balancer that connects Python to Apache. These are basic
setup instructions for it. We'll be installing passenger as root, editing `/etc/hosts` and the Apache configuration, and creating a new directory to store the app that we want to serve.

Start by following the instructions on the [passenger site](http://www.modrails.com/install.html). This will get you a passenger installation on disk.

## Apache Setup ##

Then Apache has to be modified to use passenger. For now, I created a virtual host at a distinct host name to use with passenger (leaving my main Apache untouched.) Right now I'm using `dataserver.curie.local` as the host name. Add that to `/etc/hosts`:

    127.0.0.1 localhost dataserver.curie.local

It's always a good idea to keep the apache configuration modular. On OS X, create `/etc/apache2/extra/passenger.conf` with the following contents:

    LoadModule passenger_module /opt/local/lib/ruby/gems/1.8/gems/passenger-3.0.9/ext/apache2/mod_passenger.so
	PassengerRoot /opt/local/lib/ruby/gems/1.8/gems/passenger-3.0.9
	PassengerRuby /opt/local/bin/ruby

	PassengerLogLevel 3
	PassengerDebugLogFile /Users/jmadden/Projects/DataserverPassenger/logs/debug_log
	<VirtualHost *:80>
		ServerName dataserver.curie.local
		DocumentRoot /Users/jmadden/Projects/DataserverPassenger/public
		<Directory  /Users/jmadden/Projects/DataserverPassenger/public>
			Allow from all
			Options -MultiViews
		</Directory>
	PassengerResolveSymlinksInDocumentRoot on
	#	ErrorLog /Users/jmadden/Projects/DataserverPassenger/logs/error_log
	#	CustomLog /Users/jmadden/Projects/DataserverPassenger/logs/access_log common
	</VirtualHost>

The first three lines are the standard lines from the passenger install. Then there's a block where I'm enabling lots of debugging. You could use a value from 0 to 3, or omit those two lines entirely. The last block is the virtual host definition. The `ServerName` must match what you put in `/etc/hosts`. You'll also notice that I'm pointing to a directory that I created specifically for this purpose.

You can restart Apache on the command line as root using `launchctl stop org.apach.httpd.`

## Disk Layout ##
Passenger was built to serve Rails apps, so for it to work the app must be laid out like a Rails app. I did this all with symlinks back to the content, our Python code, and the web app:

	[jmadden@curie ~/Projects/DataserverPassenger]$ ls -l
	database/
	dataserver.ini
	logs/
	passenger_request_handler.py -> /Users/jmadden/Projects/Sprints/20110505/src/main/python/passenger_request_handler.py
	passenger_wsgi.py -> /Users/jmadden/Projects/Sprints/20110505/src/main/python/passenger_wsgi.py
	public/
		NextThoughtWebApp -> /Users/jmadden/Projects/NextThoughtWebApp/
		prealgebra -> /Users/jmadden/Projects/AoPSBooks/Prealgebra_text/prealgebra/
	python -> /Users/jmadden/Projects/Sprints/20110505/src/main/python/

In summary, the content to serve goes in the `public/` directory. Two python files get linked into the root, and the python directory itself is linked in the root as well.

If you put things at this same path, then `dataserver.ini` is optional. Otherwise, you'll need to adjust it to include settings for your path. These are the defaults:

	[passenger]
	app.root = ~/Projects/DataserverPassenger/public
	[database]
	dataserver.dir = ~/Projects/DataserverPassenger/database
	dataserver.file = data.fs

You could either symlink the database directory to an existing database, or you could change the `dataserver.dir` in `dataserver.ini.`

## Testing ##

With that in place, you should be able to visit `http://dataserver.curie.local/NextThoughtWebApp/` (note the trailing slash) and login to the app. Passenger will automatically take care of starting the dataserver in the background.

Note that websockets are currently disabled when using passenger. The dataserver will only accept XHR-Polling socket.io sessions; both platforms automatically fallback to this.
