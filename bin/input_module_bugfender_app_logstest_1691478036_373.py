
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
    pass

def collect_events(helper, ew):
    import json
    import bugfender_import_data as bf
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

    log_list = bf.get_bugfender_app_logs(helper)

    event_count = 0
    for item in log_list:
        timestamp_rfc3339 = item.get("timestamp")
        timestamp_utc_seconds = bf.convert_rfc3339_to_utc_total_seconds(timestamp_rfc3339, helper)
        event = helper.new_event(data=json.dumps(item), time=timestamp_utc_seconds, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
        ew.write_event(event)
        event_count += 1

    helper.log_debug(f"Modular input {helper.get_input_type()} terminated successfully! {event_count} events in total were indexed. Most recent timestamp: {most_recent_event_timestamp}")