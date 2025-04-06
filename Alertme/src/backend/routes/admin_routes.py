from flask import Blueprint, request, jsonify
from ...database.db_connector import db
from ...utils.auth.auth_utils import admin_required
from bson import ObjectId
from datetime import datetime, timedelta
import jwt
import os

admin_routes = Blueprint('admin_routes', __name__)

def verify_admin_token(token):
    try:
        payload = jwt.decode(
            token,
            os.getenv('JWT_SECRET_KEY'),
            algorithms=['HS256']
        )
        return payload.get('is_admin', False)
    except:
        return False

@admin_routes.before_request
def verify_admin():
    if request.method != 'OPTIONS':
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        if not verify_admin_token(token):
            return jsonify({'message': 'Invalid admin token'}), 401

@admin_routes.route('/api/admin/verify', methods=['GET'])
@admin_required
def verify_admin(current_user):
    return jsonify({'message': 'Valid admin token', 'is_admin': True}), 200

@admin_routes.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users(current_user):
    try:
        users = list(db.users.find({}, {'password': 0}))
        for user in users:
            user['_id'] = str(user['_id'])
        return jsonify({'users': users})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_routes.route('/api/admin/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_user, user_id):
    try:
        result = db.users.delete_one({'_id': ObjectId(user_id)})
        if result.deleted_count:
            # Delete user's deadlines
            db.deadlines.delete_many({'user_id': user_id})
            return jsonify({'message': 'User deleted successfully'})
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_routes.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats(current_user):
    try:
        total_users = db.users.count_documents({})
        total_deadlines = db.deadlines.count_documents({})
        active_users = db.users.count_documents({'last_login': {'$gt': datetime.now() - timedelta(days=7)}})
        
        return jsonify({
            'total_users': total_users,
            'total_deadlines': total_deadlines,
            'active_users': active_users
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
