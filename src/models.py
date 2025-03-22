class User:
    def __init__(self, id, telegram_id, full_name, company_id, balance):
        self.id = id
        self.telegram_id = telegram_id
        self.full_name = full_name
        self.company_id = company_id
        self.balance = balance

class Company:
    def __init__(self, id, name, api_key):
        self.id = id
        self.name = name
        self.api_key = api_key