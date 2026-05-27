import argparse
import asyncio
import base64
import sys
from pathlib import Path

UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"


class AckWaiter:
    def __init__(self, verbose=False):
        self.lines = []
        self._waiters = []
        self.verbose = verbose

    def feed(self, _sender, data):
        for raw in data.decode(errors="replace").splitlines():
            line = raw.strip()
            if not line:
                continue
            if self.verbose or line.startswith(("PUT_", "PONG", "ERR")):
                print("<", line)
            self.lines.append(line)
            for waiter in list(self._waiters):
                waiter(line)

    async def wait_for(self, predicate, timeout=8):
        for line in self.lines:
            if predicate(line):
                return line

        loop = asyncio.get_running_loop()
        fut = loop.create_future()

        def check(line):
            if not fut.done() and predicate(line):
                fut.set_result(line)

        self._waiters.append(check)
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            try:
                self._waiters.remove(check)
            except ValueError:
                pass


def b64(data):
    return base64.b64encode(data).decode("ascii")


async def send_line(client, line, delay_s):
    data = (line + "\n").encode("ascii")
    await client.write_gatt_char(UART_RX_UUID, data, response=True)
    if delay_s:
        await asyncio.sleep(delay_s)


async def find_device(name, timeout):
    from bleak import BleakScanner

    print("Scanning for {}...".format(name))
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name == name or name in (ad.local_name or ""),
        timeout=timeout,
    )
    if device is None:
        raise RuntimeError("BLE device {!r} not found".format(name))
    return device


async def upload(args):
    from bleak import BleakClient

    local_path = Path(args.local).resolve()
    data = local_path.read_bytes()
    remote_path = args.remote

    device = await find_device(args.name, args.scan_timeout)
    print("Connecting to {} ({})...".format(device.name or args.name, device.address))

    ack = AckWaiter(verbose=args.verbose)
    async with BleakClient(device) as client:
        if not client.is_connected:
            raise RuntimeError("BLE connect failed")

        await client.start_notify(UART_TX_UUID, ack.feed)

        await send_line(client, "QUIET", args.delay)
        await ack.wait_for(lambda line: line == "OK QUIET", timeout=args.timeout)

        await send_line(client, "PING", args.delay)
        await ack.wait_for(lambda line: line == "PONG", timeout=args.timeout)

        if remote_path == "/user_main.py":
            await send_line(client, "PU", args.delay)
        else:
            begin_line = "PB " + b64(remote_path.encode())
            if len(begin_line) + 1 > 20:
                raise RuntimeError(
                    "Remote path command is too long for conservative BLE writes. "
                    "Use /user_main.py or increase the BLE MTU/chunk path support."
                )
            await send_line(client, begin_line, args.delay)
        await ack.wait_for(lambda line: line == "PUT_OK BEGIN", timeout=args.timeout)

        total = len(data)
        sent = 0
        for offset in range(0, total, args.chunk_size):
            chunk = data[offset:offset + args.chunk_size]
            await send_line(client, "PC " + b64(chunk), args.delay)
            sent += len(chunk)
            await ack.wait_for(
                lambda line, size=len(chunk): line == "PUT_OK CHUNK {}".format(size),
                timeout=args.timeout,
            )
            print("> uploaded {}/{} bytes".format(sent, total))

        await send_line(client, "PE", args.delay)
        await ack.wait_for(lambda line: line == "PUT_OK END", timeout=args.timeout)
        print("Uploaded {} to {}".format(local_path, remote_path))

        if args.reset:
            try:
                await send_line(client, "RESET", args.delay)
                print("Reset requested")
            except Exception as exc:
                print("Upload succeeded, but reset request was not confirmed: {}".format(exc))


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Upload a file to ZebraBot over BLE UART.")
    parser.add_argument("local", help="Local file to upload, for example user_main.py")
    parser.add_argument(
        "remote",
        nargs="?",
        default="/user_main.py",
        help="Remote MicroPython path. Defaults to /user_main.py",
    )
    parser.add_argument("--name", default="ZebraBot", help="BLE advertised name")
    parser.add_argument("--chunk-size", type=int, default=12, help="Raw bytes per BLE chunk")
    parser.add_argument("--delay", type=float, default=0.02, help="Delay after each write")
    parser.add_argument("--timeout", type=float, default=8.0, help="Ack timeout in seconds")
    parser.add_argument("--scan-timeout", type=float, default=12.0, help="Scan timeout in seconds")
    parser.add_argument("--reset", action="store_true", help="Reset the board after upload")
    parser.add_argument("--verbose", action="store_true", help="Print all BLE notifications")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be positive")
    asyncio.run(upload(args))


if __name__ == "__main__":
    main()
