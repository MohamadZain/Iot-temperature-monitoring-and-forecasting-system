# Import OAuth libraries for authentication with Arduino Cloud
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

# Import Arduino IoT Cloud API client libraries
import iot_api_client as iot
from iot_api_client.rest import ApiException
from iot_api_client.configuration import Configuration
from iot_api_client.api import ThingsV2Api, PropertiesV2Api, SeriesV2Api
from iot_api_client.models import *

# Import utilities
import csv              # For saving data to CSV file
from time import sleep # To avoid API rate limits

# Arduino Cloud API endpoints
HOST = "https://api2.arduino.cc"
TOKEN_URL = "https://api2.arduino.cc/iot/v1/clients/token"

# 🔐 API Credentials (obtained from Arduino Cloud)
client_id = "Vy4EoUypN4a5g280YfodsY7JEff8XcAZ"
client_secret = "7FoBhdgTHaioiwLB7oh0Q4lbrq5OIwlwnvloJlG74JFpExdVS5DRp3aSLB5fJrUW"

# 🏢 Organization / Space ID
org_id = "8a697149-a271-4a3e-9061-6575303ab06b"

# 📅 Time range for fetching historical data
extract_from = "2026-03-20T00:00:00Z"
extract_to   = "2026-03-24T23:59:59Z"

# 📁 Output CSV file name
filename = "output.csv"


# 🔑 Function to generate access token using OAuth2
def get_token():
    oauth_client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=oauth_client)

    # Request access token from Arduino Cloud
    token = oauth.fetch_token(
        token_url=TOKEN_URL,
        client_id=client_id,
        client_secret=client_secret,
        include_client_id=True,
        audience="https://api2.arduino.cc/iot",
        headers={"X-Organization": org_id}
    )
    return token


# 🔧 Initialize API client using the access token
def init_client(token):
    client_config = Configuration(HOST)
    client_config.access_token = token.get("access_token")

    # Create API client with organization header
    client = iot.ApiClient(
        client_config,
        header_name="X-Organization",
        header_value=org_id
    )
    return client


# 📊 Fetch and display time-series data for a specific property
def dump_property_data(client, thing_name, prop_name, prop_id):
    sleep(1)  # Prevent API overload

    print(f"\n--- {thing_name} | {prop_name} ---")

    series_api = SeriesV2Api(client)

    # Create request for time-series data
    propertyRequest = BatchQueryRawRequestMediaV1(
        q="property." + prop_id,
        var_from=extract_from,
        to=extract_to
    )

    # Wrap request in batch format
    seriesRequest = BatchQueryRawRequestsMediaV1(
        resp_version=1,
        requests=[propertyRequest]
    )

    # Fetch data from Arduino Cloud
    timeseries = series_api.series_v2_batch_query_raw(seriesRequest)

    try:
        # Loop through all returned data points
        for s in timeseries.responses:
            for i in range(len(s.times)):
                time = s.times[i]     # Timestamp
                value = s.values[i]   # Sensor value

                # 🖨️ Print data (for screenshot/output)
                print(f"Time: {time} | {prop_name}: {value}")

                # 💾 Save data to CSV file
                writer.writerow([thing_name, prop_name, time, value])

    except ApiException as e:
        print("Error:", e)


# 🔍 Fetch all Things and filter only the required one
def get_things_and_props():
    token = get_token()          # Get access token
    client = init_client(token)  # Initialize API client

    things_api = ThingsV2Api(client)
    properties_api = PropertiesV2Api(client)

    # 🎯 Target only your specific Thing
    TARGET_THING_NAME = "Group 10"

    try:
        # Get list of all Things
        things = things_api.things_v2_list()

        for thing in things:
            # Skip all other Things
            if thing.name != TARGET_THING_NAME:
                continue

            print(f"\nFound Target Thing: {thing.name}")

            # Get properties (variables) of the selected Thing
            properties = properties_api.properties_v2_list(
                id=thing.id,
                show_deleted=False
            )

            # Loop through properties
            for prop in properties:
                # Only process numeric data (FLOAT or INT)
                if prop.type in ["FLOAT", "INT"]:
                    dump_property_data(
                        client,
                        thing.name,
                        prop.name,
                        prop.id
                    )

    except ApiException as e:
        print("Error:", e)


# 🚀 MAIN EXECUTION BLOCK
# Open CSV file and write header
with open(filename, 'w', newline='') as outfile:
    writer = csv.writer(outfile)

    # CSV column headers
    writer.writerow(["thing_name", "variable", "timestamp", "value"])

    # Start data extraction
    get_things_and_props()