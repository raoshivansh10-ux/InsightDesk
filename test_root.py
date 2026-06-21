import urllib.request
import urllib.error

try:
    with urllib.request.urlopen('http://127.0.0.1:5000/') as response:
        print("Status:", response.status)
        print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print(e.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
