import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/visitor_management'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Zone-Purpose Mapping
    ZONE_MAPPINGS = {
        'Meeting': ['Reception', 'Meeting Room A', 'Meeting Room B', 'Cafeteria'],
        'Company Visit': ['Reception', 'Lobby', 'Cafeteria', 'Conference Hall'],
        'Employee Visit': ['Reception', 'Lobby', 'Cafeteria', 'Office Floor 1'],
        'VIP Visitor': ['Reception', 'Lobby', 'Meeting Room A', 'Meeting Room B', 'Conference Hall', 'Executive Floor', 'Cafeteria'],
        'Vendor': ['Reception', 'Lobby', 'Procurement Office'],
        'Interview': ['Reception', 'HR Department', 'Cafeteria'],
        'Contractor': ['Reception', 'Maintenance Area', 'Cafeteria'],
        'Delivery': ['Reception', 'Loading Bay']
    }
    
    # All available zones
    ALL_ZONES = [
        'Reception',
        'Lobby',
        'Meeting Room A',
        'Meeting Room B',
        'Conference Hall',
        'Office Floor 1',
        'Office Floor 2',
        'Executive Floor',
        'HR Department',
        'Cafeteria',
        'Procurement Office',
        'Maintenance Area',
        'Loading Bay',
        'IT Department',
        'Server Room',
        'Development Lab',
        'Innovation Center',
        'Design Studio',
        'Tech Support Center'
    ]