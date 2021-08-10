Hello ${user.username}.

You are receiving this notification because an admin requested your ${request.application_url} password be reset for
${user.username}.

%if not external_reset_url:
To reset your password, follow these steps within one hour of
receiving this notification:

1. Click the link below to open a new and secure browser window.
2. Enter the requested information and follow the instructions to reset your password.

Reset your password here:
${reset_url}
%endif

%if external_reset_url:
Please click the link below and follow the instructions in
order to reset your password.

Reset your password here:
${external_reset_url}
%endif

If you are uncertain about this request, please contact your site admin.

For help, you can email us at ${support_email}.
