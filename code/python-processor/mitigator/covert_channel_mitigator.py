import random


class CovertChannelMitigator:
    def __init__(self, min_delay: float = 0.9, max_delay: float = 1.2):
        """
        Initialize the covert channel mitigator.
        Args:
            min_delay: Minimum delay to add (seconds)
            max_delay: Maximum delay to add (seconds)
        """
        self.min_delay = min_delay
        self.max_delay = max_delay

    def mitigate(self) -> float:
        """
        Apply mitigation by generating a random delay.
        Since Covert Channel is IPD based adding random delays blocks correct message recieve.
        Returns:
            The delay to apply in seconds
        """
        return random.uniform(self.min_delay, self.max_delay)
