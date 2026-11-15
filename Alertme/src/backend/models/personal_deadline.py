from .deadline import DeadlineModel


class PersonalDeadlineModel(DeadlineModel):
    def __init__(self, client, db_name=None, personal_db_name=None):
        super().__init__(client, db_name, personal_db_name)
        self.collection = self.db["deadlines"]
        self.storage = "main"
