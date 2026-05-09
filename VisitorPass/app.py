from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from functools import wraps
import json

from config import Config
from models import User, Visitor, AccessLog
from utils import generate_qr_code, validate_qr_data, is_visit_active, format_datetime

app = Flask(__name__)
app.config.from_object(Config)

# MongoDB setup
mongo = PyMongo(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Make a `now()` callable available in Jinja templates (returns UTC now)
app.jinja_env.globals['now'] = datetime.utcnow

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

# Initialize admin user
def init_admin():
    admin = mongo.db.users.find_one({'email': 'admin@techcorp.com'})
    if not admin:
        admin_data = {
            'email': 'admin@techcorp.com',
            'name': 'Administrator',
            'role': 'admin',
            'password_hash': User.generate_password_hash('admin123'),
            'created_at': datetime.utcnow(),
            'is_active': True
        }
        mongo.db.users.insert_one(admin_data)
        print("Admin user created successfully!")

# Role-based access decorator
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('receptionist_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_data = mongo.db.users.find_one({'email': email})
        
        if user_data and User.check_password(user_data['password_hash'], password):
            if not user_data.get('is_active', True):
                flash('Your account has been deactivated. Contact administrator.', 'danger')
                return redirect(url_for('login'))
            
            user = User(user_data)
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('receptionist_dashboard'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register')
def register():
    # Public registration is disabled. Admins should create accounts via admin panel.
    flash('Public registration is disabled. Ask an administrator to create an account.', 'warning')
    return redirect(url_for('login'))


@app.route('/admin/create-user', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_create_user():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role') or 'receptionist'

        if not all([name, email, password]):
            flash('Name, email and password are required', 'danger')
            return redirect(url_for('admin_create_user'))

        existing_user = mongo.db.users.find_one({'email': email})
        if existing_user:
            flash('Email already registered', 'danger')
            return redirect(url_for('admin_create_user'))

        user_data = {
            'email': email,
            'name': name,
            'role': role,
            'password_hash': User.generate_password_hash(password),
            'created_at': datetime.utcnow(),
            'is_active': True
        }

        mongo.db.users.insert_one(user_data)
        flash('User account created successfully', 'success')
        return redirect(url_for('manage_users'))

    return render_template('admin/create_user.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

# Receptionist Routes

@app.route('/receptionist/dashboard')
@login_required
@role_required('receptionist')
def receptionist_dashboard():
    # Get today's visitors
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    visitors = list(mongo.db.visitors.find({
        'created_at': {'$gte': today_start, '$lt': today_end}
    }).sort('created_at', -1))
    
    # Get active visitors
    active_visitors = list(mongo.db.visitors.find({
        'is_active': True,
        'end_datetime': {'$gte': datetime.utcnow()}
    }))
    
    stats = {
        'total_today': len(visitors),
        'active_now': len(active_visitors),
        'meetings': len([v for v in visitors if v['purpose'] == 'Meeting']),
        'vip_visitors': len([v for v in visitors if v['purpose'] == 'VIP Visitor'])
    }
    
    return render_template('receptionist/dashboard.html', visitors=visitors, stats=stats)

@app.route('/receptionist/register-visitor', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def register_visitor():
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title')
        full_name = request.form.get('full_name')
        contact_number = request.form.get('contact_number')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        purpose = request.form.get('purpose')
        start_datetime = datetime.fromisoformat(request.form.get('start_datetime'))
        end_datetime = datetime.fromisoformat(request.form.get('end_datetime'))
        
        # Get authorized zones (can be customized)
        authorized_zones = request.form.getlist('authorized_zones')
        if not authorized_zones:
            authorized_zones = Config.ZONE_MAPPINGS.get(purpose, ['Reception', 'Lobby'])
        
        # Generate unique visitor ID
        visitor_id = Visitor.generate_visitor_id()
        
        # Create QR data
        qr_data = {
            'visitor_id': visitor_id,
            'visitor_name': f"{title} {full_name}",
            'authorized_zones': authorized_zones,
            'valid_from': start_datetime.isoformat(),
            'valid_until': end_datetime.isoformat()
        }
        
        qr_code_base64 = generate_qr_code(qr_data)
        
        # Save visitor to database
        visitor_data = {
            'visitor_id': visitor_id,
            'title': title,
            'full_name': full_name,
            'contact_number': contact_number,
            'email': email,
            'purpose': purpose,
            'authorized_zones': authorized_zones,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'qr_data': json.dumps(qr_data),
            'qr_code_image': qr_code_base64,
            'current_location': None,
            'created_at': datetime.utcnow(),
            'created_by': current_user.id,
            'is_active': True
        }
        # If a password was provided, create a user account for this visitor
        if password:
            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return redirect(url_for('register_visitor'))

            # prevent creating user if email already exists
            existing_user = mongo.db.users.find_one({'email': email})
            if existing_user:
                flash('A user with this email already exists. Visitor registered without login.', 'warning')
            else:
                user_data = {
                    'email': email,
                    'name': f"{title} {full_name}",
                    'role': 'user',
                    'password_hash': User.generate_password_hash(password),
                    'created_at': datetime.utcnow(),
                    'is_active': True,
                    'authorized_zones': authorized_zones
                }
                res = mongo.db.users.insert_one(user_data)
                visitor_data['user_id'] = str(res.inserted_id)

        mongo.db.visitors.insert_one(visitor_data)

        flash('Visitor registered successfully!', 'success')
        return redirect(url_for('visitor_pass', visitor_id=visitor_id))
    
    purposes = list(Config.ZONE_MAPPINGS.keys())
    all_zones = Config.ALL_ZONES
    
    return render_template('receptionist/register_visitor.html', purposes=purposes, all_zones=all_zones)


@app.route('/receptionist/create-user', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def receptionist_create_user():
    # This route is now handled by `register_visitor` which supports creating
    # a user account when a password is provided in the visitor form.
    return redirect(url_for('register_visitor'))

@app.route('/receptionist/visitor-pass/<visitor_id>')
@login_required
@role_required('receptionist')
def visitor_pass(visitor_id):
    visitor = mongo.db.visitors.find_one({'visitor_id': visitor_id})
    
    if not visitor:
        flash('Visitor not found', 'danger')
        return redirect(url_for('receptionist_dashboard'))
    
    return render_template('receptionist/visitor_pass.html', visitor=visitor, format_datetime=format_datetime)

# Zone Access Routes

@app.route('/zones')
@login_required
def zone_access():
    all_zones = Config.ALL_ZONES
    return render_template('zones/zone_access.html', zones=all_zones)

@app.route('/zones/scan/<zone_name>')
@login_required
def scan_zone(zone_name):
    return render_template('zones/scan_qr.html', zone_name=zone_name)

@app.route('/api/verify-access', methods=['POST'])
@login_required
def verify_access():
    data = request.json
    qr_string = data.get('qr_data')
    zone_name = data.get('zone_name')
    # First, try to validate QR-style payload
    qr_data = validate_qr_data(qr_string)
    visitor = None
    visitor_id = None

    if qr_data:
        visitor_id = qr_data.get('visitor_id')
        visitor = mongo.db.visitors.find_one({'visitor_id': visitor_id})
    else:
        # Try to parse manual-entry JSON { visitor_id: '...' }
        try:
            parsed = json.loads(qr_string)
            if isinstance(parsed, dict) and parsed.get('visitor_id'):
                visitor_id = parsed.get('visitor_id')
                visitor = mongo.db.visitors.find_one({'visitor_id': visitor_id})
        except Exception:
            # Not JSON - maybe plain visitor id string
            if qr_string:
                visitor_id = qr_string
                visitor = mongo.db.visitors.find_one({'visitor_id': visitor_id})
    
    # If visitor found without visitor_id (from DB), set it
    if visitor and not visitor_id:
        visitor_id = visitor.get('visitor_id')

    if not visitor:
        return jsonify({
            'status': 'denied',
            'message': 'Visitor not found',
            'voice_message': 'Access denied. Visitor not found.'
        })
    
    # Determine start/end datetimes: prefer QR payload if present, else stored visitor datetimes
    start_dt = None
    end_dt = None
    try:
        if qr_data and qr_data.get('valid_from') and qr_data.get('valid_until'):
            start_dt = qr_data.get('valid_from')
            end_dt = qr_data.get('valid_until')
        else:
            start_dt = visitor.get('start_datetime')
            end_dt = visitor.get('end_datetime')
    except Exception:
        start_dt = visitor.get('start_datetime')
        end_dt = visitor.get('end_datetime')

    # Check if visit is active
    if not is_visit_active(start_dt, end_dt):
        # Log with details for debugging
        log_access(visitor.get('visitor_id') or visitor_id, visitor['full_name'], zone_name, 'entry', 'denied', 'Visit expired')
        return jsonify({
            'status': 'denied',
            'message': 'Visitor pass has expired',
            'voice_message': 'Access denied. Pass expired.'
        })
    
    # Check zone authorization
    if zone_name not in visitor['authorized_zones']:
        log_access(visitor_id, visitor['full_name'], zone_name, 'entry', 'denied', 'Unauthorized zone')
        return jsonify({
            'status': 'denied',
            'message': f'Not authorized to access {zone_name}',
            'voice_message': 'Access denied. Permission required to access this area.'
        })
    
    # Auto-logout from previous location
    if visitor.get('current_location') and visitor['current_location'] != zone_name:
        log_access(visitor_id, visitor['full_name'], visitor['current_location'], 'exit', 'granted', 'Auto logout')
    
    # Update current location
    mongo.db.visitors.update_one(
        {'visitor_id': visitor_id},
        {'$set': {'current_location': zone_name}}
    )
    
    # Log successful access
    log_access(visitor_id, visitor['full_name'], zone_name, 'entry', 'granted', 'Access granted')
    
    visitor_name = f"{visitor['title']} {visitor['full_name']}"
    
    return jsonify({
        'status': 'granted',
        'message': f'Welcome {visitor_name}',
        'voice_message': f"Access granted. Welcome {visitor['title']} {visitor['full_name']}.",
        'visitor_name': visitor_name,
        'zone': zone_name
    })

def log_access(visitor_id, visitor_name, zone, access_type, status, reason=None):
    """Log access attempt"""
    log_data = {
        'visitor_id': visitor_id,
        'visitor_name': visitor_name,
        'zone': zone,
        'access_type': access_type,
        'status': status,
        'timestamp': datetime.utcnow(),
        'reason': reason
    }
    mongo.db.access_logs.insert_one(log_data)

# Admin Routes

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    # Get statistics
    total_visitors = mongo.db.visitors.count_documents({})
    active_visitors = mongo.db.visitors.count_documents({
        'is_active': True,
        'end_datetime': {'$gte': datetime.utcnow()}
    })
    
    total_users = mongo.db.users.count_documents({'role': 'receptionist'})
    total_zones = len(Config.ALL_ZONES)
    
    # Recent visitors
    recent_visitors = list(mongo.db.visitors.find().sort('created_at', -1).limit(10))
    
    # Recent access logs
    recent_logs = list(mongo.db.access_logs.find().sort('timestamp', -1).limit(20))
    
    # Get visitors by purpose for chart
    purpose_counts = {}
    for purpose in Config.ZONE_MAPPINGS.keys():
        count = mongo.db.visitors.count_documents({'purpose': purpose})
        purpose_counts[purpose] = count
    
    stats = {
        'total_visitors': total_visitors,
        'active_visitors': active_visitors,
        'total_users': total_users,
        'total_zones': total_zones
    }
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_visitors=recent_visitors,
                         recent_logs=recent_logs,
                         purpose_counts=purpose_counts,
                         format_datetime=format_datetime)


@app.route('/user/dashboard')
@login_required
@role_required('user')
def user_dashboard():
    # Load user document
    user_doc = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})

    # Find visitor record linked to this user (if any)
    visitor = mongo.db.visitors.find_one({'user_id': current_user.id})

    # Recent access logs for this visitor (or by email fallback)
    recent_logs = []
    if visitor:
        recent_logs = list(mongo.db.access_logs.find({'visitor_id': visitor.get('visitor_id')}).sort('timestamp', -1).limit(20))
    else:
        recent_logs = list(mongo.db.access_logs.find({'visitor_name': {'$regex': user_doc.get('name',''), '$options': 'i'}}).sort('timestamp', -1).limit(20))

    return render_template('user/dashboard.html', user=user_doc, visitor=visitor, recent_logs=recent_logs, format_datetime=format_datetime)

@app.route('/admin/manage-zones')
@login_required
@role_required('admin')
def manage_zones():
    # Load zones from DB; initialize from config if empty
    zones_cursor = list(mongo.db.zones.find().sort('name', 1))
    if not zones_cursor:
        # initialize
        for z in Config.ALL_ZONES:
            mongo.db.zones.insert_one({'name': z})
        zones_cursor = list(mongo.db.zones.find().sort('name', 1))

    zones = [z['name'] for z in zones_cursor]

    # Compute active visitor counts per zone (visitors currently in that zone and not expired)
    zone_counts = {}
    now = datetime.utcnow()
    for zone in zones:
        try:
            count = mongo.db.visitors.count_documents({
                'current_location': zone,
                'is_active': True,
                'end_datetime': {'$gte': now}
            })
        except Exception:
            count = 0
        zone_counts[zone] = count

    return render_template('admin/manage_zones.html', zones=zones, zone_counts=zone_counts)


@app.route('/admin/add-zone', methods=['POST'])
@login_required
@role_required('admin')
def add_zone():
    zone_name = request.form.get('zone_name')
    if not zone_name:
        flash('Zone name required', 'danger')
        return redirect(url_for('manage_zones'))

    existing = mongo.db.zones.find_one({'name': zone_name})
    if existing:
        flash('Zone already exists', 'warning')
        return redirect(url_for('manage_zones'))

    mongo.db.zones.insert_one({'name': zone_name})
    flash('Zone added successfully', 'success')
    return redirect(url_for('manage_zones'))


@app.route('/admin/edit-zone/<zone_name>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_zone(zone_name):
    zone = mongo.db.zones.find_one({'name': zone_name})
    if not zone:
        flash('Zone not found', 'danger')
        return redirect(url_for('manage_zones'))

    if request.method == 'POST':
        new_name = request.form.get('new_name')
        if new_name:
            mongo.db.zones.update_one({'_id': zone['_id']}, {'$set': {'name': new_name}})
            # Also update any references in Config or collections if needed
            flash('Zone updated', 'success')
            return redirect(url_for('manage_zones'))

    return render_template('admin/edit_zone.html', zone=zone)


@app.route('/admin/delete-zone/<zone_name>', methods=['POST'])
@login_required
@role_required('admin')
def delete_zone(zone_name):
    mongo.db.zones.delete_one({'name': zone_name})
    flash('Zone deleted', 'warning')
    return redirect(url_for('manage_zones'))


@app.route('/admin/view-zone/<zone_name>')
@login_required
@role_required('admin')
def view_zone(zone_name):
    # show basic stats for zone
    granted_count = mongo.db.access_logs.count_documents({'zone': zone_name, 'status': 'granted'})
    denied_count = mongo.db.access_logs.count_documents({'zone': zone_name, 'status': 'denied'})
    recent_logs = list(mongo.db.access_logs.find({'zone': zone_name}).sort('timestamp', -1).limit(20))
    return render_template('admin/view_zone.html', zone=zone_name, granted=granted_count, denied=denied_count, recent_logs=recent_logs)

@app.route('/admin/manage-users')
@login_required
@role_required('admin')
def manage_users():
    # Show all non-admin users (receptionists, regular users)
    users = list(mongo.db.users.find({'role': {'$ne': 'admin'}}))
    return render_template('admin/manage_users.html', users=users)

@app.route('/admin/approve-user/<user_id>')
@login_required
@role_required('admin')
def approve_user(user_id):
    mongo.db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'is_active': True}}
    )
    flash('User approved successfully', 'success')
    return redirect(url_for('manage_users'))


@app.route('/admin/edit-user/<user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_user(user_id):
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        is_active = True if request.form.get('is_active') == 'on' else False

        update = {'name': name, 'email': email, 'role': role, 'is_active': is_active}
        if request.form.get('password'):
            update['password_hash'] = User.generate_password_hash(request.form.get('password'))

        mongo.db.users.update_one({'_id': ObjectId(user_id)}, {'$set': update})
        flash('User updated successfully', 'success')
        return redirect(url_for('manage_users'))

    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/deactivate-user/<user_id>')
@login_required
@role_required('admin')
def deactivate_user(user_id):
    mongo.db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'is_active': False}}
    )
    flash('User deactivated', 'warning')
    return redirect(url_for('manage_users'))

@app.route('/admin/analytics')
@login_required
@role_required('admin')
def analytics():
    # Daily visitor count for last 30 days
    daily_stats = []
    for i in range(30, 0, -1):
        date = datetime.utcnow() - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        count = mongo.db.visitors.count_documents({
            'created_at': {'$gte': date_start, '$lt': date_end}
        })
        
        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # Zone traffic
    zone_traffic = {}
    for zone in Config.ALL_ZONES:
        count = mongo.db.access_logs.count_documents({
            'zone': zone,
            'status': 'granted'
        })
        zone_traffic[zone] = count
    
    # Peak hours
    hour_traffic = {str(i): 0 for i in range(24)}
    logs = mongo.db.access_logs.find({'status': 'granted'})
    
    for log in logs:
        hour = log['timestamp'].hour
        hour_traffic[str(hour)] += 1
    
    return render_template('admin/analytics.html',
                         daily_stats=daily_stats,
                         zone_traffic=zone_traffic,
                         hour_traffic=hour_traffic)

@app.route('/admin/edit-visitor-zones/<visitor_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_visitor_zones(visitor_id):
    visitor = mongo.db.visitors.find_one({'visitor_id': visitor_id})
    
    if not visitor:
        flash('Visitor not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        new_zones = request.form.getlist('authorized_zones')
        
        mongo.db.visitors.update_one(
            {'visitor_id': visitor_id},
            {'$set': {'authorized_zones': new_zones}}
        )
        
        flash('Visitor zones updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    all_zones = Config.ALL_ZONES
    return render_template('admin/edit_visitor_zones.html', visitor=visitor, all_zones=all_zones)

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# Template filters
@app.template_filter('datetime')
def datetime_filter(value):
    return format_datetime(value)

if __name__ == '__main__':
    with app.app_context():
        init_admin()
    app.run(debug=True, host='0.0.0.0', port=5000)