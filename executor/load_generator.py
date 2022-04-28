class LoadGenerator:
    """
    Base class for generating load
    """
    def stop(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
