from ...database.db_connector import db

class User:
    def __init__(self, name, email, phone, password):
        self.name = name
        self.email = email
        self.phone = phone
        self.password = password
    
    def save(self):
        return db.users.insert_one({
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'password': self.password
        })
    
    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone
        }
    
    @staticmethod
    def find_by_email(email):
        user_data = db.users.find_one({'email': email})
        if user_data:
            return User(**user_data)
        return None
    
    @staticmethod
    def find_by_phone(phone):
        user_data = db.users.find_one({'phone': phone})
        if user_data:
            return User(**user_data)
        return None