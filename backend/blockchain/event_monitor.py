import threading
import time
import logging
from blockchain.adapters.service_log import service_log
from blockchain.adapters.warranty_tracker import warranty_tracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventMonitor:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None

        self._service_submitted_filter = None
        self._service_verified_filter = None
        self._service_disputed_filter = None
        self._claim_submitted_filter = None

    def start(self):
        if self.running:
            logger.warning("Event monitor already running")
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Event monitor started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Event monitor stopped")

    def _monitor_loop(self):
        try:
            self._service_submitted_filter = service_log.contract.events.ServiceSubmitted.create_filter(fromBlock='latest')
            self._service_verified_filter = service_log.contract.events.ServiceVerified.create_filter(fromBlock='latest')
            self._service_disputed_filter = service_log.contract.events.ServiceDisputed.create_filter(fromBlock='latest')
            self._claim_submitted_filter = warranty_tracker.contract.events.ClaimSubmitted.create_filter(fromBlock='latest')
        except Exception as e:
            logger.error(f"Failed to create event filters: {e}")
            return

        logger.info("Event filters created, starting monitoring loop")

        while self.running:
            try:
                for event in self._service_submitted_filter.get_new_entries():
                    self._handle_service_submitted(event)
                for event in self._service_verified_filter.get_new_entries():
                    self._handle_service_verified(event)
                for event in self._service_disputed_filter.get_new_entries():
                    self._handle_service_disputed(event)
                for event in self._claim_submitted_filter.get_new_entries():
                    self._handle_claim_submitted(event)
                time.sleep(5)
            except Exception as e:
                msg = str(e)
                # Ganache restarted or filter expired — recreate silently
                if 'filter not found' in msg.lower() or (isinstance(e, dict) and 'filter not found' in e.get('message', '').lower()):
                    logger.info("Event filters expired (Ganache restarted?) — recreating")
                    self._recreate_filters()
                elif 'connection' in msg.lower() or 'refused' in msg.lower() or 'max retries' in msg.lower():
                    # Ganache is down — wait quietly, don't flood logs
                    time.sleep(10)
                else:
                    logger.error(f"Error in event monitoring loop: {e}")
                time.sleep(5)

    def _recreate_filters(self):
        try:
            self._service_submitted_filter = service_log.contract.events.ServiceSubmitted.create_filter(fromBlock='latest')
            self._service_verified_filter  = service_log.contract.events.ServiceVerified.create_filter(fromBlock='latest')
            self._service_disputed_filter  = service_log.contract.events.ServiceDisputed.create_filter(fromBlock='latest')
            self._claim_submitted_filter   = warranty_tracker.contract.events.ClaimSubmitted.create_filter(fromBlock='latest')
            logger.info("Event filters recreated")
        except Exception as e:
            logger.debug(f"Could not recreate filters (Ganache may be down): {e}")

    def _handle_service_submitted(self, event):
        with self.app.app_context():
            try:
                from db.repositories import vehicles as vehicle_repo, users as user_repo
                from core.notifications import notify_new_pending_service
                vin_hash = '0x' + event['args']['vin'].hex()
                mapping = vehicle_repo.find_by_vin_hash(vin_hash)
                if not mapping:
                    logger.warning(f"VIN mapping not found for hash: {vin_hash}")
                    return
                owner = user_repo.find_by_blockchain_address(mapping.owner_address)
                if owner:
                    logger.info(f"ServiceSubmitted on-chain for {mapping.vin} — FCM to owner {owner.email}")
                    notify_new_pending_service(owner.id, mapping.vin, 'Service Record')
            except Exception as e:
                logger.error(f"Error handling ServiceSubmitted event: {e}")

    def _handle_service_verified(self, event):
        with self.app.app_context():
            try:
                from db.repositories import vehicles as vehicle_repo
                vin_hash = '0x' + event['args']['vin'].hex()
                record_index = event['args']['recordIndex']
                mapping = vehicle_repo.find_by_vin_hash(vin_hash)
                if mapping:
                    logger.info(f"ServiceVerified on-chain for VIN {mapping.vin} record {record_index}")
            except Exception as e:
                logger.error(f"Error handling ServiceVerified event: {e}")

    def _handle_service_disputed(self, event):
        with self.app.app_context():
            try:
                from db.repositories import vehicles as vehicle_repo, users as user_repo
                from core.email import send_email
                vin_hash = '0x' + event['args']['vin'].hex()
                reason = event['args']['reason']
                mapping = vehicle_repo.find_by_vin_hash(vin_hash)
                if not mapping:
                    return
                logger.warning(f"ServiceDisputed on-chain for VIN {mapping.vin} — emailing manufacturers")
                for manufacturer in user_repo.find_all_by_role('MANUFACTURER'):
                    send_email(
                        manufacturer.email,
                        f'Service Dispute Filed — {mapping.vin}',
                        (
                            f'A service record for vehicle {mapping.vin} has been disputed by the owner.\n\n'
                            f'Reason: {reason}\n\n'
                            f'Log in to VehicleChain to review the dispute and take action.'
                        ),
                    )
            except Exception as e:
                logger.error(f"Error handling ServiceDisputed event: {e}")

    def _handle_claim_submitted(self, event):
        with self.app.app_context():
            try:
                from db.repositories import vehicles as vehicle_repo, users as user_repo
                from core.email import send_email
                vin_hash = '0x' + event['args']['vin'].hex()
                mapping = vehicle_repo.find_by_vin_hash(vin_hash)
                if not mapping:
                    return
                logger.info(f"ClaimSubmitted on-chain for VIN {mapping.vin} — emailing manufacturers")
                for manufacturer in user_repo.find_all_by_role('MANUFACTURER'):
                    send_email(
                        manufacturer.email,
                        f'New Warranty Claim — {mapping.vin}',
                        (
                            f'A warranty claim has been submitted for vehicle {mapping.vin}.\n\n'
                            f'Log in to VehicleChain to review and process the claim.'
                        ),
                    )
            except Exception as e:
                logger.error(f"Error handling ClaimSubmitted event: {e}")


_monitor_instance = None


def init_event_monitor(app):
    global _monitor_instance
    _monitor_instance = EventMonitor(app)
    _monitor_instance.start()
    return _monitor_instance
