import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class BackendService {

  constructor(private http: HttpClient) { }

  sendSpotArray(spotArray)
  {
    console.log(spotArray)
    return this.http.post("http://localhost:4000/saveROI",{"spotArray": spotArray});
  }

  searchDateTime(query)
  {
    return this.http.post("http://localhost:4000/searchDateTime",{"query": query});
  }

  sendImageID(dateTime, imageID)
  {
    return this.http.post("http://localhost:4000/showImg",{"dateTime": dateTime, "imageID": imageID});
  }

  loadDefault()
  {
    return this.http.get("http://localhost:4000/defaultROI");
  }
}
