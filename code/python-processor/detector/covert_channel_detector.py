import numpy as np
from collections import deque
import logging
from typing import Tuple, Dict
import time


class CovertChannelDetector:
    def __init__(self,
                 window_size: int = 50,
                 threshold: float = 0.7,
                 history_length: int = 3):
        """
        Initialize the simple covert channel detector.
        """
        self.window_size = window_size
        self.threshold = threshold
        self.history_length = history_length
        self.packet_times = deque(maxlen=window_size * 2)
        self.ipd_history = deque(maxlen=history_length * window_size)

        self.logger = logging.getLogger(__name__)
        self.last_detection_time = time.time()
        self.detection_count = 0
        self.total_packets = 0

        # Add baseline tracking for better false positive reduction
        self.baseline_delays = deque(maxlen=100)
        self.baseline_established = False

    def add_packet(self, timestamp: float) -> None:
        """Add a new packet timestamp for analysis."""
        self.total_packets += 1
        self.packet_times.append(timestamp)

        if len(self.packet_times) >= 2:
            ipd = self.packet_times[-1] - self.packet_times[-2]
            self.ipd_history.append(ipd)

            # Build baseline of normal delays
            if not self.baseline_established and len(self.baseline_delays) < 100 and ipd < 0.2:
                self.baseline_delays.append(ipd)
                if len(self.baseline_delays) == 100:
                    self.baseline_established = True

    def detect(self) -> Tuple[bool, float, Dict]:
        """Detect covert channel by looking for artificial timing patterns in general."""
        if len(self.packet_times) < self.window_size:
            return False, 0.0, {"total_score": 0.0}

        # Get delays(ipds) only for the recent window
        delays = list(self.ipd_history)[-self.window_size:]
        # If ipd count is less than window size return not detected
        if len(delays) < self.window_size - 1:
            return False, 0.0, {"total_score": 0.0}

        delays = np.array(delays)

        # Confidence score
        score = 0.0
        detailed_scores = {}

        # 1. Check for bimodal distribution (characteristic of binary encoding)
        unique_delays, counts = np.unique(np.round(delays, 3), return_counts=True)
        bimodal_score = 0.0
        if len(unique_delays) >= 2:
            sorted_counts = np.sort(counts)[::-1]
            if len(sorted_counts) >= 2:
                count_ratio = sorted_counts[1] / sorted_counts[0]
            else:
                count_ratio = 0  # Not enough unique values to compare
            count_ratio = min(counts) / max(counts)
            if count_ratio > 0.5:
                sorted_indices = np.argsort(counts)[::-1]
                if len(sorted_indices) >= 2:
                    top_2_delays = unique_delays[sorted_indices[:2]]
                else:
                    top_2_delays = unique_delays
                value_ratio = max(top_2_delays) / max(min(top_2_delays), 0.001)
                if value_ratio > 2.0 and max(unique_delays) - min(unique_delays) > 0.2:  # One value is at least 2x the other
                    bimodal_score = 0.5

        detailed_scores['bimodal'] = bimodal_score
        score += bimodal_score

        # 2. Check for artificial regularity (too consistent timing)
        cv = np.std(delays) / max(np.mean(delays), 0.001)  # Cooefficient of variation
        regularity_score = 0.0
        print(f"cv: {cv}")
        if cv < 0.7:  # Low variation suggests artificial timing
            regularity_score = 0.3
        detailed_scores['regularity'] = regularity_score
        score += regularity_score

        # 3. Check for baseline deviation (if baseline established)
        baseline_score = 0.0
        if self.baseline_established and len(self.baseline_delays) > 0:
            baseline_mean = np.mean(self.baseline_delays)
            baseline_std = np.std(self.baseline_delays)
            current_mean = np.mean(delays)
            # Check if current delays are significantly different from baseline
            if baseline_std > 0:
                z_score = abs(current_mean - baseline_mean) / baseline_std
                if z_score > 2.0:  # More than 2 standard deviations from baseline
                    baseline_score = 0.2

        detailed_scores['baseline_deviation'] = baseline_score
        score += baseline_score

        # 4. Check for specific covert channel patterns
        pattern_score = 0.0
        if len(unique_delays) >= 2:
            # Get the two most common delay values
            sorted_indices = np.argsort(counts)[::-1]
            # Get min and max of the top 2 most frequent delays
            top_two_delays = unique_delays[sorted_indices[:2]]
            min_delay = min(top_two_delays)
            max_delay = max(top_two_delays)
            print(f"min_delay: {min_delay}, max_delay: {max_delay}")
            # Count delays that fall within ±0.1 of these two values
            if max_delay > 0.5 and min_delay > 0.1:
                if max_delay - min_delay > 0.2:
                    short_delays = np.sum((delays >= min_delay - 0.2) & (delays <= min_delay + 0.2))
                    long_delays = np.sum((delays >= max_delay - 0.2) & (delays <= max_delay + 0.2))
                    pattern_ratio = (short_delays + long_delays) / len(delays)

                    if pattern_ratio > 0.6:  # More than 60% of delays match the two main patterns
                        pattern_score = 0.4
                if max_delay - min_delay > 0.1:
                    short_delays = np.sum((delays >= min_delay - 0.1) & (delays <= min_delay + 0.1))
                    long_delays = np.sum((delays >= max_delay - 0.1) & (delays <= max_delay + 0.1))
                    pattern_ratio = (short_delays + long_delays) / len(delays)

                    if pattern_ratio > 0.6:  # More than 60% of delays match the two main patterns
                        pattern_score = 0.4

        detailed_scores['pattern_match'] = pattern_score
        score += pattern_score

        # Normalize score to 0-1 range
        score = min(1.0, score)
        detailed_scores['total_score'] = score

        is_covert = score > self.threshold

        # Debug output
        if score > 0.3:
            print(f"Detection Analysis - Bimodal: {bimodal_score:.3f}, BaselineScore: {baseline_score:.3f}, "
                  f"Regularity: {regularity_score:.3f}, Pattern: {pattern_score:.3f}, "
                  f"Total: {score:.3f}, Detected: {is_covert}")

        if is_covert:
            self.detection_count += 1
            self.last_detection_time = time.time()

        return is_covert, score, detailed_scores

    def get_detection_stats(self) -> Dict:
        """Get detection statistics."""
        detection_rate = self.detection_count / max(1, self.total_packets)
        return {
            'detection_rate': detection_rate,
            'total_packets': self.total_packets,
            'detections': self.detection_count,
            'last_detection_time': self.last_detection_time
        }
