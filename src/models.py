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


class Truck:
    def __init__(self, id, name, truck_id, company_id):
        self.id = id
        self.name = name
        self.truck_id = truck_id
        self.company_id = company_id

class Notification:
    def __init__(self, id, telegram_id, truck_id, notification_type_id, every_minutes, last_send_time, warning_type, engine_status):
        self.id = id
        self.telegram_id = telegram_id
        self.truck_id = truck_id
        self.notification_type_id = notification_type_id
        self.every_minutes = every_minutes
        self.last_send_time = last_send_time
        self.warning_type = warning_type
        self.engine_status = engine_status