
# encoding = utf-8

import os
import sys
import time
import datetime

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    import bugfender_import_data as bf
    bf.validate_rfc3339(helper.get_arg("start_date"))
    bf.validate_rfc3339(helper.get_arg("end_date"))

def collect_events(helper, ew):
    import json
    import bugfender_import_data as bf
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

    issues_list = bf.get_bugfender_app_issues(helper)

    event_count = 0
    for issue in issues_list:
        timestamp_rfc3339 = issue.get("created_at")
        timestamp_utc_seconds = bf.convert_rfc3339_to_utc_total_seconds(timestamp_rfc3339, helper)

        event = helper.new_event(source=helper.get_input_type(), time=timestamp_utc_seconds, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(issue))
        ew.write_event(event)
        event_count += 1

    helper.log_debug(f"Modular input {helper.get_input_type()} terminated successfully! {event_count} events in total were indexed.")