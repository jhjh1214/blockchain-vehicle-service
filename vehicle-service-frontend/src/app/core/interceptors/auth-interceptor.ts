import { HttpInterceptorFn, HttpErrorResponse, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth   = inject(AuthService);
  const router = inject(Router);

  const authedReq = addToken(req, auth.getToken());

  return next(authedReq).pipe(
    catchError((err: HttpErrorResponse) => {
      // On 401 from any endpoint except the auth endpoints themselves, try refresh
      const isAuthRoute = req.url.includes('/auth/login') ||
                          req.url.includes('/auth/register') ||
                          req.url.includes('/auth/refresh');

      if (err.status === 401 && !isAuthRoute) {
        return auth.refreshTokens().pipe(
          switchMap(r => next(addToken(req, r.access_token))),
          catchError(() => {
            auth.logout();
            router.navigate(['/login']);
            return throwError(() => err);
          })
        );
      }

      return throwError(() => err);
    })
  );
};

function addToken(req: HttpRequest<unknown>, token: string | null): HttpRequest<unknown> {
  if (!token) return req;
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}
