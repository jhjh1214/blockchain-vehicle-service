import time
from flask import Blueprint, request, jsonify

_stats_cache: dict = {}  # {mfr_address: {'data': dict, 'expires': float}}
_STATS_TTL = 15  # seconds


def invalidate_stats_cache() -> None:
    """Clear all cached dashboard stats (call after SC status changes)."""
    _stats_cache.clear()
from api.middleware import token_required, role_required
from api.utils import sanitize, validate_vin, paginate
from core import vehicle_service
from core import service_log_service
from db.repositories import vehicles as vehicle_repo, users as user_repo
from db.models import VehicleVINMapping, WarrantyClaimMetadata, VehicleRecall, RecallVINService
from db.models import db as _db
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

    year_raw = data.get('year')
    try:
        year = int(year_raw) if year_raw is not None else None
    except (TypeError, ValueError):
        return jsonify({'error': 'year must be an integer'}), 400
    if year is not None:
        import time as _time
        current_year = int(_time.strftime('%Y'))
        if year < 1886 or year > current_year + 1:
            return jsonify({'error': f'year must be between 1886 and {current_year + 1}'}), 400

    mfr_brand = request.user.get('brand', '')
    if mfr_brand and make.lower() != mfr_brand.lower():
        return jsonify({'error': f"Brand mismatch: your account is authorised for '{mfr_brand}' vehicles only"}), 403

    intended_owner_email = sanitize(data.get('intended_owner_email', ''), 255).lower() or None

    try:
        warranty_years = int(data.get('warranty_years', 3))
    except (TypeError, ValueError):
        return jsonify({'error': 'warranty_years must be an integer'}), 400
    if not (1 <= warranty_years <= 20):
        return jsonify({'error': 'warranty_years must be between 1 and 20'}), 400

    try:
        result = vehicle_service.register_vehicle(
            vin=vin,
            owner_email=owner_email,
            warranty_years=warranty_years,
            make=make,
            model=model,
            year=year,
            from_address=Config.DEPLOYER_ADDRESS,
            registered_by=request.user['blockchain_address'],
            intended_owner_email=intended_owner_email,
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
        import logging; logging.getLogger(__name__).exception('claim_vehicle failed')
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/my-vehicles', methods=['GET'])
@role_required('OWNER')
def get_my_vehicles():
    try:
        vehicles = vehicle_service.get_my_vehicles(request.user['blockchain_address'])
        result = paginate(vehicles, request.args)
        return jsonify({**result, 'vehicles': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/transfer', methods=['POST'])
@role_required('OWNER')
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
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
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
        # Only the vehicle owner may see the owner's email address
        requester_address = request.user.get('blockchain_address', '')
        owner_address = result.get('owner', {}).get('address', '')
        if requester_address.lower() != owner_address.lower():
            result.get('owner', {}).pop('email', None)
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/fleet', methods=['GET'])
@role_required('MANUFACTURER')
def get_fleet():
    """Paginated list of vehicles registered by this manufacturer."""
    from db.models import ServiceMetadata, db as _db
    from datetime import datetime as _dt

    mfr_address = request.user['blockchain_address']
    all_vehicles = VehicleVINMapping.query.filter_by(registered_by=mfr_address).order_by(
        VehicleVINMapping.created_at.desc()
    ).all()

    vins = [v.vin for v in all_vehicles]
    service_stats: dict = {}
    if vins:
        for row in _db.session.query(
            ServiceMetadata.vin,
            _db.func.count(ServiceMetadata.id).label('cnt'),
            _db.func.max(ServiceMetadata.service_date).label('last_date'),
        ).filter(ServiceMetadata.vin.in_(vins)).group_by(ServiceMetadata.vin).all():
            service_stats[row.vin] = {
                'service_count': row.cnt,
                'last_service_date': row.last_date.isoformat() if row.last_date else None,
            }

    now = _dt.utcnow()
    items = []
    for v in all_vehicles:
        d = v.to_dict()
        st = service_stats.get(v.vin, {})
        d['service_count'] = st.get('service_count', 0)
        d['last_service_date'] = st.get('last_service_date')
        if st.get('last_service_date'):
            last = _dt.fromisoformat(st['last_service_date'])
            d['days_since_service'] = (now - last).days
        else:
            d['days_since_service'] = None
        items.append(d)

    result = paginate(items, request.args)
    result['vehicles'] = result.pop('items')
    return jsonify(result), 200


@vehicle_bp.route('/stats', methods=['GET'])
@role_required('MANUFACTURER')
def get_manufacturer_stats():
    from db.models import db as _db
    mfr_address = request.user['blockchain_address']
    mfr_brand   = request.user.get('brand', '')
    total_vehicles = VehicleVINMapping.query.filter_by(registered_by=mfr_address).count()
    sc_total       = user_repo.count_by_role_brand('SERVICE_CENTER', mfr_brand)
    sc_active      = user_repo.count_by_role_status_brand('SERVICE_CENTER', 'active', mfr_brand)
    sc_pending     = user_repo.count_by_role_status_brand('SERVICE_CENTER', 'pending', mfr_brand)
    mfr_vins_subq = _db.session.query(VehicleVINMapping.vin).filter_by(registered_by=mfr_address).scalar_subquery()
    warranty_claims = WarrantyClaimMetadata.query.filter(
        WarrantyClaimMetadata.vin.in_(mfr_vins_subq)
    ).count()
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
    mfr_brand   = request.user.get('brand', '')

    cached = _stats_cache.get(mfr_address)
    if cached and cached['expires'] > time.time():
        return jsonify(cached['data']), 200

    total_vehicles    = VehicleVINMapping.query.filter_by(registered_by=mfr_address).count()
    active_warranties = VehicleVINMapping.query.filter(
        VehicleVINMapping.registered_by == mfr_address,
        VehicleVINMapping.warranty_expiry > int(_time.time())
    ).count()
    sc_total  = user_repo.count_by_role_brand('SERVICE_CENTER', mfr_brand)
    sc_active = user_repo.count_by_role_status_brand('SERVICE_CENTER', 'active', mfr_brand)
    sc_pending = user_repo.count_by_role_status_brand('SERVICE_CENTER', 'pending', mfr_brand)

    # Subquery: VINs registered by this manufacturer (used to scope all per-vehicle metrics)
    mfr_vins_subq = _db.session.query(VehicleVINMapping.vin).filter_by(registered_by=mfr_address).scalar_subquery()

    warranty_claims = WarrantyClaimMetadata.query.filter(
        WarrantyClaimMetadata.vin.in_(mfr_vins_subq)
    ).count()

    month_start = _dt.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    services_this_month = ServiceMetadata.query.filter(
        ServiceMetadata.created_at >= month_start,
        ServiceMetadata.vin.in_(mfr_vins_subq)
    ).count()

    # Subquery: SC addresses belonging to this brand (for top-SC chart)
    brand_sc_subq = _db.session.query(User.blockchain_address).filter(
        User.role == 'SERVICE_CENTER',
        User.brand.ilike(mfr_brand) if mfr_brand else _db.true()
    ).scalar_subquery()

    # Service type distribution (pie chart) — only this manufacturer's vehicles
    service_type_counts: dict = {}
    for row in ServiceMetadata.query.with_entities(
        ServiceMetadata.service_type, _db.func.count(ServiceMetadata.id)
    ).filter(
        ServiceMetadata.vin.in_(mfr_vins_subq)
    ).group_by(ServiceMetadata.service_type).all():
        service_type_counts[row[0] or 'Other'] = row[1]

    # Warranty claim trend — last 6 months (line chart) — this manufacturer's vehicles only
    claim_trend: list = []
    for i in range(5, -1, -1):
        ref = _dt.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month = (ref.month - i - 1) % 12 + 1
        year  = ref.year + ((ref.month - i - 1) // 12)
        start = _dt(year, month, 1)
        if month == 12:
            end = _dt(year + 1, 1, 1)
        else:
            end = _dt(year, month + 1, 1)
        count = WarrantyClaimMetadata.query.filter(
            WarrantyClaimMetadata.created_at >= start,
            WarrantyClaimMetadata.created_at < end,
            WarrantyClaimMetadata.vin.in_(mfr_vins_subq)
        ).count()
        claim_trend.append({'month': start.strftime('%b %Y'), 'count': count})

    # Top 5 service centres by submission volume (bar chart) — this brand's SCs only
    top_sc_rows = ServiceMetadata.query.with_entities(
        ServiceMetadata.service_center_address,
        _db.func.count(ServiceMetadata.id).label('submissions')
    ).filter(
        ServiceMetadata.service_center_address.isnot(None),
        ServiceMetadata.service_center_address.in_(brand_sc_subq)
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

    # Fleet health score: warranty coverage (50%) + recent service activity (50%)
    recently_serviced = 0
    if total_vehicles > 0:
        ninety_days_ago = _dt.utcnow() - _td(days=90)
        recently_serviced = ServiceMetadata.query.with_entities(
            ServiceMetadata.vin
        ).filter(
            ServiceMetadata.vin.in_(mfr_vins_subq),
            ServiceMetadata.service_date >= ninety_days_ago,
        ).distinct().count()
    warranty_pct = (active_warranties / total_vehicles * 50) if total_vehicles else 0
    service_pct  = (recently_serviced / total_vehicles * 50) if total_vehicles else 0
    fleet_health_score = round(warranty_pct + service_pct)

    # Manufacturer ETH balance
    manufacturer_eth_balance = None
    try:
        from blockchain.client import web3_client
        from web3 import Web3
        mfr_checksum = Web3.to_checksum_address(mfr_address)
        balance_wei = web3_client.w3.eth.get_balance(mfr_checksum)
        manufacturer_eth_balance = round(float(Web3.from_wei(balance_wei, 'ether')), 4)
    except Exception:
        pass

    payload = {
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
        'fleet_health_score':        fleet_health_score,
        'manufacturer_eth_balance':  manufacturer_eth_balance,
    }
    _stats_cache[mfr_address] = {'data': payload, 'expires': time.time() + _STATS_TTL}
    return jsonify(payload), 200


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
        vehicle_data = vehicle_registry.get_vehicle(vin)
        if not vehicle_data.get('exists'):
            return jsonify({'error': 'Vehicle not found on blockchain'}), 404
    except Exception:
        vehicle_data = {}

    try:
        raw_finalized = service_log_service.get_finalized_services(vin) or []
        finalized = [dict(r, record_index=i) for i, r in enumerate(raw_finalized)]
    except Exception:
        finalized = []

    # Recall history for this VIN
    recall_history = []
    if mapping.registered_by:
        mfr = user_repo.find_by_blockchain_address(mapping.registered_by)
        if mfr and mfr.brand:
            all_recalls = VehicleRecall.query.filter_by(brand=mfr.brand).all()
            serviced_recall_ids = {
                s.recall_id for s in RecallVINService.query.filter_by(vin=vin).all()
            }
            for r in all_recalls:
                recall_history.append({
                    'recall_id': r.id,
                    'title': r.title,
                    'description': r.description,
                    'issued_at': r.created_at.isoformat() if r.created_at else None,
                    'status': r.status,
                    'serviced': r.id in serviced_recall_ids,
                })

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
        'recall_history': recall_history,
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

    from db.models import db as _db
    mfr_address = request.user['blockchain_address']
    mfr_vins_subq = _db.session.query(VehicleVINMapping.vin).filter_by(registered_by=mfr_address).scalar_subquery()

    registrations = VehicleVINMapping.query.filter_by(registered_by=mfr_address).order_by(VehicleVINMapping.created_at.desc()).limit(8).all()
    claims = WarrantyClaimMetadata.query.filter(
        WarrantyClaimMetadata.vin.in_(mfr_vins_subq)
    ).order_by(WarrantyClaimMetadata.created_at.desc()).limit(8).all()
    disputes = ServiceMetadata.query.filter(
        ServiceMetadata.disputed == True,
        ServiceMetadata.vin.in_(mfr_vins_subq)
    ).order_by(ServiceMetadata.created_at.desc()).limit(8).all()

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


@vehicle_bp.route('/export/<vin>', methods=['GET'])
@limiter.limit('10 per minute')
def export_vehicle_pdf(vin):
    """Generate a PDF vehicle history report (public, rate-limited)."""
    import io
    from datetime import datetime as _dt

    try:
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping:
        return jsonify({'error': 'Vehicle not found'}), 404

    try:
        from blockchain.adapters.vehicle_registry import vehicle_registry
        vehicle_data = vehicle_registry.get_vehicle(vin)
    except Exception:
        vehicle_data = {}

    try:
        finalized = service_log_service.get_finalized_services(vin) or []
    except Exception:
        finalized = []

    warranty_expiry = vehicle_data.get('warranty_expiry', 0)
    warranty_valid  = warranty_expiry > int(time.time()) if warranty_expiry else False
    warranty_date   = _dt.utcfromtimestamp(warranty_expiry).strftime('%d %b %Y') if warranty_expiry else 'N/A'

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=20*mm, rightMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)

        styles = getSampleStyleSheet()
        title_style  = ParagraphStyle('Title',  parent=styles['Title'],  fontSize=20, spaceAfter=4)
        sub_style    = ParagraphStyle('Sub',    parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#64748b'), spaceAfter=14)
        label_style  = ParagraphStyle('Label',  parent=styles['Normal'], fontSize=9,  textColor=colors.HexColor('#94a3b8'), spaceBefore=8, spaceAfter=2)
        value_style  = ParagraphStyle('Value',  parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#0f172a'))
        section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=13, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor('#1e293b'))
        footer_style = ParagraphStyle('Footer',  parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER, spaceBefore=20)

        story = []
        story.append(Paragraph('VehicleChain', title_style))
        story.append(Paragraph('Blockchain-Verified Vehicle History Report', sub_style))
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=16))

        # Vehicle identity
        story.append(Paragraph('Vehicle Information', section_style))
        info_data = [
            ['VIN', vin,         'Make',  mapping.make or '—'],
            ['Model', mapping.model or '—', 'Year', str(mapping.year) if mapping.year else '—'],
            ['Warranty Status', 'Active' if warranty_valid else 'Expired',
             'Warranty Expiry', warranty_date],
            ['Registered', mapping.created_at.strftime('%d %b %Y') if mapping.created_at else '—', '', ''],
        ]
        info_table = Table(info_data, colWidths=[35*mm, 65*mm, 35*mm, 35*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME',    (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE',    (0,0), (-1,-1), 10),
            ('FONTNAME',    (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME',    (2,0), (2,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR',   (0,0), (0,-1), colors.HexColor('#64748b')),
            ('TEXTCOLOR',   (2,0), (2,-1), colors.HexColor('#64748b')),
            ('BACKGROUND',  (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING',     (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
        ]))
        story.append(info_table)

        # Service records
        story.append(Paragraph('Service History', section_style))
        if finalized:
            hdr = ['#', 'Service Type', 'Date', 'Mileage (km)', 'Technician']
            rows = [hdr]
            for idx, rec in enumerate(finalized):
                meta = rec.get('metadata') or {}
                rows.append([
                    str(idx + 1),
                    meta.get('service_type') or '—',
                    meta.get('service_date', '')[:10] if meta.get('service_date') else '—',
                    str(meta.get('mileage') or '—'),
                    meta.get('technician_name') or '—',
                ])
            svc_table = Table(rows, colWidths=[12*mm, 55*mm, 32*mm, 35*mm, 36*mm])
            svc_table.setStyle(TableStyle([
                ('FONTNAME',    (0,0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE',    (0,0), (-1,-1), 9),
                ('BACKGROUND',  (0,0), (-1, 0), colors.HexColor('#1e293b')),
                ('TEXTCOLOR',   (0,0), (-1, 0), colors.white),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
                ('GRID',        (0,0), (-1,-1), 0.4, colors.HexColor('#e2e8f0')),
                ('PADDING',     (0,0), (-1,-1), 5),
            ]))
            story.append(svc_table)
        else:
            story.append(Paragraph('No finalized service records found.', sub_style))

        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0'), spaceBefore=20))
        story.append(Paragraph(
            f'Generated by VehicleChain on {_dt.utcnow().strftime("%d %b %Y %H:%M")} UTC  ·  Data verified on-chain',
            footer_style
        ))

        doc.build(story)
        buffer.seek(0)
        from flask import send_file
        safe_vin = vin.replace('/', '_')
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'VehicleChain_{safe_vin}.pdf',
        )
    except ImportError:
        return jsonify({'error': 'PDF generation not available — install reportlab'}), 503


@vehicle_bp.route('/fleet-export', methods=['GET'])
@role_required('MANUFACTURER')
@limiter.limit('5 per minute')
def export_fleet_pdf():
    """Generate a manufacturer-level fleet audit report PDF."""
    import io
    from datetime import datetime as _dt

    mfr_address = request.user['blockchain_address']
    mfr_brand   = request.user.get('brand', '') or 'Fleet'

    vehicles_list = VehicleVINMapping.query.filter_by(registered_by=mfr_address).order_by(
        VehicleVINMapping.created_at.desc()
    ).all()

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.enums import TA_CENTER

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=20*mm, rightMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)

        styles = getSampleStyleSheet()
        title_style   = ParagraphStyle('Title',   parent=styles['Title'],   fontSize=20, spaceAfter=4)
        sub_style     = ParagraphStyle('Sub',     parent=styles['Normal'],  fontSize=11, textColor=colors.HexColor('#64748b'), spaceAfter=14)
        section_style = ParagraphStyle('Section', parent=styles['Heading2'],fontSize=13, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor('#1e293b'))
        footer_style  = ParagraphStyle('Footer',  parent=styles['Normal'],  fontSize=8,  textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER, spaceBefore=20)

        story = []
        story.append(Paragraph('VehicleChain', title_style))
        story.append(Paragraph(f'Fleet Audit Report — {mfr_brand}', sub_style))
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=12))

        # Summary block
        now = _dt.utcnow()
        active_count = sum(1 for v in vehicles_list if v.warranty_expiry and v.warranty_expiry > int(time.time()))
        summary_data = [
            ['Total Vehicles', str(len(vehicles_list)), 'Active Warranties', str(active_count)],
            ['Brand', mfr_brand, 'Report Date', now.strftime('%d %b %Y %H:%M UTC')],
        ]
        summary_table = Table(summary_data, colWidths=[40*mm, 60*mm, 40*mm, 30*mm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE',   (0,0), (-1,-1), 10),
            ('FONTNAME',   (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME',   (2,0), (2,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR',  (0,0), (0,-1), colors.HexColor('#64748b')),
            ('TEXTCOLOR',  (2,0), (2,-1), colors.HexColor('#64748b')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING',    (0,0), (-1,-1), 6),
        ]))
        story.append(summary_table)

        # Vehicle table
        story.append(Paragraph('Registered Vehicles', section_style))
        if vehicles_list:
            from db.models import ServiceMetadata
            hdr = ['VIN', 'Make', 'Model', 'Year', 'Warranty', 'Services']
            rows = [hdr]
            for v in vehicles_list:
                warranty_ok = v.warranty_expiry and v.warranty_expiry > int(time.time())
                svc_count = ServiceMetadata.query.filter_by(vin=v.vin).count()
                rows.append([
                    v.vin or '—',
                    v.make or '—',
                    v.model or '—',
                    str(v.year) if v.year else '—',
                    'Active' if warranty_ok else 'Expired',
                    str(svc_count),
                ])
            col_w = [38*mm, 25*mm, 25*mm, 14*mm, 25*mm, 18*mm]
            tbl = Table(rows, colWidths=col_w)
            tbl.setStyle(TableStyle([
                ('FONTNAME',       (0,0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE',       (0,0), (-1,-1), 9),
                ('BACKGROUND',     (0,0), (-1, 0), colors.HexColor('#1e293b')),
                ('TEXTCOLOR',      (0,0), (-1, 0), colors.white),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
                ('GRID',           (0,0), (-1,-1), 0.4, colors.HexColor('#e2e8f0')),
                ('PADDING',        (0,0), (-1,-1), 5),
                ('TEXTCOLOR',      (4,1), (4,-1), colors.HexColor('#16a34a')),
            ]))
            story.append(tbl)
        else:
            story.append(Paragraph('No vehicles registered.', sub_style))

        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0'), spaceBefore=20))
        story.append(Paragraph(
            f'Generated by VehicleChain on {now.strftime("%d %b %Y %H:%M")} UTC  ·  Data verified on-chain',
            footer_style
        ))

        doc.build(story)
        buffer.seek(0)
        from flask import send_file
        safe_brand = mfr_brand.replace(' ', '_').replace('/', '_')
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'VehicleChain_Fleet_{safe_brand}.pdf',
        )
    except ImportError:
        return jsonify({'error': 'PDF generation not available — install reportlab'}), 503


@vehicle_bp.route('/recall', methods=['POST'])
@role_required('MANUFACTURER')
def send_recall():
    data = request.get_json() or {}
    title = sanitize(data.get('title', ''), 200)
    description = sanitize(data.get('message', '') or data.get('description', ''), 2000)
    affected_models = data.get('affected_models') or None  # list of model names or None
    if not title or not description:
        return jsonify({'error': 'title and message are required'}), 400

    brand = request.user.get('brand', '')
    issued_by_name = request.user.get('name', 'Manufacturer')

    # Persist recall to DB
    recall = VehicleRecall(
        brand=brand,
        issued_by_user_id=request.user['id'],
        title=title,
        description=description,
        affected_models=affected_models,
    )
    _db.session.add(recall)
    _db.session.commit()

    # Push notification to all owner mobile devices
    from core.notifications import broadcast_recall
    sent = broadcast_recall(title=title, body=description[:200], issued_by=issued_by_name)

    # Email all SC of the same brand
    try:
        sc_users = user_repo.find_service_centers(status='active', brand=brand)
        if sc_users:
            from core.email import send_email
            sc_emails = [sc.email for sc in sc_users if sc.email]
            for email in sc_emails:
                send_email(
                    to=email,
                    subject=f'[Recall Alert] {title}',
                    text=f'A recall has been issued by {issued_by_name}.\n\n'
                         f'Title: {title}\n\nDetails:\n{description}\n\n'
                         f'Please check your dashboard for details and mark recall services as completed for affected vehicles.',
                )
    except Exception:
        pass  # Email failure must not block the response

    return jsonify({'sent': sent, 'recall_id': recall.id}), 200


@vehicle_bp.route('/recalls', methods=['GET'])
@role_required('MANUFACTURER', 'SERVICE_CENTER')
def list_recalls():
    brand = request.user.get('brand', '')
    status_filter = request.args.get('status', 'active')
    query = VehicleRecall.query.filter_by(brand=brand)
    if status_filter in ('active', 'closed'):
        query = query.filter_by(status=status_filter)
    recalls = query.order_by(VehicleRecall.created_at.desc()).all()
    result = []
    for r in recalls:
        d = r.to_dict()
        d['serviced_count'] = len(r.vin_services)
        result.append(d)
    return jsonify({'recalls': result}), 200


@vehicle_bp.route('/recalls/owner', methods=['GET'])
@role_required('OWNER')
def list_recalls_owner():
    """Return active recalls for the owner's registered vehicles."""
    owner_addr = request.user.get('blockchain_address', '')
    vehicles = VehicleVINMapping.query.filter_by(owner_address=owner_addr).all()
    if not vehicles:
        return jsonify({'recalls': []}), 200

    # Collect brands from all vehicles the owner has
    brands = set()
    for v in vehicles:
        if v.registered_by:
            mfr = user_repo.find_by_blockchain_address(v.registered_by)
            if mfr and mfr.brand:
                brands.add(mfr.brand)

    if not brands:
        return jsonify({'recalls': []}), 200

    recalls = VehicleRecall.query.filter(
        VehicleRecall.brand.in_(brands),
        VehicleRecall.status == 'active'
    ).order_by(VehicleRecall.created_at.desc()).all()

    owner_vins = {v.vin for v in vehicles}
    result = []
    for r in recalls:
        d = r.to_dict()
        serviced_vins = {s.vin for s in r.vin_services}
        d['my_serviced_vins'] = list(owner_vins & serviced_vins)
        d['my_affected_vins'] = list(owner_vins)
        result.append(d)
    return jsonify({'recalls': result}), 200


@vehicle_bp.route('/recalls/<int:recall_id>/service', methods=['POST'])
@role_required('SERVICE_CENTER')
def mark_recall_serviced(recall_id):
    data = request.get_json() or {}
    vin = validate_vin(data.get('vin', ''))
    notes = sanitize(data.get('notes', ''), 500)

    recall = VehicleRecall.query.filter_by(id=recall_id, status='active').first()
    if not recall:
        return jsonify({'error': 'Recall not found or already closed'}), 404

    existing = RecallVINService.query.filter_by(recall_id=recall_id, vin=vin).first()
    if existing:
        return jsonify({'message': 'Already marked as serviced', 'service': existing.to_dict()}), 200

    svc = RecallVINService(
        recall_id=recall_id,
        vin=vin,
        sc_user_id=request.user['id'],
        notes=notes or None,
    )
    _db.session.add(svc)
    _db.session.commit()
    return jsonify({'message': f'VIN {vin} marked as recall serviced', 'service': svc.to_dict()}), 201


@vehicle_bp.route('/recalls/<int:recall_id>/close', methods=['POST'])
@role_required('MANUFACTURER')
def close_recall(recall_id):
    brand = request.user.get('brand', '')
    recall = VehicleRecall.query.filter_by(id=recall_id, brand=brand).first()
    if not recall:
        return jsonify({'error': 'Recall not found'}), 404
    recall.status = 'closed'
    _db.session.commit()
    return jsonify({'message': 'Recall closed'}), 200


@vehicle_bp.route('/recalls/check/<vin>', methods=['GET'])
@role_required('SERVICE_CENTER', 'MANUFACTURER', 'OWNER')
def check_vin_recalls(vin):
    """Check if a VIN's vehicle has any active recalls."""
    try:
        vin = validate_vin(vin)
    except Exception:
        return jsonify({'error': 'Invalid VIN'}), 400

    vm = VehicleVINMapping.query.filter_by(vin=vin).first()
    if not vm or not vm.registered_by:
        return jsonify({'recalls': []}), 200

    mfr = user_repo.find_by_blockchain_address(vm.registered_by)
    if not mfr or not mfr.brand:
        return jsonify({'recalls': []}), 200

    recalls = VehicleRecall.query.filter_by(brand=mfr.brand, status='active').all()
    serviced_recall_ids = {
        s.recall_id for s in RecallVINService.query.filter_by(vin=vin).all()
    }
    result = []
    for r in recalls:
        d = r.to_dict()
        d['serviced_for_vin'] = r.id in serviced_recall_ids
        result.append(d)
    return jsonify({'recalls': result}), 200


# ─── Integrity Reconciliation (manufacturer self-service) ─────────────────────

@vehicle_bp.route('/reconcile', methods=['POST'])
@role_required('MANUFACTURER', 'SERVICE_CENTER')
def reconcile_records():
    """
    Manufacturer triggers integrity check on their brand's service records.
    Re-computes SHA-256 from stored DB fields and compares to stored metadata_hash.
    Records are marked 'ok' or 'tampered' and the result is returned.

    Body: { "vin": "<VIN>" }   (optional — omit to check all vehicles of this brand)
    """
    import hashlib, json as _json
    from db.models import ServiceMetadata as _SM, db as _db
    from datetime import datetime as _dt

    data = request.get_json(silent=True) or {}
    vin_filter = data.get('vin', '').strip().upper() or None
    role       = request.user['role']
    addr       = request.user['blockchain_address']

    if role == 'MANUFACTURER':
        # Scope to all vehicles this manufacturer registered
        brand_vins_query = VehicleVINMapping.query.filter_by(registered_by=addr)
        if vin_filter:
            brand_vins_query = brand_vins_query.filter_by(vin=vin_filter)
        brand_vins = {v.vin for v in brand_vins_query.all()}
    else:
        # SERVICE_CENTER — scope to VINs they personally submitted services for
        from db.models import ServiceMetadata as _SM2
        sc_vins_query = _SM2.query.with_entities(_SM2.vin).filter(
            _SM2.service_center_address.ilike(addr)
        )
        if vin_filter:
            sc_vins_query = sc_vins_query.filter(_SM2.vin == vin_filter)
        brand_vins = {row.vin for row in sc_vins_query.all()}

    if not brand_vins:
        return jsonify({'checked': 0, 'ok': 0, 'tampered': 0, 'records': []}), 200

    rows = _SM.query.filter(_SM.vin.in_(brand_vins)).all()
    checked = ok_count = tampered_count = 0
    records_out = []

    for row in rows:
        checked += 1
        # Reconstruct exactly what submit_service() hashed
        meta = {
            'service_type':    row.service_type or '',
            'service_date':    row.service_date.isoformat() if row.service_date else '',
            'mileage':         row.mileage,
            'parts_replaced':  row.parts_replaced or '',
            'technician_name': row.technician_name or '',
            'service_notes':   row.service_notes or '',
            'ecu_modules':     [],
            'photos':          row.photos or [],
        }
        recomputed = '0x' + hashlib.sha256(
            _json.dumps(meta, sort_keys=True).encode()
        ).hexdigest()

        status = 'ok' if recomputed == (row.metadata_hash or '') else 'tampered'
        row.integrity_status     = status
        row.integrity_checked_at = _dt.utcnow()

        if status == 'ok':
            ok_count += 1
        else:
            tampered_count += 1
            records_out.append({
                'vin':            row.vin,
                'metadata_hash':  row.metadata_hash,
                'service_date':   row.service_date.isoformat() if row.service_date else None,
                'service_type':   row.service_type,
                'integrity':      status,
            })

    _db.session.commit()
    return jsonify({
        'checked':  checked,
        'ok':       ok_count,
        'tampered': tampered_count,
        'records':  records_out,
    }), 200
