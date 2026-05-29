class ApiEndpoints {
  // Auth
  static const login = '/auth/login';
  static const register = '/auth/register';
  static const logout = '/auth/logout';
  static const me = '/auth/me';
  static const profile = '/auth/profile';
  static const changePassword = '/auth/change-password';
  static const deviceToken = '/auth/device-token';

  // Vehicles
  static const myVehicles = '/vehicle/owner/vehicles';
  static const claimVehicle = '/vehicle/claim';
  static const transferVehicle = '/vehicle/transfer';
  static String vehicleDetail(String vin) => '/vehicle/$vin';
  static String warrantyCheck(String vin) => '/warranty/check/$vin';
  static String warrantyEligibilityCheck(String vin) => '/warranty/check-eligibility/$vin';

  // Services
  static const ownerPendingServices = '/service/owner/pending';
  static const ownerVerifyService = '/service/owner/verify';
  static const ownerDisputeService = '/service/owner/dispute';
  static const ownerServiceHistory = '/service/owner/history';

  // Warranties
  static const submitClaim = '/warranty/submit-claim';
  static const ownerClaims = '/warranty/owner/claims';
  static String vehicleClaims(String vin) => '/warranty/claims/$vin';

  // Export
  static String vehicleExport(String vin) => '/vehicle/export/$vin';
}
