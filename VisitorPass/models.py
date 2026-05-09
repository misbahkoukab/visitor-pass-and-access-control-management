from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.name = user_data['name']
        self.role = user_data['role']
        self.password_hash = user_data.get('password_hash')
        self.created_at = user_data.get('created_at', datetime.utcnow())
        # Use a backing attribute for active state to avoid clashing
        # with any property implementation from mixins or frameworks.
        self._is_active = user_data.get('is_active', True)

    @property
    def is_active(self):
        return bool(getattr(self, '_is_active', True))

    @is_active.setter
    def is_active(self, value):
        self._is_active = bool(value)
    
    @staticmethod
    def check_password(password_hash, password):
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def generate_password_hash(password):
        return generate_password_hash(password)

class Visitor:
    def __init__(self, data):
        self.visitor_id = data.get('visitor_id')
        self.title = data.get('title')
        self.full_name = data.get('full_name')
        self.contact_number = data.get('contact_number')
        self.email = data.get('email')
        self.purpose = data.get('purpose')
        self.authorized_zones = data.get('authorized_zones', [])
        self.start_datetime = data.get('start_datetime')
        self.end_datetime = data.get('end_datetime')
        self.qr_data = data.get('qr_data')
        self.current_location = data.get('current_location')
        self.created_at = data.get('created_at', datetime.utcnow())
        self.created_by = data.get('created_by')
        self.is_active = data.get('is_active', True)
    
    @staticmethod
    def generate_visitor_id():
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_suffix = secrets.token_hex(3).upper()
        return f"VIS{timestamp}{random_suffix}"

class AccessLog:
    def __init__(self, data):
        self.visitor_id = data.get('visitor_id')
        self.visitor_name = data.get('visitor_name')
        self.zone = data.get('zone')
        self.access_type = data.get('access_type')  # 'entry' or 'exit'
        self.status = data.get('status')  # 'granted' or 'denied'
        self.timestamp = data.get('timestamp', datetime.utcnow())
        self.reason = data.get('reason')