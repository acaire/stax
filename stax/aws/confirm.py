class Confirm:
    def __init__(self, question, method):
        self.question = question
        self.method = method


class ClickConfirm(Confirm):
    pass


class BuildkiteConfirm(Confirm):
    pass
