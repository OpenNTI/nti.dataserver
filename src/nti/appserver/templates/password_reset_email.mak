Hello ${user.username}.

%if not remote_user:
You are receiving this notification because you (or someone pretending
to be you) requested your ${request.application_url} password be reset for
${user.username}.
%endif

%if remote_user:
You are receiving this notification because

	%if remote_user_is_super_admin:
	an Administrator
	%endif

	%if not remote_user_is_super_admin:
	${remote_user_display_name}
	%endif

requested your ${request.application_url} password be reset for
${user.username}.
%endif

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

If you did not make this request, you can safely disregard this email.

For help, you can email us at ${support_email}.
