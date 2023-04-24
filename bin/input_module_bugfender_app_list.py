
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
    pass

def collect_events(helper, ew):
    import json
    import bugfender_import_data as bf
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
    
    # get response from Bugfender API
    api_endpoint = "/api/app"
    response = bf.get_bugfender_data(helper, api_endpoint, None)

    # format response
    formatted_data = response.json()

    # for each response item ....
    for item in formatted_data:
        event = helper.new_event(data=json.dumps(item), time=None, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
        ew.write_event(event)
    helper.log_debug(f"Response from Bugfender endpoint {api_endpoint} successfully written to Splunk.")
