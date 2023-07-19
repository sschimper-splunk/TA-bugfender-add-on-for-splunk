
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
    # last_timestamp_checkpoint_key = f"{helper.get_input_stanza_names()}_most_recent_timestamp"
    # last_timestamp = helper.get_check_point(last_timestamp_checkpoint_key)

    last_timestamp = bf.get_latest_timestamp(helper)
    helper.log_debug(f"[-] last timestamp: {last_timestamp}")

    # convert timestamp to rfc3339-compliant string to use in API call
    # start_date = None
    # if last_timestamp is not None:
    #    start_date = bf.convert_datetime_to_rfc3339_and_add_second(last_timestamp, helper)

    # get response from Bugfender API
    api_endpoint = "/logs/download"
    helper.log_debug(f"Starting to query data from enpoint {api_endpoint} to Splunk.")
    response = bf.get_bugfender_data(helper, api_endpoint)

    # convert response from ndsjon string to Python list of Python doctionaries
    if (type(response) == list):
        formatted_data = response
    else:
        formatted_data = response.json(cls=ndjson.Decoder)
    
    helper.log_debug(f"Data received. Starting to write data queried from enpoint {api_endpoint} to Splunk.")

    # initialize counters
    event_count = 0

    # Retrieve latest saved timestamp, if it is None, use date far in the past
    if last_timestamp is not None:
        most_recent_event_timestamp = datetime.datetime.strptime(last_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
    else:
        most_recent_event_timestamp = datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
    most_recent_event = None

    # for each response item ....
    for item in formatted_data:
        # convert Bugfender event timestamp from rfc3339 to utc
        timestamp_rfc3339 = item.get("timestamp")
        timestamp_utc = bf.convert_rfc3339_to_utc(timestamp_rfc3339, helper)
        timestamp_utc_seconds = bf.convert_rfc3339_to_utc_total_seconds(timestamp_rfc3339, helper)

        # update most recent timestamp and event
        if (timestamp_utc >= most_recent_event_timestamp):
            most_recent_event_timestamp = timestamp_utc
            most_recent_event = item
 
        event = helper.new_event(data=json.dumps(item), time=timestamp_utc_seconds, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
        ew.write_event(event)
        event_count += 1

    helper.log_debug(f"Data queried from endpoint {api_endpoint} successfully written to Splunk. {event_count} events in total were indexed.")

    # save most recent date
    # helper.save_check_point(last_timestamp_checkpoint_key, most_recent_event_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"))
    
    helper.log_debug(f"most recent event: {most_recent_event}")
    bf.set_latest_timestamp(helper, most_recent_event_timestamp)