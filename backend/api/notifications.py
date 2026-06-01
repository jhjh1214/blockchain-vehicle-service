from flask import Blueprint, request, jsonify
from api.middleware import token_required
from db.models import Notification, db
from extensions import limiter

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('', methods=['GET'])
@token_required
@limiter.limit('60 per minute')
def list_notifications():
    user_id = request.user['user_id']
    limit = min(int(request.args.get('limit', 30)), 100)
    notifs = (
        Notification.query
        .filter_by(user_id=user_id)
        .order_by(Notification.read.asc(), Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify({'notifications': [n.to_dict() for n in notifs]}), 200


@notifications_bp.route('/count', methods=['GET'])
@token_required
def unread_count():
    count = Notification.query.filter_by(user_id=request.user['user_id'], read=False).count()
    return jsonify({'unread': count}), 200


@notifications_bp.route('/<int:notif_id>/read', methods=['POST'])
@token_required
def mark_read(notif_id):
    n = Notification.query.filter_by(id=notif_id, user_id=request.user['user_id']).first()
    if not n:
        return jsonify({'error': 'Not found'}), 404
    n.read = True
    db.session.commit()
    return jsonify({'message': 'Marked as read'}), 200


@notifications_bp.route('/read-all', methods=['POST'])
@token_required
def mark_all_read():
    Notification.query.filter_by(user_id=request.user['user_id'], read=False).update({'read': True})
    db.session.commit()
    return jsonify({'message': 'All notifications marked as read'}), 200
