${report_type} from ${userid}:


    ${filled_body}

%if request_info_table:
Request Information
===================

    ${request_info_table}
%endif

%if request_details_table:
Request Details
===============

    ${request_details_table}
%endif
