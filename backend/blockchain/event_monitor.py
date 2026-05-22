import threading
import time
import logging
from blockchain.adapters.service_log import service_log
from blockchain.adapters.warranty_tracker import warranty_tracker
from blockchain.adapters.vehicle_registry import vehicle_registry

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
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error in event monitoring loop: {e}")
                time.sleep(5)

    def _handle_service_submitted(self, event):
        with self.app.app_context():
            try:
                from db.models import db
                from db.repositories import vehicles as vehicle_repo, users as user_repo
                vin_hash = '0x' + event['args']['vin'].hex()
                mapping = vehicle_repo.find_by_vin_hash(vin_hash)
                if not mapping:
                    logger.warning(f"VIN mapping not found for hash: {vin_hash}")
                    return
                vehicle = vehicle_registry.get_vehicle(mapping.vin)
                owner = user_repo.find_by_blockchain_address(vehicle['owner'])
                if owner:
                    logger.info(f"Service submitted for VIN {mapping.vin} — notifying {owner.email}")
                    self._notify(owner.email, "New Service Pending Verification",
                                 f"A service has been submitted for your vehicle {mapping.vin}. Please review and verify.")
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
                    logger.info(f"Service verified for VIN {mapping.vin} — record index: {record_index}")
            except Exception as e:
                logger.error(f"Error handling ServiceVerified event: {e}")

    def _handle_service_disputed(self, event):
        with self.app.app_context():
            try:
                from db.repositories import vehicles as vehicle_repo
                vin_hash = '0x' + event['args']['vin'].hex()
                reason = event['args']['reason']
                mapping = vehicle_repo.find_by_vin_hash(vin_hash)
                if mapping:
                    logger.warning(f"Service DISPUTED for VIN {mapping.vin} — reason: {reason}")
            except Exception as e:
                logger.error(f"Error handling ServiceDisputed event: {e}")

    def _handle_claim_submitted(self, event):
        with self.app.app_context():
            try:
                from db.repositories import vehicles as vehicle_repo, users as user_repo
                vin_hash = '0x' + event['args']['vin'].hex()
                mapping = vehicle_repo.find_by_vin_hash(vin_hash)
                if mapping:
                    logger.info(f"Warranty claim submitted for VIN {mapping.vin}")
                    for manufacturer in user_repo.find_all_by_role('MANUFACTURER'):
                        self._notify(manufacturer.email, "New Warranty Claim",
                                     f"A warranty claim has been submitted for vehicle {mapping.vin}. Review required.")
            except Exception as e:
                logger.error(f"Error handling ClaimSubmitted event: {e}")

    @staticmethod
    def _notify(recipient_email: str, subject: str, message: str):
        logger.info(f"NOTIFICATION — To: {recipient_email} | {subject} | {message}")


_monitor_instance = None


def init_event_monitor(app):
    global _monitor_instance
    _monitor_instance = EventMonitor(app)
    _monitor_instance.start()
    return _monitor_instance
