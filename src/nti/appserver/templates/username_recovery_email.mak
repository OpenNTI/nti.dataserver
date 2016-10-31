Hello ${users[0].username}.

You are receiving this notification because you (or someone pretending
to be you) requested a reminder of the NextThought username associated
with this email address on ${request.application_url}.

We found the following usernames associated with this email address:
% for user in users:
     ${user.username}
% endfor

If you did not request this reminder, you can safely disregard this email.

For help, you can email us at support@nextthought.com.

Sincerely,
NextThought
