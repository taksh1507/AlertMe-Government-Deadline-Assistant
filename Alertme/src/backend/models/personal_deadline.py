from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import re

class PersonalDeadlineModel:
    def __init__(self):
        try:
            self.client = MongoClient('mongodb://your_mongodb_uri')
            self.db = self.client['your_database_name']
            self.collection = self.db['deadlines']
            self.users = self.db['users']
            
            # Create indexes
            self.collection.create_index([('user_id', 1)])
            self.collection.create_index([('due_date', 1)])
            self.users.create_index([('original_id', 1)], unique=True)
        except Exception as e:
            raise Exception(f"Failed to connect to MongoDB: {str(e)}")

    def create_deadline(self, deadline_data):
        try:
            # Ensure user exists in personal_deadlines_db
            self.users.update_one(
                {'original_id': deadline_data['user_id']},
                {'$set': {'original_id': deadline_data['user_id']}},
                upsert=True
            )
            # Data validation and cleaning
            cleaned_data = {
                'title': str(deadline_data.get('title', '')).strip(),
                'description': str(deadline_data.get('description', '')).strip(),
                'due_date': str(deadline_data.get('due_date', '')),
                'priority': str(deadline_data.get('priority', 'low')).lower(),
                'status': str(deadline_data.get('status', 'pending')).lower(),
                'type': 'personal',
                'user_id': deadline_data.get('user_id'),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }

            # Validate required fields
            if not cleaned_data['title']:
                raise ValueError("Title is required")
            if not cleaned_data['due_date']:
                raise ValueError("Due date is required")
            if not cleaned_data['user_id']:
                raise ValueError("User ID is required")
            if cleaned_data['priority'] not in ['low', 'medium', 'high']:
                raise ValueError("Invalid priority level")

            # Validate date format
            try:
                datetime.strptime(cleaned_data['due_date'], '%Y-%m-%d')
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")

            # Insert the document with cleaned data
            result = self.collection.insert_one(cleaned_data)
            return str(result.inserted_id)

        except ValueError as ve:
            raise ValueError(str(ve))
        except Exception as e:
            raise Exception(f"Failed to create deadline: {str(e)}")

    def get_user_deadlines(self, user_id):
        try:
            deadlines = list(self.collection.find({'user_id': user_id}))
            for deadline in deadlines:
                deadline['id'] = str(deadline['_id'])
                del deadline['_id']
            return deadlines
        except Exception as e:
            raise Exception(f"Failed to get deadlines: {str(e)}")

    def update_deadline(self, deadline_id, deadline_data):
        try:
            deadline_data['updated_at'] = datetime.utcnow()
            result = self.collection.update_one(
                {'_id': ObjectId(deadline_id)},
                {'$set': deadline_data}
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Failed to update deadline: {str(e)}")

    def delete_deadline(self, deadline_id):
        try:
            result = self.collection.delete_one({'_id': ObjectId(deadline_id)})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Failed to delete deadline: {str(e)}")