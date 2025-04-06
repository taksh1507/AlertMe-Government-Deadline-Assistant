from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from ..models.user import User
import jwt
import os
from datetime import datetime, timedelta

auth = Blueprint('auth', __name__, url_prefix='/auth')  # Add url_prefix

@auth.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    if User.find_by_email(data['email']):
        return jsonify({'message': 'Email already registered'}), 400
        
    if User.find_by_phone(data['phone']):
        return jsonify({'message': 'Phone number already registered'}), 400
    
    user = User(
        name=data['name'],
        email=data['email'],
        phone=data['phone'],
        password=generate_password_hash(data['password'])
    )
    user.save()
    
    return jsonify({'message': 'User created successfully'}), 201

@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.find_by_email(data['email'])
    
    if user and check_password_hash(user.password, data['password']):
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200
    
    return jsonify({'message': 'Invalid email or password'}), 401

@auth.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    # Get admin credentials from environment variables
    admin_email = os.getenv('ADMIN_EMAIL', 'your_admin_email')
    admin_password = os.getenv('ADMIN_PASSWORD', 'your_admin_password')
    
    if email == admin_email and password == admin_password:
        # Generate admin token
        token = jwt.encode(
            {
                'user_id': 'admin',
                'is_admin': True,
                'exp': datetime.utcnow() + timedelta(days=1)
            },
            os.getenv('JWT_SECRET_KEY')
            algorithm='HS256'
        )
        
        return jsonify({
            'token': token,
            'message': 'Admin login successful'
        }), 200
    
    return jsonify({'message': 'Invalid admin credentials'}), 401