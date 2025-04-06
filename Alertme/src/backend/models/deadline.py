from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import re

class DeadlineModel:
    def __init__(self):
        try:
            self.client = MongoClient('mongodb://your_mongodb_uri')
            self.db = self.client['your_database_name']
            self.personal_db = self.client['your_personal_db']
            self.collection = self.personal_db['deadlines']
            
            # Create indexes
            self.collection.create_index([('user_id', 1)])
            self.collection.create_index([('due_date', 1)])
        except Exception as e:
            raise Exception(f"Failed to connect to MongoDB: {str(e)}")

    def validate_deadline_data(self, deadline_data):
        try:
            required_fields = ['user_id', 'title', 'due_date']
            for field in required_fields:
                if not deadline_data.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate date format (YYYY-MM-DD)
            date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
            if not date_pattern.match(deadline_data['due_date']):
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
            
            # Set default values
            deadline_data.setdefault('priority', 'medium')
            deadline_data.setdefault('status', 'pending')
            deadline_data.setdefault('description', '')
            
            return deadline_data
            
        except Exception as e:
            raise ValueError(f"Validation error: {str(e)}")

    def create_deadline(self, deadline_data):
        try:
            self.validate_deadline_data(deadline_data)
            deadline_data['created_at'] = datetime.utcnow()
            deadline_data['updated_at'] = datetime.utcnow()
            result = self.collection.insert_one(deadline_data)
            return str(result.inserted_id)
        except Exception as e:
            raise Exception(f"Failed to create deadline: {str(e)}")

    def get_all_deadlines(self, user_id):
        try:
            deadlines = self.collection.find({'user_id': user_id})
            return [{**deadline, '_id': str(deadline['_id'])} for deadline in deadlines]
        except Exception as e:
            raise Exception(f"Failed to fetch deadlines: {str(e)}")

    def get_deadline_by_id(self, deadline_id):
        deadline = self.collection.find_one({'_id': ObjectId(deadline_id)})
        if deadline:
            deadline['_id'] = str(deadline['_id'])
        return deadline

    def update_deadline(self, deadline_id, update_data):
        update_data['updated_at'] = datetime.utcnow()
        self.collection.update_one(
            {'_id': ObjectId(deadline_id)},
            {'$set': update_data}
        )

    def delete_deadline(self, deadline_id):
        self.collection.delete_one({'_id': ObjectId(deadline_id)})

    def get_deadlines_by_date(self, date, user_id):
        deadlines = self.collection.find({
            'user_id': user_id,
            'due_date': {'$regex': f'^{date}'}
        })
        return [{**deadline, '_id': str(deadline['_id'])} for deadline in deadlines]

class Deadline:
    def __init__(self, user_id, title, due_date, priority='medium', 
                 description='', status='pending', _id=None, created_at=None):
        self._id = _id
        self.user_id = user_id
        self.title = title
        self.description = description
        self.due_date = due_date
        self.priority = priority
        self.status = status
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self):
        return {
            'id': str(self._id) if self._id else None,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

    @staticmethod
    def from_dict(data):
        return Deadline(
            _id=ObjectId(data['_id']) if '_id' in data else None,
            user_id=data['user_id'],
            title=data['title'],
            description=data.get('description', ''),
            due_date=data['due_date'],
            priority=data.get('priority', 'medium'),
            status=data.get('status', 'pending'),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None
        )  # Added missing closing parenthesis