import argparse
import asyncio
from nats.aio.client import Client as NATS
import os
import random
from scapy.all import Ether


async def run(mean_value):
    print(f"Mean value for random delay: {mean_value}")
    nc = NATS()

    nats_url = os.getenv("NATS_SURVEYOR_SERVERS", "nats://nats:4222")
    await nc.connect(nats_url)

    async def message_handler(msg):
        subject = msg.subject
        data = msg.data  # .decode()
        # print(f"Received a message on '{subject}': {data}")
        packet = Ether(data)
        print(packet.show())
        # Publish the received message to outpktsec and outpktinsec
        delay = random.expovariate(1 / mean_value)
        await asyncio.sleep(delay)
        if subject == "inpktsec":
            await nc.publish("outpktinsec", msg.data)
        else:
            await nc.publish("outpktsec", msg.data)

    # Subscribe to inpktsec and inpktinsec topics
    await nc.subscribe("inpktsec", cb=message_handler)
    await nc.subscribe("inpktinsec", cb=message_handler)

    print("Subscribed to inpktsec and inpktinsec topics")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Disconnecting...")
        await nc.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Python Processor")
    parser.add_argument("--mean_value", type=float, default=5e-6, help="Mean value for random delay")
    args = parser.parse_args()
    asyncio.run(run(args.mean_value))
