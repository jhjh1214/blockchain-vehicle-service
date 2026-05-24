class ApiEndpoints {
  // Auth
  static const login = '/auth/login';
  static const register = '/auth/register';
  static const logout = '/auth/logout';
  static const me = '/auth/me';
  static const profile = '/auth/profile';
  static const changePassword = '/auth/change-password';

  // Vehicles
  static const myVehicles = '/vehicles/owner/vehicles';
  static const claimVehicle = '/vehicles/claim';
  static const transferVehicle = '/vehicles/transfer';
  static String vehicleDetail(String vin) => '/vehicles/$vin';
  static String warrantyCheck(String vin) => '/warranties/check/$vin';

  // Services
  static const ownerPendingServices = '/services/owner/pending';
  static const ownerVerifyService = '/services/owner/verify';
  static const ownerDisputeService = '/services/owner/dispute';
  static const ownerServiceHistory = '/services/owner/history';

  // Warranties
  static const submitClaim = '/warranties/submit-claim';
  static const ownerClaims = '/warranties/owner/claims';
  static String vehicleClaims(String vin) => '/warranties/claims/$vin';
}
