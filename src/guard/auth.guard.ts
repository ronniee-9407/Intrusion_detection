import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router, UrlTree } from '@angular/router';
import { Observable } from 'rxjs';
import { AuthService } from '../services/auth.service';

@Injectable({
   providedIn: 'root'
})
export class AuthGuard implements CanActivate {

  constructor(private authService: AuthService, private router: Router) {}

  canActivate(next: ActivatedRouteSnapshot, state: RouterStateSnapshot)
  {
    let url = state.url;
    return this.checkLogin(url);
  }

  checkLogin(url: string) 
  {
    let val = localStorage.getItem('isUserLoggedIn');

    if(val != null && val == "true")
    {
      if(url == "/login" || url == "/")
      {
        this.router.parseUrl('/dashboard');
        return;
      }
      else 
          return true;
    } 
    else 
    {
      return this.router.parseUrl('/login');
    }
  }
}