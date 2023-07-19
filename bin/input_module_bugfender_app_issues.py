
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
    import pytz

    # get response from Bugfender API
    api_endpoint = "/issues"
    issues_list = bf.get_bugfender_data(helper, api_endpoint)

    event_count = 0
    last_timestamp = bf.get_latest_timestamp(helper)
    helper.log_debug(f"[-] last timestamp: {last_timestamp}")

    # Retrieve latest saved timestamp, if it is None, use date far in the past
    if last_timestamp is not None:
        most_recent_event_timestamp = datetime.datetime.strptime(last_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
    else:
        most_recent_event_timestamp = datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
    most_recent_event = None

    # for each issue...
    for issue in issues_list:
        # convert Bugfender event timestamp from rfc3339 to utc to use with the event
        timestamp_rfc3339 = issue.get("created_at")
        timestamp_utc = bf.convert_rfc3339_to_utc(timestamp_rfc3339, helper)
        timestamp_utc_seconds = bf.convert_rfc3339_to_utc_total_seconds(timestamp_rfc3339, helper)

        # update most recent timestamp and event
        if (timestamp_utc >= most_recent_event_timestamp):
            most_recent_event_timestamp = timestamp_utc
            most_recent_event = issue

        event = helper.new_event(source=helper.get_input_type(), time=timestamp_utc_seconds, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(issue))
        ew.write_event(event)
        event_count += 1

    helper.log_debug(f"Data queried from endpoint {api_endpoint} successfully written to Splunk. {event_count} events in total were indexed.")

    helper.log_debug(f"most recent event: {most_recent_event}")
    bf.set_latest_timestamp(helper, most_recent_event_timestamp)