import urllib.request
import urllib.error
import json

def test_url(url):
    print(f"\nTesting URL: {url}")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"Success! Status code: {response.getcode()}")
            print(f"Content-Type: {response.info().get_content_type()}")
            body = response.read().decode('utf-8')
            print(f"Body Length: {len(body)}")
            try:
                data = json.loads(body)
                print("Successfully parsed JSON!")
                if isinstance(data, list):
                    print(f"Count: {len(data)}")
                    if data:
                        print("First item preview:")
                        print(json.dumps(data[0], indent=2)[:500])
                else:
                    print(f"Data type: {type(data)}")
            except Exception as je:
                print(f"JSON Parse Error: {je}")
                print(f"Preview: {body[:300]}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} - {e.reason}")
        try:
            body = e.read().decode('utf-8')
            print(f"Error body preview: {body[:300]}")
        except Exception:
            pass
    except Exception as e:
        print(f"Other Error: {e}")

test_url("https://careers-hcsgcorp.icims.com/jobs/search?pr=0&in_iframe=1&format=json")
