import argparse
import asyncio
from nats.aio.client import Client as NATS
import os
import random
import time
import logging

from detector.covert_channel_detector import CovertChannelDetector
from mitigator.covert_channel_mitigator import CovertChannelMitigator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run(mean_value, min_delay, max_delay, window_size: int = 50, detection_threshold: float = 0.6, history_length: int = 5):
    """
    Run the processor with covert channel detection and mitigation.

    Args:
        mean_value: Mean value for adding random delay to packages
        window_size: Number of packets to analyze in detection window
        detection_threshold: Threshold for detection confidence (0-1)
        history_length: Number of windows to keep for baseline comparison
    """
    nc = NATS()

    # Initialize detector and mitigator
    detector = CovertChannelDetector(
        window_size=window_size,
        threshold=detection_threshold,
        history_length=history_length
    )
    mitigator = CovertChannelMitigator(min_delay=min_delay, max_delay=max_delay)

    nats_url = os.getenv("NATS_SURVEYOR_SERVERS", "nats://nats:4222")
    await nc.connect(nats_url)

    processed_packets_count = 0
    detected_covert_channel_count = 0
    continue_to_mitigate = False
    current_mitigation_count = 0

    async def message_handler(msg):
        nonlocal continue_to_mitigate, current_mitigation_count, detected_covert_channel_count, processed_packets_count
        now = time.time()
        # Add packet to detector
        detector.add_packet(now)
        # Check for covert channel
        is_covert, confidence, detailed_scores = detector.detect()

        if is_covert:
            print(f"Covert channel detected! Confidence: {confidence:.2f}")
            detected_covert_channel_count += 1

            # Log detailed scores for analysis
            if logger.isEnabledFor(logging.DEBUG):
                score_str = ", ".join([f"{k}: {v:.3f}" for k, v in detailed_scores.items()
                                       if k != 'total_score'])
                logger.debug(f"Detection scores: {score_str}")
            # Apply mitigation
            continue_to_mitigate = True
            current_mitigation_count = 0

        else:
            # Process packet normally with random delay
            delay = random.expovariate(1 / mean_value)
            await asyncio.sleep(delay)
        if continue_to_mitigate:
            current_mitigation_count += 1
            if current_mitigation_count >= 10:
                continue_to_mitigate = False
                current_mitigation_count = 0
            else:
                delay = mitigator.mitigate()
                logger.debug(f"Mitigator applied random delay: {delay}")
                await asyncio.sleep(delay)
        processed_packets_count += 1
        print(f"Processed packets count: {processed_packets_count}")
        print(f"Detected covert channel count: {detected_covert_channel_count}")
        subject = msg.subject
        if subject == "inpktsec":
            await nc.publish("outpktinsec", msg.data)
        else:
            await nc.publish("outpktsec", msg.data)

    # Subscribe to inpktsec and inpktinsec topics
    await nc.subscribe("inpktsec", cb=message_handler)
    await nc.subscribe("inpktinsec", cb=message_handler)

    print("Subscribed to inpktsec and inpktinsec topics")
    print(f"IPD Covert Channel Detector active with window_size={window_size}, threshold={detection_threshold}")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Disconnecting...")
        await nc.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Python Processor")
    parser.add_argument("--mean_value", type=float, default=5e-6, help="Mean value for random delay")
    parser.add_argument("--min_delay", type=float, default=0.6, help="Mean value for random delay")
    parser.add_argument("--max_delay", type=float, default=1.6, help="Mean value for random delay")
    parser.add_argument("--window_size", type=int, default=30,
                        help="Window size for detector (number of packets to analyze)")
    parser.add_argument("--detection_threshold", type=float, default=0.65,
                        help="Detection threshold (0-1)")
    parser.add_argument("--history_length", type=int, default=5,
                        help="Number of windows to keep for baseline comparison")
    args = parser.parse_args()
    asyncio.run(run(args.mean_value, args.min_delay, args.max_delay, args.window_size, args.detection_threshold, args.history_length))
