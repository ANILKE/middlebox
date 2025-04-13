import argparse
import socket
import time

from statistics import mean


def start_covert_channel_listener(args):
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Get variables from args
    print(args.port)
    port = args.port  # Port number for listening
    sender_bit_delay = args.sender_bit_delay  # Assigned bit delay on sender for 0 value
    given_delay_threshold = args.given_delay_threshold  # Add this to sender_bit_delay to tolarete other networking delyas
    bit_repeat_len = args.bit_repeat_len  # How many packets are repeated in sender to sen 1 bit
    bitstream_len = args.bitstream_len
    ipd_threshold = sender_bit_delay + given_delay_threshold
    print(f"Port: {port}, Sender Bit Delay: {sender_bit_delay}, Given Delay Threshold: {given_delay_threshold}, Bit Repeat Len: {bit_repeat_len}, Bitstream len: {bitstream_len}")

    # Bind the socket to the port
    server_address = ('', port)
    sock.bind(server_address)

    # Create needed variables
    recv_times = []  # Keeps ipds
    timestamps = []  # Keeps timestamps when a data is received

    print(f"Covert channel listener started on port {port}")
    is_first_data_received = False
    resulting_stream = ""
    while True:
        data, address = sock.recvfrom(4096)
        now = time.time()
        timestamps.append(now)
        print(f"{bitstream_len} bit stream is started at: {now}")
        print(f"Received {len(data)} bytes from {address}")
        print(data.decode())
        if len(timestamps) >= 2:
            ipd = timestamps[-1] - timestamps[-2]
            recv_times.append(ipd)
            print(f"Received packet, IPD: {ipd:.4f}s")
        if len(recv_times) >= bit_repeat_len or (len(recv_times) >= bit_repeat_len - 1 and not is_first_data_received):  # since recv_times added after second receive in first run first time add if bigger than minus 1
            is_first_data_received = True
            avg_ipd = mean(recv_times)
            bit = "0" if avg_ipd < ipd_threshold else "1"
            print(f"Decoded bit: {bit} (avg IPD: {avg_ipd:.4f}s)")
            recv_times.clear()
            resulting_stream += bit
            if len(resulting_stream) >= bitstream_len:
                now = time.time()
                print(f"{bitstream_len} bit stream is completed at: {now}. Decoded bitstream: {resulting_stream}")
                data = resulting_stream.encode()
                if data:
                    sock.sendto(data, address)
                resulting_stream = ""


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Covert Channel Sender")
    parser.add_argument("--port", type=int, default=8002, help="Listening Port")
    parser.add_argument("--sender_bit_delay", type=float, default=0.3, help="Senders bit delay for 0")
    parser.add_argument("--given_delay_threshold", type=float, default=0.3, help="Delay Threshold")
    parser.add_argument("--bit_repeat_len", type=int, default=5, help="How many packets sends the same bit")
    parser.add_argument("--bitstream_len", type=int, default=10, help="How many packets sends the same bit")

    args = parser.parse_args()
    start_covert_channel_listener(args)
