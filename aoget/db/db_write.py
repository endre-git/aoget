class DbWrite:
    """Function wrapper to write to the database."""

    def __init__(self, function_to_wrap, *args, **kwargs):
        self.function = function_to_wrap
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        result = self.function(self.args, self.kwargs)
        return result
