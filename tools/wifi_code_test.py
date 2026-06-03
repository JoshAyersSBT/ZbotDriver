import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def run(cmd, timeout=30):
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip())
    if proc.returncode != 0:
        raise RuntimeError("command failed: {}".format(" ".join(str(x) for x in cmd)))
    return proc.stdout


def mpremote(args, command, timeout=30):
    return run([args.mpremote, "connect", args.port] + command, timeout=timeout)


def deploy(args):
    print("== deploy runtime files to {} ==".format(args.port))
    try:
        mpremote(args, ["mkdir", "robot"], timeout=30)
    except Exception:
        pass

    files = [
        ("main.py", ":main.py"),
        ("boot.py", ":boot.py"),
        ("robot/config.py", ":robot/config.py"),
        ("robot/wifi_code.py", ":robot/wifi_code.py"),
        ("robot/debug_io.py", ":robot/debug_io.py"),
        ("robot/error_report.py", ":robot/error_report.py"),
    ]
    for local, remote in files:
        mpremote(args, ["cp", str(ROOT / local), remote], timeout=20)


def serial_tests(args):
    print("== serial MicroPython tests on {} ==".format(args.port))
    snippet = r'''
import os
from robot import wifi_code as w

errors = []

def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        errors.append(name)

path, query = w._parse_query("/upload?path=%2Fuser_main.py&reset=1")
check("parse path", path == "/upload")
check("parse query path", query.get("path") == "/user_main.py")
check("parse query reset", query.get("reset") == "1")
check("url decode", w._url_decode("hello+%57iFi%21") == "hello WiFi!")
check("default path", w._sanitize_path("") == "/user_main.py")
check("relative path", w._sanitize_path("code.py") == "/code.py")

try:
    w._sanitize_path("/bad/../path.py")
    check("reject parent path", False)
except ValueError:
    check("reject parent path", True)

srv = w.WifiCodeServer(ap_enabled=False, sta_ssid="", token="secret")
check("auth query", srv._authorized({"token": "secret"}, {}))
check("auth header", srv._authorized({}, {"x-zbot-token": "secret"}))
check("auth form", srv._authorized({}, {}, {"token": "secret"}))
check("auth reject", not srv._authorized({}, {}))

test_path = "/wifi_code_serial_test.txt"
tmp_path = test_path + ".part"
try:
    os.remove(test_path)
except OSError:
    pass
try:
    os.remove(tmp_path)
except OSError:
    pass

fp = open(tmp_path, "wb")
fp.write(b"serial-ok")
fp.close()
srv._commit(tmp_path, test_path)
fp = open(test_path, "rb")
data = fp.read()
fp.close()
check("commit content", data == b"serial-ok")
try:
    os.remove(test_path)
except OSError:
    pass

if errors:
    raise RuntimeError(",".join(errors))
print("SERIAL_TESTS_OK")
'''
    out = mpremote(args, ["exec", snippet], timeout=30)
    if "SERIAL_TESTS_OK" not in out:
        raise RuntimeError("serial tests did not report success")


def http_request(url, data=None, token=""):
    headers = {}
    if token:
        headers["X-Zbot-Token"] = token
    request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urlopen(request, timeout=12) as response:
        return response.read().decode(errors="replace")


def http_tests(args):
    if not args.url:
        print("== HTTP tests skipped: pass --url http://ROBOT_IP:8080 to enable ==")
        return

    print("== HTTP tests against {} ==".format(args.url))
    base = args.url.rstrip("/")
    status = http_request(base + "/status")
    print(status.strip())
    if not status.startswith("OK "):
        raise RuntimeError("bad /status response")

    query = {"path": "/wifi_code_http_test.txt"}
    if args.token:
        query["token"] = args.token
    body = b"http-upload-ok"
    upload_url = base + "/upload?" + urlencode(query)
    result = http_request(upload_url, data=body, token=args.token)
    print(result.strip())
    if "OK uploaded" not in result:
        raise RuntimeError("bad /upload response")

    verify = r'''
import os
path = "/wifi_code_http_test.txt"
fp = open(path, "rb")
data = fp.read()
fp.close()
print("HTTP_FILE", data)
if data != b"http-upload-ok":
    raise RuntimeError("http upload content mismatch")
os.remove(path)
print("HTTP_TESTS_OK")
'''
    out = mpremote(args, ["exec", verify], timeout=20)
    if "HTTP_TESTS_OK" not in out:
        raise RuntimeError("HTTP upload verification failed")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Test ZebraBot Wi-Fi code upload support.")
    parser.add_argument("--port", default="COM7", help="Serial port for mpremote")
    parser.add_argument(
        "--mpremote",
        default=str(ROOT / ".venv" / "Scripts" / "mpremote.exe"),
        help="Path to mpremote executable",
    )
    parser.add_argument("--deploy", action="store_true", help="Copy updated runtime files to the board first")
    parser.add_argument("--url", default="", help="Optional robot URL, for example http://192.168.4.1:8080")
    parser.add_argument("--token", default="", help="Optional WIFI_CODE_TOKEN for HTTP tests")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.deploy:
        deploy(args)
    serial_tests(args)
    http_tests(args)
    print("WIFI_CODE_TESTS_OK")


if __name__ == "__main__":
    main()
