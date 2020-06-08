Hi ${display_name}!

${notable.creator} mentioned you in a recent post in ${notable.__parent__.display_name()}:

"${notable.snippet}"

View online: ${notable.href}

If you have any questions, feel free to message us at ${support_email}.

% if unsubscribe_link:
You currently receive periodic email updates at ${email_to} for ${site_name} activity.
Unsubscribe: ${unsubscribe_link}
% endif