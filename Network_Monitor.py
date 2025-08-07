class NetworkMonitor:
    """Monitor network statistics and latency."""
    
    def __init__(self):
        self.sent_count = 0
        self.ack_count = 0
        self.last_sent_time = {}
        self.latencies = []
        self.max_latency_samples = 100
        
    def message_sent(self, sequence: int):
        """Record when a message was sent."""
        self.sent_count += 1
        self.last_sent_time[sequence] = time.time()
        
    def message_acknowledged(self, sequence: int, timestamp: float):
        """Calculate latency when acknowledgment received."""
        if sequence in self.last_sent_time:
            latency = (time.time() - self.last_sent_time[sequence]) * 1000  # ms
            self.latencies.append(latency)
            if len(self.latencies) > self.max_latency_samples:
                self.latencies.pop(0)
            self.ack_count += 1
            del self.last_sent_time[sequence]
            return latency
        return None
        
    def get_stats(self) -> Dict:
        """Get current network statistics."""
        if not self.latencies:
            return {
                "avg_latency": 0, 
                "max_latency": 0, 
                "packet_loss": 0,
                "sent": self.sent_count,
                "acked": self.ack_count
            }
            
        avg_latency = sum(self.latencies) / len(self.latencies)
        max_latency = max(self.latencies)
        expected_acks = self.sent_count // 5  # Only every 5th packet expects ack
        packet_loss = 1 - (self.ack_count / expected_acks) if expected_acks > 0 else 0
        
        return {
            "avg_latency": avg_latency,
            "max_latency": max_latency,
            "packet_loss": packet_loss,
            "sent": self.sent_count,
            "acked": self.ack_count
        }