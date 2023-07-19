import sys
import os
import requests
import datetime
from datetime import datetime, timedelta
import time
import iso8601
import pytz
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import ndjson
import json

# code stolen from here: https://stackoverflow.com/questions/62764701/how-to-validate-that-a-string-is-a-time-in-rfc3339-format
def validate_rfc3339(date):
    if date is None:
        return
    try:
        assert datetime.strptime(date, '%Y-%m-%dT%H:%M:%S%z').tzinfo is not None
    except ValueError:
        raise ValueError("Incorrect data format, time should be YYYY-MM-DDThh:mm:ss:z")

# timestamp conversion. Based on: https://medium.com/@pritishmishra_72667/converting-rfc3339-timestamp-to-utc-timestamp-in-python-8dfa485358ff
def convert_rfc3339_to_utc(rfc333_date, helper):
    try:
        date_obj = iso8601.parse_date(rfc333_date)
        date_utc = date_obj.astimezone(pytz.utc)
    except Exception as e:
        helper.log_error(f"Something went wrong during timestamp conversion from rfc3339 to utc: {str(e)}")
        raise e
    return date_utc

def convert_datetime_to_rfc3339_and_add_second(utc_date, helper):
    try:
        date_obj = iso8601.parse_date(utc_date)
        date_obj = (date_obj + timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        helper.log_debug(f"Retreived date converted to {date_obj}, with one second being added.")
    except Exception as e:
        helper.log_error(f"Something went wrong during timestamp conversion from datetime object to rfc3339 string: {str(e)}")
        raise e
    return date_obj

# timestamp conversion. Based on: https://medium.com/@pritishmishra_72667/converting-rfc3339-timestamp-to-utc-timestamp-in-python-8dfa485358ff
def convert_rfc3339_to_utc_total_seconds(rfc333_date, helper):
    try:
        date_obj = iso8601.parse_date(rfc333_date)
        date_utc = date_obj.astimezone(pytz.utc)
        delta = date_utc - datetime(1970, 1, 1, tzinfo=pytz.utc)
    except Exception as e:
        helper.log_error(f"Something went wrong during timestamp conversion from rfc3339 to utc: {str(e)}")
        raise e
    return delta.total_seconds()

# function to hash strings. Taken from: https://stackoverflow.com/questions/27522626/hash-function-in-python-3-3-returns-different-results-between-sessions
def hash(text:str):
  hash = 0
  for ch in text:
    hash = (hash * 281 ^ ord(ch) * 997) & 0xFFFFFFFF
  return hash

def get_latest_timestamp(helper):
    lastest_timestamp_checkpoint_key = f"{helper.get_input_stanza_names()}_most_recent_timestamp"
    lastest_timestamp = helper.get_check_point(lastest_timestamp_checkpoint_key)
    helper.log_debug(f"[>] get_latest_timestamp() -> latest timestamp received: {lastest_timestamp}")
    return lastest_timestamp

def set_latest_timestamp(helper, timestamp_datetime):
    lastest_timestamp_checkpoint_key = f"{helper.get_input_stanza_names()}_most_recent_timestamp"
    timestamp_string = timestamp_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    helper.save_check_point(lastest_timestamp_checkpoint_key, timestamp_string)
    helper.log_debug(f"[-] set checkpoint with latest timestamp being {timestamp_string}")

def get_interval_days(helper):
    interval = helper.get_arg("interval_days")
    if (interval is None or interval == ""):
        return 5 # default days
    else:
        return int(interval)

# Acquire Bufender API access token
def get_bugfender_auth_token(account, helper):
    helper.log_debug("[>] get_bugfender_auth_token()")
    opt_username = account.get("username")
    opt_password = account.get("password")

    url = "https://dashboard.bugfender.com/auth/token"
    headers = {"Content-type": "application/x-www-form-urlencoded"}

    data = {
        "grant_type" : "client_credentials",
        "client_id" : opt_username,
        "client_secret" : opt_password
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
    except Exception as e:
        helper.log_error(f"POST Request to {url} failed: {str(e)}")
        raise e

    return response.json().get("access_token")

def update_header_with_new_auth_token(helper):
    auth_token = get_bugfender_auth_token(helper.get_arg("global_account"), helper)
    return {"Authorization": f"Bearer {auth_token}"}

 # perform API call
def make_api_call(url, headers, params, helper, endpoint, stream):
    helper.log_debug("[>] make_api_call()")
    helper.log_debug(f"Querying Bugfender API Endpoint {endpoint} with parameters {params}")
    try:
        response = requests.get(url, headers=headers, params=params, stream=stream)
        response.raise_for_status()
    except Exception as e:
        helper.log_error(f"GET Request to {url} failed: {str(e)}")
        raise e
    helper.log_debug(f"Data successfully retrieved from Bugfender API Endpoint {endpoint}.")

    return response

# convert ndjson to json. Code taken from here: https://stackoverflow.com/questions/54191861/how-to-specify-requests-to-return-data-as-json
def ndjson_to_json(ndjson, helper):
    helper.log_debug("[>] ndjson_to_json")
    result = []
    for s in ndjson.split("\n")[:-1]:
        result.append(json.loads(s))
    return result

def get_past_log_data(url, headers, params, helper, endpoint):
    helper.log_debug("[>] get_past_log_data()")
    DAYS_INTERVAL = get_interval_days(helper)

    range_end = datetime.utcnow()
    range_start = (range_end - timedelta(days=DAYS_INTERVAL))

    log_list = []

    response_text = None
    while(response_text != ""):
        params = {
            "date_range_start" : range_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "date_range_end" : range_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "format" : "ndjson"
        }

        auth_token = get_bugfender_auth_token(helper.get_arg("global_account"), helper)
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = make_api_call(url=url, headers=headers, params=params, helper=helper, endpoint=endpoint, stream=True)
        helper.log_debug("[>] returning to get_past_log_data() after make_api_call() has been called.")
        response_text = response.text
        if (response_text == ""):
            break
        helper.log_debug("[>] get_past_log_data() BEFORE ndjson to json conversion.")
        # data = response.json(cls=ndjson.Decoder)
        data = ndjson_to_json(response_text, helper)
        helper.log_debug("[>] get_past_log_data() AFTER ndjson to json conversion.")
        helper.log_debug(f"Received {len(data)} log events.")
        log_list += data
        range_end = (range_start - timedelta(seconds=1)) # one second gap
        range_start = (range_end - timedelta(days=DAYS_INTERVAL))

    return log_list

def get_bugfender_issues_data(url, headers, params, helper):
    helper.log_debug("[>] get_bugfender_issues_data()")
    issue_status = helper.get_arg("issue_status")
    params["issue_status"] = 4 if issue_status == "issue_status_closed" else 1
    page_size = helper.get_arg("page_size")
    if page_size is None:
        page_size = 100
    params["page_size"] = page_size
    params["version"] = -1 # API Call only returns issues when this is set to -1

    total_issues = []

    # setting the amount of total pages to 1, later
    # in the for loop, this value will get updates with
    # the actual total_pages value
    page = 1
    total_pages = 1 # initial value, to be changed inside while loop below
    total_pages_updated = False

    while(page <= total_pages):
        # make api call
        # get Bugfender Auth token
        auth_token = get_bugfender_auth_token(helper.get_arg("global_account"), helper)
        headers = {"Authorization": f"Bearer {auth_token}"}
        params["page"] = page
        response = make_api_call(url, headers, params, helper, "/issues", stream=False)
        response = response.json()

        # update total pages
        if not total_pages_updated:
            total_pages = response.get("total_pages")
            total_pages_updated = True

        # log debug statements
        item_count = response.get("item_count")
        page_index = response.get("page_index")
        helper.log_debug(f"/issues response - item_count: {item_count}, page_index: {page_index}, total_pages: {total_pages}")

        # append issue list to resulting list
        issues = response.get("issues")
        # for issue in issues:
        #    total_issues.append(issue)
        total_issues += issues
        page = page + 1

    return total_issues

def get_past_bugfender_issues_data(url, headers, helper):
    helper.log_debug("[>] get_past_bugfender_issues_data()")
    DAYS_INTERVAL = get_interval_days(helper)

    range_end = datetime.utcnow()
    range_start = (range_end - timedelta(days=DAYS_INTERVAL))

    issues_list = []
    response_empty = False
    while not response_empty:
        params = {
            "date_range_start" : range_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "date_range_end" : range_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }

        auth_token = get_bugfender_auth_token(helper.get_arg("global_account"), helper)
        headers = {"Authorization": f"Bearer {auth_token}"}
        response_list = get_bugfender_issues_data(url, headers, params, helper)
        if (not response_list):
            response_empty = True
            break
        issues_list += response_list
        range_end = (range_start - timedelta(seconds=1)) # one second gap
        range_start = (range_end - timedelta(days=DAYS_INTERVAL))

    return issues_list

def get_bugfender_devices_endpoint_data(url, headers, params, helper):
    helper.log_debug("[>] get_bugfender_devices_endpoint_data()")
    # set format to parameters
    params["format"] = "json"
    params["order"] = helper.get_arg("order")

    # set page size
    if (helper.get_arg("page_size")):
        params["page_size"] = helper.get_arg("page_size")
    # DEBUG
    else:
        params["page_size"] = "100" # default value

    total_devices = []

    # The /devices endpoint works with pagination, therefore multiple API calls are performed.
    # If the overall process is taking longer than one hour, the access token expires. Therefore,
    # we are tracking the time. 
    query_start_time = time.time()

    next_cursor = "start" # intial value to enter while loop below

    while next_cursor != "":
        if (next_cursor != "start"):
            params["next_cursor"] = next_cursor

        # when 45 minutes (2700 seconds) are passed, get new access token
        # and reset the timer
        if (time.time() - query_start_time > 2700):
            helper.log_debug("[>] get_bugfender_devices_endpoint_data() - 45 Minutes have passed, acquiring new access token.")
            headers = update_header_with_new_auth_token(helper)
            query_start_time = time.time()
        
        # DEBUG
        time.sleep(2)

        response = make_api_call(url, headers, params, helper, "/devices", stream=False)
        response = response.json()

        next_cursor = response.get("next_cursor")

        # append issue list to resulting list
        devices = response.get("devices")
        if devices:
            helper.log_debug(f"Response - Received {len(devices)} devices.")
            for device in devices:
                total_devices.append(device)

    return total_devices

def get_bugfender_endpoint_data(auth_token, endpoint, helper):
    helper.log_debug("[>] get_bugfender_endpoint_data()")
    # get user input
    app_id = helper.get_arg("app_id")
    start_date = helper.get_arg("start_date")
    end_date = helper.get_arg("end_date")

    # construct URL
    base_url = f"https://dashboard.bugfender.com"
    url = base_url + f"/api/app/{app_id}" + endpoint
    if (endpoint == "/api/app"):
        url = base_url + endpoint

    # Use acquired auth token
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Configure parameters - time interval
    params = {}
    if start_date is not None:
        params["date_range_start"] = start_date
    if end_date is not None:
        params["date_range_end"] = end_date

    # If we are dealing with /logs/download and /devices endpoints,
    # check if we have any most recent timestamp stored
    last_timestamp = get_latest_timestamp(helper)

    if (last_timestamp is None and endpoint == "/logs/download"):
        return get_past_log_data(url, headers, params, helper, endpoint)
    elif (last_timestamp and endpoint == "/logs/download"):
        params["date_range_start"] = datetime.strptime(last_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        params["date_range_end"] = None

    if (last_timestamp is None and endpoint == "/issues"):
        return get_past_bugfender_issues_data(url, headers, helper)
    elif (last_timestamp and endpoint == "/issues"):
        params["date_range_start"] = datetime.strptime(last_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        params["date_range_end"] = None

    # If the endpoint is '/issues' (which uses pagination), the
    # API Call is handled in a special way, represented by the
    # 'get_bugfender_issues_endpoint_data' function
    if (endpoint == "/issues"):
        return get_bugfender_issues_data(url, headers, params, helper)
    elif (endpoint == "/devices"):
        return get_bugfender_devices_endpoint_data(url, headers, params, helper)
    elif (endpoint == "/logs/download"):
        params["format"] = "ndjson"

    # perform API call
    response = make_api_call(url, headers, params, helper, endpoint, stream=False)
    return response

def get_bugfender_data(helper, bugfender_api_endpoint):
    # get Bugfender Auth token
    auth_token = get_bugfender_auth_token(helper.get_arg("global_account"), helper)

    # get Bugfender data with the help of the auth token
    response = get_bugfender_endpoint_data(auth_token, bugfender_api_endpoint, helper)

    return response

