export const environment = {
  production: true,
  // Relative URL: Angular is served behind nginx which proxies /api → Flask.
  // Override with BACKEND_URL at build time if needed:
  //   ng build --configuration production --define="import.meta.env.BACKEND_URL='/api'"
  apiUrl: '/api'
};
