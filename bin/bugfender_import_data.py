import sys
import requests
import datetime
from datetime import timedelta
import iso8601
import pytz

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
        delta = date_utc - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
    except Exception as e:
        helper.log_error(f"Something went wrong during timestamp conversion from rfc3339 to utc: {str(e)}")
        raise e
    return delta.total_seconds()

def check_response_status(url, response, helper):
    if(response.status_code != 200):
        msg = f"API Request to {url} returned code {response.status_code}: {response.text}"
        helper.log_error(msg)
        sys.exit(msg)

# Acquire Bufender API access token
def get_bugfender_auth_token(account, helper):
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
    except Exception as e:
        helper.log_error(f"POST Request to {url} failed: {str(e)}")
        raise e

    check_response_status(url, response, helper)

    return response.json().get("access_token")

 # perform API call
def make_api_call(url, headers, params, helper, endpoint):
    helper.log_debug(f"Querying Bugfender API Endpoint {endpoint}.")
    try:
        response = requests.get(url, headers=headers, params=params)
    except Exception as e:
        helper.log_error(f"GET Request to {url} failed: {str(e)}")
        raise e
    check_response_status(url, response, helper)
    helper.log_debug(f"Data successfully retrieved from Bugfender API Endpoint {endpoint}.")

    return response


def get_bugfender_issues_endpoint_data(url, headers, params, helper):
    issue_status = helper.get_arg("issue_status")
    params["issue_status"] = 4 if issue_status == "issue_status_closed" else 1
    params["page_size"] = 100
    params["version"] = -1 # API Call only returns issues when this is set to -1

    total_issues = []

    # setting the amount of total pages to 1, later
    # in the for loop, this value will get updates with
    # the actual total_pages value
    page = 1
    total_pages = 1 # initial value, to be changed inside while loop below
    total_pages_updated = False

    while page <= total_pages:
        # make api call 
        helper.log_debug(f"Querying Bugfender API Endpoint /issues with params: {params}")
        params["page"] = page
        response = make_api_call(url, headers, params, helper, "/issues")
        response = response.json()

        # update total pages
        if not total_pages_updated:
            total_pages = response.get("total_pages")
            total_pages_updated = True

        # log debug statements
        item_count = response.get("item_count")
        page_index = response.get("page_index")
        helper.log_debug(f"Response - item_count: {item_count}, page_index: {page_index}, total_pages = {total_pages}")

        # append issue list to resulting list
        issues = response.get("issues")
        for issue in issues: 
            total_issues.append(issue)

        page = page + 1

    return total_issues
    

def get_bugfender_endpoint_data(auth_token, endpoint, helper, logs_last_time_stamp):
    # get user input
    app_id = helper.get_arg("app_id")
    start_date = helper.get_arg("start_date")
    end_date = helper.get_arg("end_date")

    # construct URL
    base_url = f"https://dashboard.bugfender.com"
    url = base_url + f"/api/app/{app_id}" + endpoint
    if(endpoint == "/api/app"):
        url = base_url + endpoint
    
    # Use acquired auth token 
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Configure parameters - time interval
    params = {}
    if start_date is not None:
        params["date_range_start"] = start_date
    if end_date is not None:
        params["date_range_end"] = end_date
    if start_date is None and end_date is None and logs_last_time_stamp is not None:
        helper.log_debug(f"Adding timestamp {logs_last_time_stamp} as parameter to API call.")
        params["date_range_start"] = logs_last_time_stamp

    # If the endpoint is '/issues' (which uses pagination), the 
    # API Call is handled in a special way, represented by the 
    # 'get_bugfender_issues_endpoint_data' function
    if(endpoint == "/issues"):
        return get_bugfender_issues_endpoint_data(url, headers, params, helper)

    # Configure parameters - formating
    if(endpoint == "/logs/download"):
        params["format"] = "ndjson"
    elif(endpoint == "/devices"):
        params["format"] = "json"

    # perform API call
    response = make_api_call(url, headers, params, helper, endpoint)
    return response

def get_bugfender_data(helper, bugfender_api_endpoint, logs_last_time_stamp):
    # get Bugfender Auth token
    auth_token = get_bugfender_auth_token(helper.get_arg("global_account"), helper)

    # get Bugfender data with the help of the auth token
    response = get_bugfender_endpoint_data(auth_token, bugfender_api_endpoint, helper, logs_last_time_stamp)

    return response
