from flask import Blueprint, request, jsonify

from utils.email_utils import is_valid_email, generate_verification_code, send_verification_email

email_bp = Blueprint('email', __name__, url_prefix='/email')


@email_bp.route('/verification/send', methods=['POST'])
def send_verification():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    email = data.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400

    if not is_valid_email(email):
        return jsonify({'success': False, 'message': 'Invalid email format'}), 400

    code = generate_verification_code()
    send_verification_email(email, code)

    return jsonify({
        'success': True,
        'message': 'Verification code sent'
    })
