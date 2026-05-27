import time
from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from api.utils import sanitize, validate_vin, paginate
from core import vehicle_service
from db.repositories import vehicles as vehicle_repo, users as user_repo
from db.models import VehicleVINMapping, WarrantyClaimMetadata
from config import Config
from extensions import limiter

vehicle_bp = Blueprint('vehicle', __name__)


@vehicle_bp.route('/register', methods=['POST'])
@role_required('MANUFACTURER')
def register_vehicle():
    data = request.get_json() or {}
    try:
        vin         = validate_vin(data.get('vin', ''))
        owner_email = sanitize(data.get('owner_email', ''), 255).lower() or None
        make        = sanitize(data.get('make', ''), 50)
        model       = sanitize(data.get('model', ''), 50)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    try:
        year = int(data.get('year', 0)) if data.get('year') else None
    except (TypeError, ValueError):
        return jsonify({'error': 'year must be an integer'}), 400

    mfr_brand = request.user.get('brand', '')
    if mfr_brand and make.lower() != mfr_brand.lower():
        return jsonify({'error': f"Brand mismatch: your account is authorised for '{mfr_brand}' vehicles only"}), 403

    try:
        result = vehicle_service.register_vehicle(
            vin=vin,
            owner_email=owner_email,
            warranty_years=int(data.get('warranty_years', 3)),
            make=make,
            model=model,
            year=year,
            from_address=Config.DEPLOYER_ADDRESS,
            registered_by=request.user['blockchain_address']
        )
        return jsonify(result), 200
    except (ValueError, LookupError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/claim', methods=['POST'])
@role_required('OWNER')
def claim_vehicle():
    """Owner claims a manufacturer pre-registered (pending) vehicle."""
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    try:
        result = vehicle_service.claim_vehicle(
            vin=vin,
            owner_address=request.user['blockchain_address']
        )
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/my-vehicles', methods=['GET'])
@token_required
def get_my_vehicles():
    try:
        vehicles = vehicle_service.get_my_vehicles(request.user['blockchain_address'])
        result = paginate(vehicles, request.args)
        return jsonify({**result, 'vehicles': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/transfer', methods=['POST'])
@token_required
def transfer_vehicle():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    new_owner_email = sanitize(data.get('new_owner_email', ''), 255).lower()
    if not new_owner_email:
        return jsonify({'error': 'new_owner_email required'}), 400
    try:
        result = vehicle_service.transfer_vehicle(
            vin=vin,
            new_owner_email=new_owner_email,
            from_address=request.user['blockchain_address']
        )
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/<vin>', methods=['GET'])
@token_required
def get_vehicle(vin):
    try:
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        result = vehicle_service.get_vehicle(vin)
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/fleet', methods=['GET'])
@role_required('MANUFACTURER')
def get_fleet():
    """Paginated list of vehicles registered by this manufacturer."""
    mfr_address = request.user['blockchain_address']
    query = VehicleVINMapping.query.filter_by(registered_by=mfr_address)
    all_vehicles = query.order_by(VehicleVINMapping.created_at.desc()).all()
    items = [v.to_dict() for v in all_vehicles]
    result = paginate(items, request.args)
    result['vehicles'] = result.pop('items')
    return jsonify(result), 200


@vehicle_bp.route('/stats', methods=['GET'])
@role_required('MANUFACTURER')
def get_manufacturer_stats():
    mfr_address    = request.user['blockchain_address']
    total_vehicles = VehicleVINMapping.query.filter_by(registered_by=mfr_address).count()
    sc_total       = user_repo.count_by_role('SERVICE_CENTER')
    sc_active      = user_repo.count_by_role_status('SERVICE_CENTER', 'active')
    sc_pending     = user_repo.count_by_role_status('SERVICE_CENTER', 'pending')
    warranty_claims = WarrantyClaimMetadata.query.count()
    return jsonify({
        'total_vehicles':  total_vehicles,
        'sc_total':        sc_total,
        'sc_active':       sc_active,
        'sc_pending':      sc_pending,
        'warranty_claims': warranty_claims,
    }), 200


@vehicle_bp.route('/dashboard-stats', methods=['GET'])
@role_required('MANUFACTURER')
def get_dashboard_stats():
    """Consolidated manufacturer dashboard stats — single endpoint matching FYP1 spec."""
    import time as _time
    from datetime import datetime as _dt, timedelta as _td
    from db.models import ServiceMetadata, db as _db
    from db.models import User

    mfr_address = request.user['blockchain_address']

    total_vehicles    = VehicleVINMapping.query.filter_by(registered_by=mfr_address).count()
    active_warranties = VehicleVINMapping.query.filter(
        VehicleVINMapping.registered_by == mfr_address,
        VehicleVINMapping.warranty_expiry > int(_time.time())
    ).count()
    sc_total          = user_repo.count_by_role('SERVICE_CENTER')
    sc_active         = user_repo.count_by_role_status('SERVICE_CENTER', 'active')
    sc_pending        = user_repo.count_by_role_status('SERVICE_CENTER', 'pending')
    warranty_claims   = WarrantyClaimMetadata.query.count()

    month_start = _dt.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    services_this_month = ServiceMetadata.query.filter(
        ServiceMetadata.created_at >= month_start
    ).count()

    # Service type distribution (pie chart)
    service_type_counts: dict = {}
    for row in ServiceMetadata.query.with_entities(
        ServiceMetadata.service_type, _db.func.count(ServiceMetadata.id)
    ).group_by(ServiceMetadata.service_type).all():
        service_type_counts[row[0] or 'Other'] = row[1]

    # Warranty claim trend — last 6 months (line chart)
    claim_trend: list = []
    for i in range(5, -1, -1):
        ref = _dt.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # shift back i months
        month = (ref.month - i - 1) % 12 + 1
        year  = ref.year + ((ref.month - i - 1) // 12)
        start = _dt(year, month, 1)
        if month == 12:
            end = _dt(year + 1, 1, 1)
        else:
            end = _dt(year, month + 1, 1)
        count = WarrantyClaimMetadata.query.filter(
            WarrantyClaimMetadata.created_at >= start,
            WarrantyClaimMetadata.created_at < end
        ).count()
        claim_trend.append({'month': start.strftime('%b %Y'), 'count': count})

    # Top 5 service centres by submission volume (bar chart)
    top_sc_rows = ServiceMetadata.query.with_entities(
        ServiceMetadata.service_center_address,
        _db.func.count(ServiceMetadata.id).label('submissions')
    ).filter(
        ServiceMetadata.service_center_address.isnot(None)
    ).group_by(
        ServiceMetadata.service_center_address
    ).order_by(
        _db.desc('submissions')
    ).limit(5).all()

    top_service_centers = []
    for addr, count in top_sc_rows:
        sc_user = User.query.filter_by(blockchain_address=addr, role='SERVICE_CENTER').first()
        label = (sc_user.name or sc_user.email) if sc_user else addr[:10] + '…'
        disputed = ServiceMetadata.query.filter_by(
            service_center_address=addr, disputed=True
        ).count()
        rate = round(disputed / count * 100, 1) if count else 0.0
        top_service_centers.append({
            'label': label,
            'address': addr,
            'submissions': count,
            'disputed': disputed,
            'dispute_rate': rate,
            'flagged': rate > 10.0,
        })

    return jsonify({
        'total_vehicles':            total_vehicles,
        'active_warranties':         active_warranties,
        'sc_total':                  sc_total,
        'sc_active':                 sc_active,
        'sc_pending':                sc_pending,
        'warranty_claims':           warranty_claims,
        'services_this_month':       services_this_month,
        'service_type_distribution': service_type_counts,
        'warranty_claim_trend':      claim_trend,
        'top_service_centers':       top_service_centers,
    }), 200


@vehicle_bp.route('/public/<vin>', methods=['GET'])
@limiter.limit('30 per minute')
def get_vehicle_public(vin):
    """Public vehicle verification — no authentication required."""
    try:
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping:
        return jsonify({'error': 'Vehicle not found'}), 404

    try:
        from blockchain.adapters.vehicle_registry import vehicle_registry
        from blockchain.adapters.service_log import service_log
        vehicle_data = vehicle_registry.get_vehicle(vin)
        if not vehicle_data.get('exists'):
            return jsonify({'error': 'Vehicle not found on blockchain'}), 404

        finalized = service_log.get_finalized_services(vin) or []
    except Exception:
        vehicle_data = {}
        finalized = []

    warranty_expiry = vehicle_data.get('warranty_expiry', 0)
    return jsonify({
        'vin':    vin,
        'make':   mapping.make,
        'model':  mapping.model,
        'year':   mapping.year,
        'warranty': {
            'expiry':   warranty_expiry,
            'is_valid': warranty_expiry > int(time.time()) if warranty_expiry else False,
        },
        'service_records': finalized,
        'registered_at': mapping.created_at.isoformat() if mapping.created_at else None,
    }), 200


@vehicle_bp.route('/owner/vehicles', methods=['GET'])
@role_required('OWNER')
def get_owner_vehicles():
    try:
        vehicles = vehicle_service.get_my_vehicles(request.user['blockchain_address'])
        result = paginate(vehicles, request.args)
        return jsonify({**result, 'vehicles': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/activity-feed', methods=['GET'])
@role_required('MANUFACTURER')
def activity_feed():
    """Recent activity feed: vehicle registrations, warranty claims, and disputes."""
    from db.models import VehicleVINMapping, ServiceMetadata, WarrantyClaimMetadata

    registrations = VehicleVINMapping.query.order_by(VehicleVINMapping.created_at.desc()).limit(8).all()
    claims = WarrantyClaimMetadata.query.order_by(WarrantyClaimMetadata.created_at.desc()).limit(8).all()
    disputes = ServiceMetadata.query.filter_by(disputed=True).order_by(ServiceMetadata.created_at.desc()).limit(8).all()

    feed = []
    for v in registrations:
        feed.append({
            'type': 'registration',
            'vin': v.vin,
            'description': f"{v.make or ''} {v.model or ''}".strip() or v.vin,
            'timestamp': v.created_at.isoformat() if v.created_at else None,
        })
    for c in claims:
        desc = (c.issue_description or '')[:80]
        feed.append({
            'type': 'warranty_claim',
            'vin': c.vin,
            'description': desc or 'Warranty claim submitted',
            'timestamp': c.created_at.isoformat() if c.created_at else None,
        })
    for d in disputes:
        feed.append({
            'type': 'dispute',
            'vin': d.vin,
            'description': d.service_type or 'Service record disputed',
            'timestamp': d.created_at.isoformat() if d.created_at else None,
        })

    feed.sort(key=lambda x: x.get('timestamp') or '', reverse=True)
    return jsonify({'feed': feed[:15]}), 200
