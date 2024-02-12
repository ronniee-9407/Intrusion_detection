import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from 'src/services/auth.service';
import { NotificationService } from 'src/services/notification.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent implements OnInit {

  constructor(private router: Router, private authService: AuthService, private notificationService: NotificationService) { }

  ngOnInit() 
  {

  }

  login() 
  {
    let username = document.getElementById("UserID") as HTMLInputElement;
    let usernameValue = username.value;
    let password = document.getElementById("inputPassword") as HTMLInputElement;
    let passwordValue = password.value;
    this.authService.login(usernameValue, passwordValue).subscribe((data) => { 
      console.log("Is Login Success: " + data); 
      if(data) 
      {
        this.notificationService.showSuccess("Successfully Logged In", "Notification");
        this.router.navigate(['/dashboard']);
      }
      else this.notificationService.showError("ID and Password do not match!", "Notification");
    });
  }
}
