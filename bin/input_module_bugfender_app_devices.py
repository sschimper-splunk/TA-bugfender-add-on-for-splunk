
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
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    # app_id = definition.parameters.get('app_id', None)
    # start_date = definition.parameters.get('start_date', None)
    # end_date = definition.parameters.get('end_date', None)
    pass

def collect_events(helper, ew):
    import json
    import bugfender_import_data as bf
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
    
    # get response from Bugfender API
    api_endpoint = "/devices"
    response = bf.get_bugfender_data(helper, api_endpoint, None)

    # format response
    formatted_data = response.json()

    duplicate_count = 0

    # for each response item ....
    for device in formatted_data.get("devices"):
        # ... check if event is already been indexed, use timestamp field as key
        device_id = device.get("id")
        checkpoint_key = f"{helper.get_input_stanza_names()}_{device_id}"
        state = helper.get_check_point(checkpoint_key)

        # if not, write to Splunk
        if state is None:
            event = helper.new_event(data=json.dumps(device), time=None, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
            ew.write_event(event)
            helper.save_check_point(checkpoint_key, "indexed")
        else:
            duplicate_count = duplicate_count + 1

    helper.log_debug(f"Response from Bugfender endpoint {api_endpoint} successfully written to Splunk. {duplicate_count} duplicate events were encountered and skipped.")
    