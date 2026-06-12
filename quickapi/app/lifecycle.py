class Lifecycle:
    def __init__(self):
        self.startup_handlers = []
        self.shutdown_handlers = []

    def on_startup(self, handler):
        self.startup_handlers.append(handler)
        return handler

    def on_shutdown(self, handler):
        self.shutdown_handlers.append(handler)
        return handler

    def startup(self):
        for handler in self.startup_handlers:
            handler()

    def shutdown(self):
        for handler in self.shutdown_handlers:
            handler()
