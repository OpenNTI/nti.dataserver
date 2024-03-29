============================================
 nginx, gunicorn haproxy, and stunnel Setup
============================================

The combination of the nginx HTTP server, gunicorn WSGI server, and
haproxy reverse proxy is a popular one in the Python world. `nginx
<http://nginx.org/>`_ is a very lightweight HTTP server (relative to
Apache) and will be used for serving the static parts of the site.
`gunicorn <http://gunicorn.org/>`_ is a load balancer/monitor specifically
tailored to Python WSGI applications, especially those that use
gevent. `HAProxy <http://haproxy.1wt.eu>`_ is the reverse proxy
that sits in front of both of these and mediates between them (it can
also handle load balancing);
(it would not be necessary if nginx could handle WebSockets, but as of
1.1.12, it cannot). Finally, `stunnel <http://www.stunnel.org/>`_
serves as the SSL termination point, and forwards all actual serving
to HAProxy (stunnel is needed because it supports arbitrary TCP
connections and arbitrary duration; neither amazon's load balancing
service nor the open-source Poind support WebSockets).

These are basic setup instructions for OS X and Amazon Linux. The Linux
instructions are derived from `a blog
post <http://adrian.org.ar/python/django-nginx-green-unicorn-in-an-ubuntu-11-10-ec2-instance>`_.

nginx Setup
===========

Our end goal will be to get nginx serving static content from
``/Library/WebServer/Documents/`` on port 8080 (Linux) or port 8080 (OS X)
with gzip compression enabled. Dynamic content requests will be
forwarded to port 8081 where the dataserver runs.
(The section `SSL And Complete Configuration`_
gives the final configuration.)

Installation
------------

As of this writing, the latest nginx stable version is 1.0.12. On linux,
follow `the instructions <http://wiki.nginx.org/Install>`_ to install
nginx (on Amazon linux, don't forget to add a ``priority=1`` line to the
Yum configuration). On OS X, use MacPorts. If the version that comes
with macports is too old, create a custom portfile for 1.0.12 and follow
the normal procedure.

Mac OS X
~~~~~~~~

Begin by copying ``/opt/local/etc/nginx/nginx.conf.default`` to
``/opt/local/etc/nginx/nginx.conf.`` Edit this new file to enable the
commented-out logging (make sure the paths point to
``/opt/local/var/log/nginx/``), gzip (also add a ``gzip_types`` line to
allow compression of more than ``text/html``:
``gzip_types application/x-javascript application/javascript text/xml;``)
and keepalive (add ``keepalive_disable none;``). In the ``server``
stanza, point the root to ``/Library/WebServer/Documents/`` and listen
on port 8080; deny access to .htaccess files.

Test that this has worked by browsing
``http://localhost:8080/prealgebra/``. Use the web inspector to verify
that resources were gzipped.

Note that gzip requires a fixed list of types and cannot accept
wildcards. These instructions set up gzip for static content types only,
not the myriad of content types used by the OData implementation of
dataserver2.

Linux
~~~~~

On Linux, the main configuration file is ``/etc/nginx/nginx.conf``;
enable gzip in this file. This file includes ``conf.d/*.conf``; proceed
to make the rest of the changes in ``conf.d/default.conf``, leaving the
port at 80.

The ``/Library/WebServer/Documents/`` tree should be owned by the
``nginx`` user.

Proxy Configuration
-------------------

The nginx process will redirect requests to the gunicorn (or standalone)
dataserver by proxy. There are two methods to accomplish this, explicit
and implicit. Implicit will probably be preferred.

With either method, after you make the changes and restart nginx (e.g.,
with ``nginx -s reload`` on OS X or ``service nginx reload`` on Linux)
and start the dataserver (e.g, ``pserve config/development.ini``) you should be able to
use a single port (80 or 8080) to request both static content, hit the
dataserver, and search within a unit of content.

Note that neither method supports websockets, so socket.io will fallover
to using XHR-polling. This is due to nginx not supporting 'Connection:
Upgrade' from the proxy (no matter how hard you fight). In the future,
we will consider using the tcp proxy for this (it requires different
ports for websockets and the main app, sadly).

Explicit Proxy Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this method, we explicitly list the paths that we want proxied. To do
this, add a ``location`` configuration to the ``server`` section of the
nginx configuration:

::

    location ~ /dataserver[2]?|/.*/Search/|/socket.io/ {
        proxy_buffering off;
        proxy_pass_header Server;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_connect_timeout 10;
        proxy_read_timeout 10;
        proxy_pass http://localhost:8081;
    }

Implicit Proxy Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method functions much like Passenger: if the file exists on disk,
serve it. Otherwise, pass the request through to the dataserver. This
takes two blocks, one at the ``http`` level:

::

        upstream appserver {
                server localhost:8081 fail_timeout=10;
        }

And the second within the ``server`` level (this replaces the existing
``location /`` block:

::
	proxy_http_version 1.1;
    root   /Library/WebServer/Documents;
    location / {
        # checks for static file, if not found proxy to app
        try_files $uri @proxy_to_app;
        index  index.html index.htm;
        expires +10m;
		add_header Cache-Control proxy-revalidate;
    }

    location @proxy_to_app {
        proxy_buffering off;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;

        proxy_pass   http://appserver;
    }

SSL and Complete Configuration
------------------------------

If we are using nginx as the SSL termination point, we would stop
here. The nginx wiki has `good instructions
<http://wiki.nginx.org/HttpSslModule>`_ on how to enable SSL for
nginx. Once that's done, the entire configuration for the dataserver
should look something like this:


::

	sendfile       on;
	tcp_nopush     on;
	directio 512;
	aio on;

	keepalive_timeout  65;
	keepalive_disable none;

	gzip  on;
	gzip_types text/css text/javascript application/xml application/x-javascript application/javascript text/xml application/vnd.nextthought.workspace+json;
	gzip_proxied any;
	gzip_vary on;
	gzip_http_version 1.0;

	open_file_cache max=1000;
	open_file_cache_errors on;

	upstream appserver {
		server localhost:8081 fail_timeout=10;
	}
	server {
		#listen       8080;
		server_name  alpha-ec2.nextthought.com;
		listen 443 default_server ssl;
		listen 80;
		ssl_certificate /opt/nti/ssl_certs/server.crt;
		ssl_certificate_key /opt/nti/ssl_certs/server.key;

		root   /Library/WebServer/Documents;
		proxy_http_version 1.1;
		location / {
			# checks for static file, if not found proxy to app
			try_files $uri @proxy_to_app;
			index  index.html index.htm;
		    expires +10m;
			add_header Cache-Control proxy-revalidate;
		}

		location @proxy_to_app {
			proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
			proxy_set_header Host $http_host;
			proxy_buffering off;
			proxy_redirect off;

			proxy_pass   http://appserver;
		}

		# deny access to .htaccess files, if Apache's document root
		# concurs with nginx's one
		#
		location ~ /\.ht {
			deny  all;
		}

	}



gunicorn setup
==============

It is very easy to use gunicorn with the above setup. The gunicorn
server is the default server in ``config/development.ini`` so the
``pserve`` command by default will launch gunicorn. (This is a rather
specific configuration; see gunicorn.py for more info.)

In the future, we may be able to bind to a unix
domain socket (a file) instead of a port; this might be a bit faster.

::

	openssl req -x509 -newkey rsa:1024 -keyout srv_comb.pem -out srv_comb.pem -days 365 -nodes

HAProxy
=======

The 1.5-dev series of haproxy is required for proper PROXY protocal support.
Version 1.5-dev9 is current. On linux, compile with:

::

	make TARGET=linux26 PREFIX=/opt/nti

If you first install the haproxy RPM, then you can patch
``/etc/init.d/haproxy`` to use the new binary (or replace the old
binary with the new one).

The configuration would reside in ``/etc/haproxy/haproxy.cfg``.
HAProxy is configured to take HTTP traffic from stunnel and direct it to
the Dataserver directly if possible, otherwise to assume it is static
content and direct to nginx. It also listens or port 843 (the flash
socket policy port) and directs that to the dataserver as well (in
plain TCP mode).

Note that with haproxy in front, you probably want to disable nginx
proxying to the dataserver and let haproxy do all the direction.

::

  global
	log         127.0.0.1 local2
	maxconn     4096 # Total Max Connections. This is dependent on ulimit
	nbproc      3

  defaults
	mode        http
	# If we don't set this, then we lose X-Forwarded-For
	option http-server-close

  frontend httpredir 0.0.0.0:80
	option httplog
	log global
	timeout client 600
	use_backend ssl_backend if TRUE

  frontend flashsocketredirct 0.0.0.0:843
	mode tcp
	timeout client 600
	default_backend flash_backend


  backend ssl_backend
	timeout server 30000
	timeout connect 4000
	# the server redir seems to be broken in 1.5 dev9
	# It seems to be directly making the server connection and
	# choking on the SSL response, resulting in empty data for the client
	#server alphassl alpha.nextthought.com:443 backup redir https://alpha.nextthought.com
	# Redirect location without HTTP path causes some weird
	# issues too for the pad in particular
	# redirect prefix seems to do what we want
	redirect prefix https://alpha.nextthought.com


  frontend all 127.0.0.1:8084
	option httplog
	log global
	timeout client 86400000
	# Listen on the socket for incoming SSL in proxy mode
	# We give it a specific id so that we can match in an ACL
	# (We can't match on ssl itself because that's already been handled)
	bind /var/run/ssl-frontend.sock user root mode 600 id 42 accept-proxy
	default_backend www_backend

	acl is_websocket hdr(Upgrade) -i WebSocket
	acl is_websocket hdr_beg(Host) -i ws

	acl is_dyn path_beg /dataserver
	acl is_dyn path_beg /library
	acl is_dyn path_beg /socket.io
	acl is_dyn path_beg /dictionary
	# Consider a path_sub here for Search urls

	acl is_ssl so_id 42

	# Proxying for YouTube so we can avoid Cross-Origin issues in the
	# browser
	acl is_youtube path_beg /embed
	acl is_youtube path_beg /get_video_info

	# Block some common attack vectors
	# and restricted data
	acl is_blocked_name path_end .php .asp .jsp .exe .aspx
	acl is_blocked_name path_dir .nti_acl indexdir
	block if is_blocked_name

	# The webapp uses the ?h= param to bust CDN caches that don't
	# properly vary by origin. But if we have nginx in front of the
	# dataserver as a proxy, nginx sees the query param and passes it
	# through, which is very slow. In that case, disable try_files
	# and trust the ACLs here to direct things appropriately.
	acl is_host_cors url_sub ?h=

	use_backend www_backend if is_host_cors
	use_backend socket_backend if is_websocket
	use_backend socket_backend if is_dyn
	use_backend youtube_backend if is_youtube

	# Let gunicorn/nginx know if we are dealing with an incoming HTTPS request
	# (This is a default 'secure-header' in gunicorns conf)
	reqidel ^X-FORWARDED-PROTOCOL:.*
	reqadd X-FORWARDED-PROTOCOL:\ ssl if is_ssl

	# Go to the app by default
	redirect location /NextThoughtWebApp/index.html code 301 if { path / }
	redirect location /tutorials/index.html code 301 if { path /tutorials }

  backend youtube_backend
	balance roundrobin
	timeout server 30000
	timeout connect 4000
	# We must alter the Host line so youtube's
	# virtual hosting works. For the get_video_info portion
	# we MUST use the host 'www.youtube.com' (youtube.com redirects
	# to this, which still has Cross Origin issues)
	reqidel ^Host:.*
	reqadd Host:\ www.youtube.com
	# NOTE: Server lines that use DNS names are resolved at (and only
	# at) startup. If DNS is unavailable, haproxy will fail to start.
	# If the DNS info later changes haproxy will fail to see the change.
	server youtube www.youtube.com:80 weight 1 maxconn 1024


  backend www_backend
	balance roundrobin
	option forwardfor # This sets X-Forwarded-For
	timeout server 30000
	timeout connect 4000
	server nginx 127.0.0.1:8080 weight 1 maxconn 1024

  backend socket_backend
	balance roundrobin
	option forwardfor # This sets X-Forwarded-For
	timeout queue 5000
	timeout server 86400000
	timeout connect 86400000
	server dataserver 127.0.0.1:8081 weight 1 maxconn 1024

  backend flash_backend
	mode tcp
	balance roundrobin
	timeout queue 5000
	timeout server 86400000
	timeout connect 86400000
	balance roundrobin
	option forwardfor # This sets X-Forwarded-For
	server flashserver 127.0.0.1:10843 weight 1 maxconn 1024

Logging
-------

Haproxy can produce incredibly detailed logs that are very useful for
performance tuning in a situation with multiple backends (like ours).
They are verbose, though, and clutter things up by default. On Linux,
we want to clean things up by editing the syslog configuration and
enabling logrotate. (This assumes the logging configuration from above.)

First, syslog. Disable haproxy from writing to the standard message
file and put it in its own file:

::

  # Find the line like this and add 'local2.none'
  *.info;mail.none;authpriv.none;cron.none;local2.none  /var/log/messages

  # Add a line like this
  local2.*                                              /var/log/haproxy


Then in ``/etc/logrotate.d/haproxy``, but this configuration:

::

  /var/log/haproxy {
    daily
    rotate 10
    missingok
    notifempty
    compress
    create 644 root root
    sharedscripts
    postrotate
        /bin/kill -HUP `cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null || true
        /bin/kill -HUP `cat /var/run/rsyslogd.pid 2> /dev/null` 2> /dev/null || true
    endscript
  }

Stunnel
=======

These instructions are for version 4.53; any version greater than 4.44
is required in order to add PROXY support so that HAProxy knows the
originating IP and can pass it on to nginx.

On AWS, first install the available stunnel distribution (to get setup
scripts). Then download and compile the latest stunnel like so:

::

	./configure --prefix=/opt/nti --disable-dependency-tracking --with-threads=pthread; make

::

	cert = /opt/nti/ssl_certs/srv_comb.pem
	# It seems that as of the 2012 AMI, FIPS support is on in OpenSSL
	# Which leads to a "fingerprint" error (it may be that
	# regenning the certs could solve that, but turning fips
	# off is easier)
	fips = no
	[https]
	accept = 443
	connect = /var/run/ssl-frontend.sock
	protocol = proxy
	# The default SSL version support doesn't let us be crawled
	# by google. Turn them all on. (This probably allows some minimal
	# security holes?)
	sslVersion = all

Finally, ``make install`` You probably want to copy/link the binary from
/opt/nti/bin into /usr/bin. (Likewise for haproxy.)


Upstart
=======

The following is an upstart configuration to put in
``/etc/init/dataserver.conf`` for Amazon linux.

::

    description "Dataserver"
    start on runlevel [2345]
    stop on runlevel [06]

    respawn
    respawn limit 10 5

    # setuid seems not to be supported in this version
    #setuid ec2-user
    #exec /home/ec2-user/app_run.sh

    exec /bin/su - ec2-user /opt/nti/bin/gunicorn -k nti.appserver.gunicorn.GeventApplicationWorker nti.appserver.gunicorn:app -b 127.0.0.1:8081
