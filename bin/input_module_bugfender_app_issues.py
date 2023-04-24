
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

    # get response from Bugfender API
    api_endpoint = "/issues"
    issue_list = bf.get_bugfender_data(helper, api_endpoint, None)

    duplicate_count = 0

    # for each issue...
    for issue in issue_list:
        # convert Bugfender event timestamp from rfc3339 to utc to use with the event
        timestamp_rfc3339 = issue.get("created_at")
        timestamp_utc_seconds = bf.convert_rfc3339_to_utc_total_seconds(timestamp_rfc3339, helper)

        # ... check if event is already been indexed, use timestamp field as key...
        checkpoint_key = f"{helper.get_input_stanza_names()}_{timestamp_rfc3339}"
        state = helper.get_check_point(checkpoint_key)

        if state is None:
            event = helper.new_event(source=helper.get_input_type(), time=timestamp_utc_seconds, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(issue))
            ew.write_event(event)
            helper.save_check_point(checkpoint_key, "indexed")
        else:
            duplicate_count = duplicate_count + 1

    helper.log_debug(f"Response from Bugfender endpoint {api_endpoint} successfully written to Splunk. {duplicate_count} duplicate events were encountered and skipped.")
