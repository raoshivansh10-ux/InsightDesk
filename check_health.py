import sys
import urllib.request
import urllib.error

def check_url(url, service_name):
    print(f"Checking {service_name} at {url}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.status
            print(f"  [OK] {service_name} is UP! Response status: {status}")
            return True
    except urllib.error.HTTPError as e:
        # Some endpoints might return 401 or 404 but are still listening
        print(f"  [OK] {service_name} is UP! (HTTP Error {e.code})")
        return True
    except urllib.error.URLError as e:
        print(f"  [FAIL] {service_name} is DOWN! Error: {e.reason}")
        return False
    except Exception as e:
        print(f"  [FAIL] {service_name} is DOWN! Error: {str(e)}")
        return False

def main():
    print("==================================================")
    print("             InsightDesk Health Status            ")
    print("==================================================")
    
    frontend_up = check_url("http://localhost:5173/", "Frontend")
    backend_up = check_url("http://localhost:5000/", "Backend")
    
    print("==================================================")
    if frontend_up and backend_up:
        print("STATUS: GREEN - ALL SERVICES RUNNING SUCCESSFULLY")
        sys.exit(0)
    else:
        print("STATUS: RED - SOME SERVICES ARE DOWN")
        sys.exit(1)

if __name__ == '__main__':
    main()
