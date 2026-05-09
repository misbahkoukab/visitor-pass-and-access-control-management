import qrcode
from io import BytesIO
import base64
from datetime import datetime, timezone
import json

def generate_qr_code(data):
    """Generate QR code and return as base64 string"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    qr_data = json.dumps(data)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return img_str

def validate_qr_data(qr_string):
    """Validate and parse QR code data"""
    try:
        data = json.loads(qr_string)
        required_keys = ['visitor_id', 'visitor_name', 'authorized_zones', 'valid_until']
        
        if all(key in data for key in required_keys):
            return data
        return None
    except:
        return None

def is_visit_active(start_datetime, end_datetime):
    """Check if visit is currently active"""
    def _parse(dt):
        if isinstance(dt, str):
            s = dt
            # Accept trailing Z as UTC
            if s.endswith('Z'):
                s = s.replace('Z', '+00:00')
            return datetime.fromisoformat(s)
        return dt

    start = _parse(start_datetime)
    end = _parse(end_datetime)

    # If either datetime is timezone-aware, compare in UTC with aware now
    if (getattr(start, 'tzinfo', None) is not None) or (getattr(end, 'tzinfo', None) is not None):
        now = datetime.now(timezone.utc)

        def _to_utc(dt):
            if getattr(dt, 'tzinfo', None) is None:
                # assume naive datetimes are in UTC
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        start_utc = _to_utc(start)
        end_utc = _to_utc(end)
        return start_utc <= now <= end_utc

    # Both are naive datetimes — compare using local server time
    now = datetime.now()
    return start <= now <= end

def format_datetime(dt):
    """Format datetime for display"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    return dt.strftime('%d %b %Y, %I:%M %p')