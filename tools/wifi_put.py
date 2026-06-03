import argparse
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AP_URL = "http://192.168.4.1:8080"


def upload(args):
    local = Path(args.local).resolve()
    data = local.read_bytes()

    base = args.url.rstrip("/")
    query = {"path": args.remote}
    if args.reset:
        query["reset"] = "1"
    if args.token:
        query["token"] = args.token

    url = base + "/upload?" + urlencode(query)
    headers = {"Content-Type": "application/octet-stream"}
    if args.token:
        headers["X-Zbot-Token"] = args.token

    request = Request(url, data=data, headers=headers, method="POST")
    with urlopen(request, timeout=args.timeout) as response:
        body = response.read().decode(errors="replace")
        print(body.strip())

    print("Uploaded {} bytes from {} to {}".format(len(data), local, args.remote))


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Upload a file to ZebraBot over Wi-Fi HTTP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "If --url is omitted, AP mode is used by default.\n\n"
            "AP mode example: python tools\\wifi_put.py user_main.py --ap --reset\n"
            "Router example:  python tools\\wifi_put.py user_main.py --url http://ROBOT_IP:8080"
        ),
    )
    parser.add_argument("items", nargs="+", help="Local file, or legacy: URL local [remote]")
    parser.add_argument(
        "--url",
        default="",
        help="Robot URL on a router/common network, for example http://192.168.1.44:8080",
    )
    parser.add_argument(
        "--ap",
        action="store_true",
        help="Use the default ZebraBot AP URL, http://192.168.4.1:8080",
    )
    parser.add_argument(
        "--remote",
        default="/user_main.py",
        help="Remote MicroPython path. Defaults to /user_main.py",
    )
    parser.add_argument("--token", default="", help="Optional Wi-Fi code token")
    parser.add_argument("--reset", action="store_true", help="Reset the board after upload")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds")
    args = parser.parse_args(argv)

    # Backward compatibility for the original positional form:
    #   wifi_put.py http://ROBOT:8080 user_main.py [/remote.py]
    if args.items[0].startswith(("http://", "https://")):
        if len(args.items) < 2:
            parser.error("legacy URL form requires a local file")
        args.url = args.items[0]
        args.local = args.items[1]
        if len(args.items) > 2:
            args.remote = args.items[2]
        if len(args.items) > 3:
            parser.error("too many positional arguments")
    else:
        if len(args.items) > 1:
            args.remote = args.items[1]
        if len(args.items) > 2:
            parser.error("too many positional arguments")
        args.local = args.items[0]
        if args.ap or not args.url:
            args.url = AP_URL

    if args.ap:
        args.url = AP_URL
    return args


def main(argv=None):
    upload(parse_args(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    main()
