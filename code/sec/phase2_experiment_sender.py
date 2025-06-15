""" SEND SAME MESSAGE REPETEADLY FOR EXPERIMENTS"""
import argparse
import os
import socket
import time


def create_bitstream_from_message(message):
    bitstream = message
    if not all(c in '01' for c in message):
        bitstream = ''.join(format(ord(char), '08b') for char in message)
    return bitstream


def start_covert_channel_sender(args):
    host = os.getenv('INSECURENET_HOST_IP')

    # Get variables from args
    port = args.port  # Port number for sending
    message = args.message  # Message bit stream
    zero_bit_delay = args.zero_bit_delay  # Port number for sending
    one_bit_delay = args.one_bit_delay  # Port number for sending
    bit_repeat_len = args.bit_repeat_len  # How many packages sends for 1 bit

    print(f"Port: {port}, Message: {message}, Zero Bit Delay: {zero_bit_delay}, One Bit Delay: {one_bit_delay}, Bit Repeat Length: {bit_repeat_len}")

    # Define delay encoding (gap between packets sent)
    BIT_DELAY = {
        "0": zero_bit_delay,  # Short gap
        "1": one_bit_delay,  # Long gap
    }

    if not host:
        print("SECURENET_HOST_IP environment variable is not set.")
        return

    ber_list = []
    capacity_list = []
    transmission_times = []
    try:
        for i in range(100):
            # Create a UDP socket
            start = time.time()
            print(f"sending started at:{start}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            bitstream = create_bitstream_from_message(message)
            print(f"Bitstream: {bitstream}")
            # Send every bit in bit stream
            for bit in bitstream:
                # Send multiple packets for each bit (for takea an average in receiver to tolarete other random delays added(like processer))
                for _ in range(bit_repeat_len):
                    sock.sendto(f"bit:{bit}".encode(), (host, port))
                    time.sleep(BIT_DELAY[bit])
            response, server = sock.recvfrom(4096)
            end = time.time()
            total_time = end - start

            # Step 2: Calculate metrics
            sent_bits = bitstream
            received_bits = response.decode()
            errors = sum(a != b for a, b in zip(sent_bits, received_bits))
            ber = errors / len(sent_bits)
            capacity = (len(received_bits) - errors) / total_time  # bits/sec

            ber_list.append(ber)
            capacity_list.append(capacity)
            transmission_times.append(total_time)

            print(f"sending end at:{end}")
            print("----------------------")
            print(f"Response from server: {response.decode()}")
            print(f"Bitstream sent: {bitstream}")
            print(f"time: {end - start}")
            print(f"bit sent: {len(bitstream) * bit_repeat_len}")
            print("----------------------")
        print(f"BERs: {ber_list}")
        print(f"Capacities: {capacity_list}")
        print(f"Transmission Times: {transmission_times}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        sock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Covert Channel Sender")
    parser.add_argument("--port", type=int, default=8002, help="Listening port")
    parser.add_argument("--message", type=str, default="", help="Message bitstream")
    parser.add_argument("--zero_bit_delay", type=float, default=0.3, help="Zero's bit delay time")
    parser.add_argument("--one_bit_delay", type=float, default=0.9, help="One's bit delay time")
    parser.add_argument("--bit_repeat_len", type=int, default=5, help="How many packets sends the same bit")

    args = parser.parse_args()
    start_covert_channel_sender(args)
