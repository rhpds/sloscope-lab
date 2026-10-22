"""Generate real HTTP traffic against the isolated controlled checkout workload."""
import time
from urllib.request import urlopen
from urllib.error import HTTPError,URLError

if __name__=='__main__':
    while True:
        try:
            with urlopen('http://checkout-api:8081/checkout',timeout=5) as response:
                response.read()
        except HTTPError as response:
            response.read()  # A deliberate 503 is a measured sample, not a generator crash.
        except (URLError,TimeoutError,OSError):
            time.sleep(1)
        time.sleep(.2)
