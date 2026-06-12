class TrafficCounter:
    def __init__(self):
        self.total = 0

    def hit(self) -> int:
        self.total += 1
        return self.total
