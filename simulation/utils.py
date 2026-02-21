
import random

class Distribution:
    """Helper to generate values based on a discrete probability distribution (PMF)."""
    def __init__(self, pmf_dict):
        """
        pmf_dict: Dict {Value: Probability}
        e.g., {0: 0.5, 1: 0.3, 2: 0.2}
        """
        self.values = list(pmf_dict.keys())
        self.probabilities = list(pmf_dict.values())
        
        # Normalize if needed (floating point issues)
        total = sum(self.probabilities)
        if abs(total - 1.0) > 0.01:
            print(f"Warning: PMF sums to {total}, normalizing...")
            self.probabilities = [p/total for p in self.probabilities]

    def sample(self):
        """Return a value sampled from the distribution."""
        return random.choices(self.values, weights=self.probabilities, k=1)[0]
