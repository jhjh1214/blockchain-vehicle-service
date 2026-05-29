import { inject } from '@angular/core';
import { Router, CanActivateFn, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { AuthService } from '../services/auth';

function checkRole(
  route: ActivatedRouteSnapshot,
  auth: AuthService,
  router: Router
): boolean {
  const requiredRole = route.data['role'];
  if (!requiredRole) return true;
  const user = auth.currentUserValue;
  if (!user || user.role !== requiredRole) {
    if (user?.role === 'MANUFACTURER') router.navigate(['/manufacturer/dashboard']);
    else if (user?.role === 'SERVICE_CENTER') router.navigate(['/dealer/dashboard']);
    else router.navigate(['/login']);
    return false;
  }
  return true;
}

export const authGuard: CanActivateFn = (route, state) => {
  const router = inject(Router);
  const auth   = inject(AuthService);

  // Fast path: access token still valid
  if (auth.isAuthenticated()) {
    return checkRole(route, auth, router);
  }

  // Slow path: access token expired — try to silently refresh before giving up
  const hasRefresh = !!(
    sessionStorage.getItem('refresh_token') || localStorage.getItem('refresh_token')
  );

  if (!hasRefresh) {
    router.navigate(['/login'], { queryParams: { returnUrl: state.url } });
    return false;
  }

  return auth.refreshTokens().pipe(
    map(() => checkRole(route, auth, router)),
    catchError(() => {
      auth.logout();
      router.navigate(['/login'], { queryParams: { returnUrl: state.url } });
      return of(false);
    })
  );
};