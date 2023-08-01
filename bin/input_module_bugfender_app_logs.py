
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
    interval = helper.get_arg("interval_days")
    if (interval is None):
        return
    try:
        int(interval)
    except ValueError:
        raise ValueError("Please enter a number")

def collect_events(helper, ew):
    import json
    import bugfender_import_data as bf
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
    import ndjson
    import pytz

    # check the checkpoint
    # get startdate from checkpoint
    most_recent_event_timestamp = bf.get_latest_timestamp(helper)
    most_recent_event_timestamp = bf.convert_latest_timestamp_to_string(most_recent_event_timestamp, helper)

    # get response from Bugfender API
    api_endpoint = "/logs/paginated"
    helper.log_debug(f"Starting to query data from enpoint {api_endpoint} to Splunk.")
    # response = bf.get_bugfender_data(helper, api_endpoint)
    # data = response.json()

    # debug
    log_list = bf.get_bugfender_data(helper, api_endpoint)
    
    helper.log_debug(f"Data received: {log_list} Starting to write data queried from enpoint {api_endpoint} to Splunk.")

    # initialize counters
    event_count = 0

    # for each response item ....
    for item in log_list:
        # convert Bugfender event timestamp from rfc3339 to utc
        timestamp_rfc3339 = item.get("time")
        timestamp_utc = bf.convert_rfc3339_to_utc(timestamp_rfc3339, helper)
        timestamp_utc_seconds = bf.convert_rfc3339_to_utc_total_seconds(timestamp_rfc3339, helper)

        # update most recent timestamp and event
        if (timestamp_utc >= most_recent_event_timestamp):
            most_recent_event_timestamp = timestamp_utc
        
        event = helper.new_event(data=json.dumps(item), time=timestamp_utc_seconds, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
        ew.write_event(event)
        event_count += 1

    helper.log_debug(f"Data queried from endpoint {api_endpoint} successfully written to Splunk. {event_count} events in total were indexed.")
    
    # bf.set_latest_timestamp(helper, most_recent_event_timestamp)