import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth';

export const authGuard: CanActivateFn = (route, state) => {
  const router = inject(Router);
  const authService = inject(AuthService);

  if (!authService.isAuthenticated()) {
    router.navigate(['/login'], { queryParams: { returnUrl: state.url } });
    return false;
  }

  // Check role if route requires specific role
  const requiredRole = route.data['role'];
  if (requiredRole) {
    const currentUser = authService.currentUserValue;
    if (!currentUser || currentUser.role !== requiredRole) {
      // Redirect to correct dashboard based on actual role
      if (currentUser?.role === 'MANUFACTURER') {
        router.navigate(['/manufacturer/dashboard']);
      } else if (currentUser?.role === 'SERVICE_CENTER') {
        router.navigate(['/dealer/dashboard']);
      } else {
        router.navigate(['/login']);
      }
      return false;
    }
  }

  return true;
};