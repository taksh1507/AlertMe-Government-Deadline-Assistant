from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from .models.deadline import DeadlineModel
from datetime import datetime, timedelta
from functools import wraps
from bson.objectid import ObjectId
from .models.personal_deadline import PersonalDeadlineModel

load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False
jwt = JWTManager(app)

# MongoDB connection with environment variables
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://your_mongodb_uri'),
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    maxPoolSize=50,
                    socketTimeoutMS=5000)
db = client[os.getenv('DB_NAME', 'your_database_name')]
personal_db = client[os.getenv('PERSONAL_DB_NAME', 'your_personal_db')]

# Admin configuration using environment variables
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'your_admin_email')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'your_admin_password')
users = db['users']

# Create indexes
db.government_deadlines.create_index([('subscribers', 1)])
db.government_deadlines.create_index([('due_date', 1)])
users.create_index([('email', 1)])
db.admin_settings.create_index([('email', 1)], unique=True)

# Admin configuration
ADMIN_EMAIL = "admin@alertme.com"
ADMIN_PASSWORD = "admin123"

# Admin middleware
def admin_required(f):
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if not claims.get('is_admin'):
            return jsonify({'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return wrapper

# Initialize deadline model
deadline_model = DeadlineModel()

# Initialize models
personal_deadline_model = PersonalDeadlineModel()

# Personal deadlines routes
@app.route('/api/personal-deadlines', methods=['GET'])
@jwt_required()
def get_personal_deadlines():
    try:
        user_id = get_jwt_identity()
        deadlines = personal_deadline_model.get_user_deadlines(user_id)
        return jsonify(deadlines)
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/personal-deadlines', methods=['POST'])
@jwt_required()
def create_personal_deadline():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Debug print
        print("Received data:", data)
        print("Current user ID:", current_user_id)
        
        # Validate required fields
        required_fields = ['title', 'due_date', 'priority']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 422
        
        # Format data before sending to model
        deadline_data = {
            'title': data.get('title').strip(),
            'description': data.get('description', ''),  # Make description optional
            'due_date': data.get('due_date'),
            'priority': data.get('priority').lower(),
            'status': data.get('status', 'pending'),
            'type': 'personal',
            'user_id': current_user_id
        }
        
        # Create deadline
        deadline_id = personal_deadline_model.create_deadline(deadline_data)
        
        return jsonify({
            'message': 'Personal deadline created successfully',
            'id': deadline_id
        }), 201
        
    except ValueError as ve:
        print("Validation error:", str(ve))
        return jsonify({'message': str(ve)}), 422
    except Exception as e:
        print("Server error:", str(e))
        return jsonify({'message': str(e)}), 500

@app.route('/api/personal-deadlines/<deadline_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def handle_personal_deadline(deadline_id):
    try:
        if request.method == 'PUT':
            data = request.get_json()
            success = personal_deadline_model.update_deadline(deadline_id, data)
            if success:
                return jsonify({'message': 'Deadline updated successfully'})
            return jsonify({'message': 'Deadline not found'}), 404
            
        elif request.method == 'DELETE':
            success = personal_deadline_model.delete_deadline(deadline_id)
            if success:
                return jsonify({'message': 'Deadline deleted successfully'})
            return jsonify({'message': 'Deadline not found'}), 404
            
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Authentication routes
@app.route('/auth/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    if data.get('email') == ADMIN_EMAIL and data.get('password') == ADMIN_PASSWORD:
        access_token = create_access_token(
            identity='admin',
            additional_claims={'is_admin': True}
        )
        return jsonify({
            'token': access_token,
            'message': 'Admin login successful'
        }), 200
    return jsonify({'message': 'Invalid admin credentials'}), 401

@app.route('/auth/api/admin/verify', methods=['GET'])
@admin_required
def verify_admin():
    return jsonify({'message': 'Valid admin token', 'is_admin': True}), 200

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    if users.find_one({'email': data['email']}):
        return jsonify({'message': 'Email already registered'}), 400
    if users.find_one({'phone': data['phone']}):
        return jsonify({'message': 'Phone number already registered'}), 400
    
    data['password'] = generate_password_hash(data['password'])
    
    # Insert into main database
    user_id = users.insert_one(data).inserted_id
    
    # Insert into personal deadlines database
    personal_db.users.insert_one({
        'original_id': str(user_id),
        'email': data['email'],
        'name': data['name']
    })
    
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = users.find_one({
        '$or': [
            {'email': data.get('identifier')},
            {'phone': data.get('identifier')}
        ]
    })
    
    if user and check_password_hash(user['password'], data['password']):
        access_token = create_access_token(identity=str(user['_id']))
        return jsonify({
            'message': 'Login successful',
            'token': access_token,
            'user': {
                'name': user['name'],
                'email': user['email'],
                'phone': user['phone']
            }
        }), 200
    return jsonify({'message': 'Invalid credentials'}), 401

# Personal deadline routes
@app.route('/api/deadlines', methods=['GET'])
@jwt_required()
def get_deadlines():
    user_id = get_jwt_identity()
    deadlines = deadline_model.get_all_deadlines(user_id)
    return jsonify(deadlines)

@app.route('/api/deadlines', methods=['POST'])
@jwt_required()
def create_deadline():
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        
        deadline_data = {
            'user_id': current_user,
            'title': data.get('title'),
            'description': data.get('description'),
            'due_date': data.get('due_date'),
            'priority': data.get('priority', 'medium'),
            'status': data.get('status', 'pending'),
            'type': 'personal'
        }
        
        deadline_id = deadline_model.create_deadline(deadline_data)
        return jsonify({
            'message': 'Deadline created successfully',
            'id': deadline_id
        }), 201
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 422
    except Exception as e:
        return jsonify({'message': f'Failed to create deadline: {str(e)}'}), 500

@app.route('/api/deadlines/<deadline_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def handle_deadline(deadline_id):
    if request.method == 'GET':
        deadline = deadline_model.get_deadline_by_id(deadline_id)
        return jsonify(deadline) if deadline else ('', 404)
    elif request.method == 'PUT':
        deadline_model.update_deadline(deadline_id, request.json)
        return '', 204
    elif request.method == 'DELETE':
        deadline_model.delete_deadline(deadline_id)
        return '', 204

@app.route('/api/deadlines/date/<date>', methods=['GET'])
@jwt_required()
def get_deadlines_by_date(date):
    user_id = get_jwt_identity()
    deadlines = deadline_model.get_deadlines_by_date(date, user_id)
    return jsonify(deadlines)

# Government deadline routes
@app.route('/admin/api/government-deadlines', methods=['GET', 'POST'])
@admin_required
def admin_government_deadlines():
    try:
        if request.method == 'GET':
            deadlines = list(db.government_deadlines.find())
            formatted_deadlines = [{
                'id': str(d['_id']),
                'title': d.get('title', ''),
                'department': d.get('department', ''),
                'due_date': d.get('due_date', ''),
                'priority': d.get('priority', ''),
                'description': d.get('description', ''),
                'subscribers': d.get('subscribers', [])
            } for d in deadlines]
            return jsonify({'deadlines': formatted_deadlines})
            
        elif request.method == 'POST':
            data = request.get_json()
            data['created_at'] = datetime.utcnow().isoformat()
            data['subscribers'] = []
            result = db.government_deadlines.insert_one(data)
            return jsonify({
                'id': str(result.inserted_id),
                'message': 'Government deadline created successfully'
            }), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/api/government-deadlines/<deadline_id>', methods=['PUT', 'DELETE'])
@admin_required
def admin_handle_govt_deadline(deadline_id):
    try:
        if request.method == 'DELETE':
            result = db.government_deadlines.delete_one({'_id': ObjectId(deadline_id)})
            if result.deleted_count:
                return jsonify({'message': 'Deadline deleted successfully'}), 200
            return jsonify({'message': 'Deadline not found'}), 404
            
        elif request.method == 'PUT':
            data = request.get_json()
            result = db.government_deadlines.update_one(
                {'_id': ObjectId(deadline_id)},
                {'$set': {
                    'title': data['title'],
                    'department': data['department'],
                    'due_date': data['due_date'],
                    'priority': data['priority'],
                    'description': data['description'],
                    'updated_at': datetime.utcnow().isoformat()
                }}
            )
            if result.modified_count:
                return jsonify({'message': 'Deadline updated successfully'}), 200
            return jsonify({'message': 'Deadline not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/government-deadlines/public', methods=['GET'])
def get_public_government_deadlines():
    try:
        deadlines = list(db.government_deadlines.find())
        formatted_deadlines = [{
            'id': str(d['_id']),
            'title': d.get('title', ''),
            'department': d.get('department', ''),
            'due_date': d.get('due_date', ''),
            'priority': d.get('priority', ''),
            'description': d.get('description', ''),
            'subscribers': d.get('subscribers', [])
        } for d in deadlines]
        return jsonify({'deadlines': formatted_deadlines})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/government-deadlines/<deadline_id>/subscribe', methods=['POST'])
@jwt_required()
def subscribe_to_govt_deadline(deadline_id):
    try:
        data = request.get_json()
        user_email = data.get('email')
        subscribed = data.get('subscribed', True)
        
        if not user_email:
            return jsonify({'message': 'Email is required'}), 400

        deadline = db.government_deadlines.find_one({'_id': ObjectId(deadline_id)})
        if not deadline:
            return jsonify({'message': 'Deadline not found'}), 404

        operation = {'$push': {'subscribers': user_email}} if subscribed else {'$pull': {'subscribers': user_email}}
        db.government_deadlines.update_one({'_id': ObjectId(deadline_id)}, operation)

        return jsonify({
            'message': 'Subscription updated successfully',
            'subscribed': subscribed
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to update subscription: {str(e)}'}), 400

@app.route('/api/user/subscribed-deadlines', methods=['GET'])
@jwt_required()
def get_subscribed_deadlines():
    try:
        user_email = get_jwt_identity()
        subscribed_deadlines = list(db.government_deadlines.find({'subscribers': user_email}))
        formatted_deadlines = [{
            'id': str(d['_id']),
            'title': d.get('title', ''),
            'department': d.get('department', ''),
            'due_date': d.get('due_date', ''),
            'priority': d.get('priority', ''),
            'description': d.get('description', ''),
            'type': 'government'
        } for d in subscribed_deadlines]
        return jsonify({'deadlines': formatted_deadlines})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin routes
@app.route('/admin/api/users', methods=['GET'])
@admin_required
def get_users():
    try:
        user_list = list(users.find({}, {'password': 0}))
        for user in user_list:
            user['_id'] = str(user['_id'])
        return jsonify({'users': user_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/api/profile', methods=['GET'])
@admin_required
def get_admin_profile():
    try:
        admin = users.find_one({'email': ADMIN_EMAIL}, {'password': 0})
        admin_data = {
            'name': admin.get('name', 'System Administrator') if admin else 'System Administrator',
            'email': ADMIN_EMAIL,
            'role': 'Administrator',
            'last_login': admin.get('last_login', datetime.utcnow().isoformat()) if admin else datetime.utcnow().isoformat()
        }
        return jsonify(admin_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/api/settings', methods=['GET', 'PUT'])
@admin_required
def handle_admin_settings():
    try:
        if request.method == 'GET':
            settings = db.admin_settings.find_one({'email': ADMIN_EMAIL}) or {
                'theme': 'light',
                'notifications_enabled': True,
                'email_notifications': True
            }
            return jsonify({
                'theme': settings.get('theme', 'light'),
                'notifications_enabled': settings.get('notifications_enabled', True),
                'email_notifications': settings.get('email_notifications', True)
            })
            
        elif request.method == 'PUT':
            data = request.get_json()
            db.admin_settings.update_one(
                {'email': ADMIN_EMAIL},
                {'$set': {
                    'theme': data.get('theme', 'light'),
                    'notifications_enabled': data.get('notifications_enabled', True),
                    'email_notifications': data.get('email_notifications', True),
                    'updated_at': datetime.utcnow().isoformat()
                }},
                upsert=True
            )
            return jsonify({'message': 'Settings updated successfully'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/api/analytics', methods=['GET'])
@admin_required
def get_admin_analytics():
    try:
        total_users = users.count_documents({})
        total_deadlines = db.government_deadlines.count_documents({})
        active_users = len(db.government_deadlines.distinct('subscribers'))
        
        deadline_stats = [{
            'title': d.get('title', ''),
            'total_subscribers': len(d.get('subscribers', [])),
            'active_users': len(d.get('subscribers', [])),
            'completion_rate': 0
        } for d in db.government_deadlines.find()]
        
        user_stats = [{
            'name': u.get('name', ''),
            'subscribed_deadlines': db.government_deadlines.count_documents({'subscribers': u.get('email')}),
            'active_deadlines': db.government_deadlines.count_documents({'subscribers': u.get('email')}),
            'completion_rate': 0
        } for u in users.find({}, {'password': 0})]
        
        return jsonify({
            'summary': {
                'total_users': total_users,
                'active_users': active_users,
                'total_deadlines': total_deadlines
            },
            'deadlines': deadline_stats,
            'users': user_stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/statistics', methods=['GET'])
@jwt_required()
def get_user_statistics():
    try:
        user_id = get_jwt_identity()
        user_deadlines = list(db.deadlines.find({'user_id': user_id}))
        
        return jsonify({
            'total_tasks': len(user_deadlines),
            'in_progress': sum(1 for d in user_deadlines if d.get('status') == 'In Progress'),
            'completed': sum(1 for d in user_deadlines if d.get('status') == 'Completed'),
            'urgent': sum(1 for d in user_deadlines if d.get('priority') == 'High')
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)