import requests
import os
import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

SPEEDPORT_URL = os.getenv("SPEEDPORT_URL", "http://192.168.2.1")
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "speedport")
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "3600"))

STATUS_URL = f"{SPEEDPORT_URL}/data/Status.json"

def validate_influx_env():
    """Raise error if required InfluxDB env vars are missing"""
    missing = []
    if not INFLUX_URL:
        missing.append("INFLUX_URL")
    if not INFLUX_TOKEN:
        missing.append("INFLUX_TOKEN")
    if not INFLUX_ORG:
        missing.append("INFLUX_ORG")
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

def get_dsl_info():
    r = requests.get(STATUS_URL, timeout=5)
    r.raise_for_status()
    items = r.json()

    result = {}
    for item in items:
        if item.get("vartype") != "value" and item.get("vartype") != "status":
            continue
        vid = item.get("varid")
        if vid == "dsl_downstream":
            result['downstream'] = int(item.get("varvalue", "0"))
        elif vid == "dsl_upstream":
            result['upstream'] = int(item.get("varvalue", "0"))
        elif vid == "dsl_link_status":
            result['link'] = str(item.get("varvalue", "")) == "online"
        elif vid == "onlinestatus":
            result['online'] = str(item.get("varvalue", "")) == "online"
        elif vid == "status":
            result['connected'] = str(item.get("varvalue", "")) == "online"

    return result

def write_to_influx(data):
    validate_influx_env()
    
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    point = (Point("dsl_status")
             .tag("host", "speedport")
             .field("downstream", data.get("downstream", 0))
             .field("upstream", data.get("upstream", 0))
             .field("link", data.get("link", False))
             .field("online", data.get("online", False))
             .field("connected", data.get("connected", False)))
    
    write_api.write(bucket=INFLUX_BUCKET, record=point)
    client.close()

if __name__ == "__main__":
    print(f"Starting DSL monitor - interval: {LOOP_INTERVAL}s")
    while True:
        try:
            try: 
                result = get_dsl_info()
            except Exception as e:
                print(f"Error: {e}")
                result = {}
            print(result)
            write_to_influx(result)
            print(f"Sleeping for {LOOP_INTERVAL} seconds...")
            time.sleep(LOOP_INTERVAL)
        except KeyboardInterrupt:
            print("\nStopped by user")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(LOOP_INTERVAL)
