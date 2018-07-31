#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Session distribution and management.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import time
import zlib
import numbers
import warnings
import contextlib
import transaction

try:
    import cPickle as pickle
except ImportError:
    import pickle

import simplejson as json

import gevent

from persistent import Persistent

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.deprecation import deprecated

from zope.event import notify

from ZODB.loglevels import TRACE

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IRedisClient
from nti.dataserver.interfaces import ISessionService
from nti.dataserver.interfaces import IAuthenticationPolicy
from nti.dataserver.interfaces import SiteNotInstalledError
from nti.dataserver.interfaces import ISessionServiceStorage
from nti.dataserver.interfaces import IUserNotificationEvent
from nti.dataserver.interfaces import IDataserverTransactionRunner
from nti.dataserver.interfaces import IImpersonatedAuthenticationPolicy

from nti.externalization.externalization import toExternalObject

from nti.externalization.externalization import DevmodeNonExternalizableObjectReplacer
#from nti.externalization.externalization.replacers import DevmodeNonExternalizableObjectReplacementFactory

from nti.socketio.interfaces import ISocketSession
from nti.socketio.interfaces import ISocketIOSocket
from nti.socketio.interfaces import ISocketSessionConnectedEvent
from nti.socketio.interfaces import ISocketSessionDisconnectedEvent

from nti.socketio.interfaces import SocketSessionDisconnectedEvent

from nti.socketio.persistent_session import AbstractSession as Session

from nti.transactions import transactions


class _AlwaysIn(object):
    """
    Everything is `in` this class.
    """

    def __init__(self):
        pass

    def __contains__(self, obj):
        return True


@contextlib.contextmanager
def _NOP_CM():
    yield


@interface.implementer(ISessionService)
class SessionService(object):
    """
    Manages the open sessions within the system.

    Keeps a dictionary of `proxy_session` objects that will have
    messages copied to them whenever anything happens to the real
    session.

    This object will look for a utility component of
    :class:`.ISessionServiceStorage` to provide session storage, and a
    utility component :class:`nti.dataserver.interfaces.IRedisClient`
    to provide Redis services.
    """

    channel_name = 'sessions/cluster_channel'

    def __init__(self):
        """
        """
        self.proxy_sessions = {}
        # self.pub_socket = None
        # Note that we have no way to close these greenlets. We depend
        # on GC of this object to let them die when the last refs to
        # us do.
        self.cluster_listener = self._spawn_cluster_listener()
        self._watching_sessions = set()
        self._session_watchdog = self._spawn_session_watchdog()

        transactions.add_abort_hooks()

    def close(self):
        self.cluster_listener.kill()
        self._session_watchdog.kill()

    @property
    def _session_db(self):
        return component.getUtility(ISessionServiceStorage)

    # NOTE: In the past we used ZMQ for the publish/subscribe functionality.
    # However, ZMQ uses background threads, which is not compatible with forking,
    # and we want to be able to fork to use certain other frameworks. Hence, we now
    # use Redis for pub/sub

    def _spawn_cluster_listener(self):

        def read_incoming():
            sub = self._redis.pubsub()
            sub.subscribe(self.channel_name)
            for msg_dict in sub.listen():
                if msg_dict['type'] != 'message':
                    continue
                __traceback_info__ = msg_dict
                msgs = msg_dict['data']
                msgs = pickle.loads(msgs)  # TODO: Compression?

                # In our background greenlet, we begin and commit
                # transactions around sending messages to
                # the proxy queue. If the proxy is transaction aware,
                # then it must also be waiting in another greenlet
                # on get_client_msg, whereupon it will see this message arrive
                # after we commit (and probably begin its own transaction)
                # NOTE: that the normal _dispatch_message_to_proxy can be called
                # already in a transaction
                # NOTE: We do not do this in a site (to reduce DB connections), so the proxy listeners need to
                # be very limited in what they do
                try:
                    transaction.begin()
                    _ = self._dispatch_message_to_proxy(*msgs)
                    transaction.commit()
                except Exception:
                    logger.exception("Failed to dispatch incoming cluster message.")

        return gevent.spawn(read_incoming)

    def _spawn_session_watchdog(self):
        # A monotonic series, unlikely to wrap when we spawned
        my_sleep_adjustment = os.getpid() % 20
        if os.getpid() % 2:  # if even, go low
            my_sleep_adjustment = -my_sleep_adjustment
        tx_runner = component.getUtility(IDataserverTransactionRunner)

        def watchdog_sessions():
            while True:
                # Some transports make it very hard to detect
                # when a session stops responding (XHR)...it just goes silent.
                # We watch for it to die (since we created it) and cleanup
                # after it...this is a compromise between always
                # knowing it has died and doing the best we can across the
                # cluster
                gevent.sleep(60 + my_sleep_adjustment)
                # Time? We can detect a dead session no faster than we decide it's dead,
                # which is SESSION_HEARTBEAT_TIMEOUT. We adjust it so that all
                # workers on a machine (which were forked almost simultaneously) don't
                # all go through it at the same instant.

                watching_sessions = list(self._watching_sessions)

                # TODO: With the heartbeats in redis, we can check for valid sessions there.
                # Only for invalid sessions will we have to hit the DB
                try:
                    # In the past, we have done this by having a single greenlet per
                    # session_id. While this was convenient and probably not too heavy weight from a greenlet
                    # perspective, there are some indications that so many small transactions was
                    # a net loss as far as the DB goes. A few bigger transactions are more efficient, to a point
                    # although there is a higher risk of conflict
                    def _get_sessions():
                        t0 = time.time()
                        result = {sid: self.get_session(sid) for sid in watching_sessions}
                        if result:
                            logger.info('Performed maintenance on %s sessions (%.2f)',
                                        len(result),
                                        time.time() - t0 )
                        return result
                    sessions = tx_runner(_get_sessions, retries=5, sleep=0.1)
                except transaction.interfaces.TransientError:
                    # Try again later
                    logger.debug("Trying session poll later", exc_info=True)
                    continue
                except SiteNotInstalledError:
                    # Happens if startup takes too long, e.g., while
                    # downloading index data
                    logger.debug("Site setup not ready; trying to poll later")
                    continue

                cleaned_count = 0
                for sid, sess in sessions.items():
                    if sess is None:
                        cleaned_count += 1
                        logger.log(TRACE, "Session %s died", sid)
                        self._watching_sessions.discard(sid)
                if cleaned_count:
                    logger.info( 'Cleaned up %s sessions (checked_count=%s)',
                                 cleaned_count, len(watching_sessions))
        return gevent.spawn(watchdog_sessions)

    def _dispatch_message_to_proxy(self, session_id, function_name, function_arg):
        handled = False
        proxy = self.get_proxy_session(session_id)
        if hasattr(proxy, function_name):
            getattr(proxy, function_name)(function_arg)
            handled = True
        elif proxy and function_name == 'session_dead':
            # Kill anything reading from it
            for x in ('queue_message_from_client', 'queue_message_to_client'):
                if hasattr(proxy, x):
                    getattr(proxy, x)(None)
            handled = True
        return handled

    def set_proxy_session(self, session_id, session=None):
        """
        Establish or remove a session proxy for the given session_id.

        :param session: Something with `queue_message_from_client` and `queue_message_to_client` methods.
                If `None`, then a proxy session for the `session_id` will be removed (if any)
        """
        if session is not None:
            self.proxy_sessions[session_id] = session
        elif session_id in self.proxy_sessions:
            del self.proxy_sessions[session_id]

    def get_proxy_session(self, session_id):
        return self.proxy_sessions.get(session_id)

    def create_session(self, session_class=Session, watch_session=True,
                       drop_old_sessions=True, **kwargs):
        """
        The returned session must not be modified.

        :param bool drop_old_sessions: If ``True`` (the default) then we will proactively look
                for sessions for the session owner in excess of some number or some age and
                automatically kill them, keeping a limit on the outstanding sessions the owner can have.
                TODO: This may force older clients off the connection? Which may make things worse?
        :param unicode owner: The session owner.
        :param kwargs: All the remaining arguments are passed to the session constructor.

        """
        if 'owner' not in kwargs:
            raise ValueError("Neglected to provide owner")

        session = session_class(**kwargs)
        self._session_db.register_session(session)

        if drop_old_sessions:
            outstanding = self.get_sessions_by_owner(session.owner)
            if outstanding:
                self._cleanup_sessions(outstanding)

        session_id = session.session_id
        if watch_session:
            self._watching_sessions.add(session_id)

        return session

    def _get_session(self, session_id):
        """
        Gets a session object without any validation.
        """
        result = self._session_db.get_session(session_id)
        if isinstance(result, Session):
            result._v_session_service = self
        return result

    #: Sessions without a hearbeat for 2 minutes get cleaned up.
    SESSION_HEARTBEAT_TIMEOUT = 60 * 2

    def _is_session_dead(self, session, max_age=SESSION_HEARTBEAT_TIMEOUT):
        too_old = time.time() - max_age
        last_heartbeat_time = self.get_last_heartbeat_time(session.session_id,
                                                           session)
        return (    last_heartbeat_time < too_old
                and session.creation_time < too_old) \
            or (session.state in (Session.STATE_DISCONNECTING, Session.STATE_DISCONNECTED))

    def _session_cleanup(self, s, send_event=True):
        """
        Cleans up a dead session.

        :param bool send_event: If ``True`` (the default) killing the session broadcasts
               a SocketSessionDisconnectedEvent. Otherwise, no events are sent.
        """
        self._session_db.unregister_session(s)

        # Now that the session is unreachable,
        # make sure the session itself knows it's dead
        s.kill(send_event=send_event)
        # Let any listeners across the cluster also know it
        self._publish_msg(b'session_dead', s.session_id, b"42")

    def _validated_session(self, s, send_event=True, cleanup=True):
        """ Returns a live session or None """
        if s and self._is_session_dead(s):
            if cleanup:
                self._session_cleanup(s, send_event=send_event)
            return None
        return s

    def get_session(self, session_id, cleanup=True):
        s = self._get_session(session_id)
        s = self._validated_session(s, cleanup=cleanup)
        if s:
            s.incr_hits()
        return s

    #: One day old sessions get cleaned up.
    SESSION_CLEANUP_AGE = 60 * 60 * 24

    def _cleanup_sessions(self, sessions):
        """
        Cleanup and notify the given sessions; we only clean up (live or dead)
        sessions if they're a certain age old.
        """
        # We only want to purge day old sessions to hopefully avoid contention
        # if the system gets in a bad state (rapid client socket requests,
        # dataserver swapping, etc). If two conflicting requests are cleaning
        # up the same sessions, conflicts should be much easier to resolve.
        one_day_ago = time.time() - self.SESSION_CLEANUP_AGE
        sessions_to_cleanup = []
        for session in sessions:
            if session.creation_time < one_day_ago:
                self._session_cleanup(session, send_event=False)
                sessions_to_cleanup.append(session)

        # Must notify once we've cleaned up all sessions we need to
        # in order to avoid a max recursion issue (from subscribers).
        for session in sessions_to_cleanup:
            notify(SocketSessionDisconnectedEvent(session))

    def get_sessions_by_owner(self, session_owner):
        """
        Returns sessions for the given owner that are reasonably likely
        to be active and alive.
        """
        maybe_valid_sessions = self._session_db.get_sessions_by_owner(
            session_owner)
        result = []
        # For efficiency, and to avoid recursing too deep in the presence of many dead sessions
        # and event listeners for dead sessions that also want to know the live sessions and so call us,
        # we collect all dead sessions before we send any notifications
        dead_sessions = []
        # copy because we mutate -> validated_session -> session_cleanup
        for maybe_valid_session in list(maybe_valid_sessions):
            valid_session = self._validated_session(maybe_valid_session,
                                                    send_event=False,
                                                    cleanup=False)
            if valid_session:
                result.append(valid_session)
            elif maybe_valid_session and maybe_valid_session.owner:
                dead_sessions.append(maybe_valid_session)

        self._cleanup_sessions(dead_sessions)
        return result

    def get_session_by_owner(self, session_owner_name, session_ids=_AlwaysIn()):
        """
        Find and return a valid session for the given username.

        :return: Session for the given owner.
        :param session_owner_name: The session.owner to match.
        :param session_ids: If not None, the session returned is one of the sessions
                in this object.    May be a single session ID or something that supports 'in.'
                The default is to return an arbitrary session.
        """
        if session_ids is None:
            session_ids = _AlwaysIn()
        elif    not isinstance(session_ids, _AlwaysIn) \
            and isinstance(session_ids, (basestring, numbers.Number)):
            # They gave us a bare string
            session_ids = (session_ids,)
        # Since this is arbitrary by name, we choose to return
        # the most recently created session that matches.
        candidates = list(self.get_sessions_by_owner(session_owner_name))
        candidates.sort(key=lambda x: x.creation_time, reverse=True)
        for s in candidates:
            if s.session_id in session_ids:
                return s
        return None

    def delete_sessions(self, session_owner):
        """
        Delete all sessions for the given owner (active and alive included)
        :return: All deleted sessions.
        """
        result = list(self._session_db.get_sessions_by_owner(session_owner))
        for s in result:
            self.delete_session(s.id)
        return result

    def delete_session(self, session_id):
        sess = self._session_db.get_session(session_id)
        self._session_db.unregister_session(sess)
        if sess:
            sess.kill()

    # ## High-level messaging routines

    def send_event_to_user(self, username, name, *args):
        """
        Directs the event named ``name`` to all connected sessions for the ``username``.
        The sequence of ``args`` is externalized and sent with the event.

        :param username: Usually a string naming a user with sessions. May also be a session itself,
                which limits the event to being sent to just that session.
        """
        if not username:
            return

        all_sessions = None
        if ISocketSession.providedBy(username):
            # We could just use this session, but we want to be sure its valid
            session_id = username.session_id
            username = username.owner
            session = self.get_session_by_owner(username,
                                                session_ids=(session_id,))
            if session is not None:
                all_sessions = (session,)
        else:
            all_sessions = self.get_sessions_by_owner(username)

        if not all_sessions:  # pragma: no cover
            logger.log(TRACE,
                       "No sessions for %s to send event %s to",
                       username, name)
            return

        # When sending an event to a user, we need to write the object
        # in the form particular to that user, since the information we transmit
        # (in particular links like the presence/absence of the Edit link or the @@like and @@favorite links)
        # depends on who is asking.
        # "Who is asking" depends on the current IAuthenticationPolicy. We have a policy that lets
        # us maintain a stack of users. If we cannot find it, then we will
        # write the wrong data out
        auth_policy = component.queryUtility(IAuthenticationPolicy)
        imp_policy = IImpersonatedAuthenticationPolicy(auth_policy, None)
        if imp_policy is not None:
            imp_user = imp_policy.impersonating_userid(username)
        else:
            imp_user = _NOP_CM

        with imp_user():
            # Trap externalization errors /now/ rather than later during
            # the process
            replacer = DevmodeNonExternalizableObjectReplacer
            args = [
                toExternalObject(arg, default_non_externalizable_replacer=replacer)
                for arg in args
            ]

        for s in all_sessions:
            logger.log(TRACE, "Dispatching %s to %s", name, s)
            ISocketIOSocket(s).send_event(name, *args)

    # ## Low-level messaging routines (that can probably be refactored/extracted for clarity)

    @Lazy
    def _redis(self):
        redis = component.getUtility(IRedisClient)
        logger.info("Using redis for session storage")
        return redis

    def _put_msg_to_redis(self, queue_name, msg):
        self._redis.pipeline().rpush(queue_name, msg).expire(
            queue_name, self.SESSION_HEARTBEAT_TIMEOUT * 2).execute()

    def _publish_msg_to_redis(self, channel_name, msg):
        self._redis.publish(channel_name, msg)  # No need to pipeline

    def _put_msg(self, meth, q_name, session_id, msg):
        sess = self._get_session(session_id)

        if sess:
            queue_name = 'sessions/' + session_id + '/' + q_name
            # TODO: Probably need to add timeouts here? Is the normal heartbeat
            # enough?
            if msg is None:
                msg = ''
            else:
                msg = zlib.compress(msg)
            # We wind up with a lot of these data managers for a given transaction (e.g., one for every
            # message to every session). We really would like to coallesce these into one, which we
            # can do with some work
            transactions.do(target=self,
                            call=self._put_msg_to_redis,
                            args=(queue_name, msg,))

    def _publish_msg(self, name, session_id, msg_str):
        if msg_str is None:  # Disconnecting/kill(). These don't need to go to the cluster, handled locally
            return

        assert isinstance(name, str)  # Not Unicode, only byte constants

        # Must be a string of some type now
        assert isinstance(session_id, basestring)
        if isinstance(session_id, unicode):
            warnings.warn("Got unexpected unicode session id",
                          UnicodeWarning, stacklevel=3)
            session_id = session_id.encode('ascii')

        # Must be a string of some type now
        assert isinstance(msg_str, basestring)
        if isinstance(msg_str, unicode):
            warnings.warn("Got unexpected unicode value",
                          UnicodeWarning, stacklevel=3)
            msg_str = msg_str.encode('utf-8')

        # Now notify the cluster of these messages. If the session proxy lives here, in this
        # process, then we can bypass the notification and handle it all in-process.
        # NOTE: This is fairly tricky and fragile because there are a few layers of things
        # going on to make this work correctly for both XHR and WebSockets from any
        # node of the cluster, and to make the WebSockets case non-blocking (gevent). See also
        # socketio-server
        if not self._dispatch_message_to_proxy(session_id, name, msg_str):
            transactions.do(target=self,
                            call=self._publish_msg_to_redis,
                            args=(self.channel_name,
                                  pickle.dumps([session_id,
                                                name, msg_str], pickle.HIGHEST_PROTOCOL),))

    def queue_message_from_client(self, session_id, msg):
        self._put_msg('enqueue_message_from_client',
                      'server_queue', session_id, msg)
        self._publish_msg(b'queue_message_from_client',
                          session_id, json.dumps(msg))

    def queue_message_to_client(self, session_id, msg):
        self._put_msg('enqueue_message_to_client',
                      'client_queue', session_id, msg)
        self._publish_msg(b'queue_message_to_client', session_id, msg)

    def _get_msgs(self, q_name, session_id):
        queue_name = 'sessions/' + session_id + '/' + q_name
        # atomically read the current messages and then clear the state of the
        # queue.
        msgs, _ = self._redis.pipeline() \
                             .lrange( queue_name, 0, -1) \
                             .delete(queue_name) \
                             .execute()
        # If the transaction aborts, put these back so they don't get lost
        result = ()
        if msgs:  # lpush requires at least one message
            # By defaulting the success value to false, when called as a commit
            # hook with one parameter, we do the right thing, and also do the
            # right thing when called on abort with no parameter
            def after_commit_or_abort(success=False):
                if not success:
                    logger.info("Pushing messages back onto %s on abort",
                                queue_name)
                    msgs.reverse()
                    self._redis.lpush(queue_name, *msgs)
            transaction.get().addAfterCommitHook(after_commit_or_abort)
            transaction.get().addAfterAbortHook(after_commit_or_abort)
            # unwrap None encoding, decompress strings. The result is a generator
            # because it's very rarely actually used
            result = (None if not x else zlib.decompress(x) for x in msgs)
        return result

    def get_messages_to_client(self, session_id):
        """
        Removes and returns all available client messages from `session_id`,
        otherwise None.
        """
        return self._get_msgs('client_queue', session_id)

    def get_messages_from_client(self, session_id):
        """
        Removes and returns all available server messages from `session_id`,
        otherwise None.
        """
        return self._get_msgs('server_queue', session_id)

    # Redirect heartbeats through redis if possible. Note this is scuzzy and
    # not clean

    def _heartbeat_key(self, session_id):
        return 'sessions/' + session_id + '.heartbeat'

    def clear_disconnect_timeout(self, session_id, heartbeat_time=None):
        """
        Clears the disconnect timer for the given session by making it the current time.

        :param float heartbeat_time: If given, this is used instead of the current time
        """
        # Note that we don't make this transactional. The fact that we got a message
        # from a client is a good-faith indication the client is still around.
        key_name = self._heartbeat_key(session_id)
        self._redis.pipeline() \
                   .set(key_name, heartbeat_time or time.time()) \
                   .expire(key_name, self.SESSION_HEARTBEAT_TIMEOUT * 2) \
                   .execute()

    def get_last_heartbeat_time(self, session_id, session=None):
        # TODO: This gets called a fair amount. Do we need to cache?
        key_name = self._heartbeat_key(session_id)
        val = self._redis.get(key_name)
        result = float(val or '0')
        return result


# TODO: Find a better spot for this


@component.adapter(IUserNotificationEvent)
def _send_notification(user_notification_event):
    """
    Event handler that sends notifications to connected users.
    """
    dataserver = component.queryUtility(IDataserver)
    sessions = getattr(dataserver, 'session_manager', None)
    if sessions:
        for target in user_notification_event.targets:
            try:
                sessions.send_event_to_user(target,
                                            user_notification_event.name,
                                            *user_notification_event.args)
            except AttributeError:  # pragma: no cover
                raise
            except Exception:  # pragma: no cover
                logger.exception("Failed to send %s to %s",
                                 user_notification_event, target)


# FIXME: Do we even need/use this?
# We maintain some extra stats in redis about who has how many active sessions
# Note that this is non-transactional; that may be an issue in case of many conflicts?
# Have to try and see
_session_active_keys = 'sessions/active_sessions_set'


@component.adapter(ISocketSession, ISocketSessionConnectedEvent)
def _increment_count_for_new_socket(session, event):
    redis = component.getUtility(IRedisClient)
    redis.zincrby(_session_active_keys, session.owner, 1)


@component.adapter(ISocketSession, ISocketSessionDisconnectedEvent)
def _decrement_count_for_dead_socket(session, event):
    redis = component.getUtility(IRedisClient)
    if redis.zscore(_session_active_keys, session.owner):
        redis.zincrby(_session_active_keys, session.owner, -1)

deprecated('SessionServiceStorage', 'Use new session storage')
class SessionServiceStorage(Persistent):
    pass
