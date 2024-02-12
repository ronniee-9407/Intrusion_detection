import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { NotificationService } from 'src/services/notification.service';
import { AuthService } from 'src/services/auth.service';
import {fabric} from 'fabric';
import Litepicker from 'litepicker';
import {webSocket} from 'rxjs/webSocket'; 
import { DomSanitizer } from '@angular/platform-browser';
import { Chart, registerables } from 'chart.js';
import * as pdfMake from 'pdfmake/build/pdfmake.js';
import * as pdfFonts from 'pdfmake/build/vfs_fonts.js';
import { BackendService } from 'src/services/backend.service';
pdfMake.vfs = pdfFonts.pdfMake.vfs;

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  views = ["Live", "ROI", "ReportHome", "ReportData", "ShowImage"];
  currView = this.views[0];
  initializeOnceROI = true;
  canvasWrapperROI;
  canvasROI;
  once = false;
  spotsROI = 0;
  startDate;
  endDate;
  startTime = "00:00";
  endTime = "23:59";
  picker;
  error = false;
  dataFromDB = [];
  dtOptions: any = {};
  deleteDisplay = false;
  arr_spot_roi = [];
  subscribed_video;
  cam_status = 0;
  imageID;
  db_status = 0;
  num_intrusion;
  snap_time;
  liveViewArrayTable = [];
  canvasScalingWidthROI;
  canvasScalingHeightROI;
  selectedDateTime;
  selectedID;
  imageDatatable;
  chart;
  videoAvailable = false;
  tableDataAvailable = false;
  modal = false;
  demoVidToggled = false;
  demo_video;
  demo_socket;
  dataStatus: boolean = false
  storage_status: boolean = false
  // storage_full_status: boolean=false

  constructor(private service: BackendService, private sanitizer: DomSanitizer, private router: Router, private notifyService: NotificationService,  private authService: AuthService) { 
    Chart.register(...registerables);
  }

  ngOnInit() 
  {
    this.socket_feed();
  }
  
  socket_feed()
  {
    let ipVideo1 = "ws://127.0.0.1:4000/intrusionVideo";
    let socketVideo1 = webSocket(ipVideo1);
    let videoFeed1 = socketVideo1.subscribe((data) => {
      let objectURL1 = 'data:image/jpg;base64,' + data['encoded_img'];   
      this.subscribed_video = this.sanitizer.bypassSecurityTrustUrl(objectURL1);
      this.videoAvailable = true;
      this.cam_status = data['cam_status'];
      this.imageID = data['image_id'];
      this.num_intrusion = data['num_intrusion'];
      this.snap_time = data['snap_time'];
      this.storage_status = data['storage_status']
      if(this.storage_status)
      {
        this.notifyService.showWarning('Storage is Full','Notification')
      }
      if(this.liveViewArrayTable.length != 0)
        this.tableDataAvailable = true;

      if(this.num_intrusion != 0)
      {
        if(this.liveViewArrayTable.length >= 15)
        {
          this.liveViewArrayTable.shift();
          this.liveViewArrayTable.push([this.snap_time, this.num_intrusion, this.imageID]);
        }
        else
        {
          this.liveViewArrayTable.push([this.snap_time, this.num_intrusion, this.imageID]);
        }
      }
    });

    let ipVideo2 = "ws://127.0.0.1:4000/dbStatus";
    let socketVideo2 = webSocket(ipVideo2);
    let videoFeed2 = socketVideo2.subscribe((data) => {
      this.db_status = data['db_status'];
    });
  }
  
  // Function for introducing delay in ms
  delay(delayInms) {
    return new Promise(resolve => {
      setTimeout(() => {
        resolve(2);
      }, delayInms);
    });
  }

  live()
  {
    this.currView = this.views[0];
  }

  async ROI()
  {
    this.currView = this.views[1];
    await this.delay(100);
    if(this.initializeOnceROI)
    {
      this.canvasWrapperROI = document.getElementById('canvas-wrapper-roi')
      this.canvasROI = new fabric.Canvas('canvas-roi', { selection: false, width: this.canvasWrapperROI.clientWidth, height: this.canvasWrapperROI.clientHeight});
      this.initializeOnceROI = false;
    }
  }

  reportAnalysis()
  {
    this.currView = this.views[2];
    this.modal = false;
    setTimeout(() => this.initializingDatePicker(), 0);
  }

  logout()
  {
    this.notifyService.showInfo("Logged Out!", "Notification");
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  initializingDatePicker()
  {
    this.picker = new Litepicker({ 
      element: document.getElementById('start-date'),
      elementEnd: document.getElementById('end-date'),
      singleMode: false,
      allowRepick: true,
      dropdowns: {"minYear":2020,"maxYear":null,"months":true,"years":true}
    });
  }

  async searchDateTime()
  {
    let tempStartDate = document.getElementById("start-date") as HTMLInputElement;
    let tempEndDate = document.getElementById("end-date") as HTMLInputElement;
    let tempStartTime = document.getElementById("start-time") as HTMLInputElement;
    let tempEndTime = document.getElementById("end-time") as HTMLInputElement;
    this.startDate = tempStartDate.value;
    this.endDate = tempEndDate.value;
    this.startTime = tempStartTime.value;
    this.endTime = tempEndTime.value;
    if(this.startDate == "" && this.endDate == "")
    {
      this.notifyService.showInfo("Select Date First!", "Notification");
      return;
    }

    let query = [this.startDate, this.endDate, this.startTime, this.endTime];
    this.service.searchDateTime(query).subscribe((data: Array<any>) => {
      this.dataFromDB = data['DBtimedata'];
      this.dataStatus = data['num_data_status']
    });


    await this.delay(1000);


    if(this.dataFromDB.length == 0)
      this.error = true;
    else
      this.error = false;

    this.currView = this.views[3];
    this.dtOptions = {
      pagingType: 'full_numbers',
      pageLength: 6,
      dom: 'Bfrtip', 
      buttons: [{extend: 'excel', text: 'Excel', title: 'Intrusion Detection', exportOptions: {columns: [ 0, 1, 2, 3]}}, {extend: 'pdfHtml5', orientation: 'portrait', pageSize: 'LEGAL', exportOptions: {columns: [ 0, 1, 2, 3]}}]    
    };
    if(this.dataStatus)
    {
      setTimeout(function(){
        this.notifyService.showInfo('Loading Graph for 150,000 data','Notification')
        this.notifyService.showWarning('Data limit exceeded','Notification')
      },10000)
    }
    await this.delay(100);
    this.drawGraph();
  }

  drawSpotROI()
  {
    this.canvasROIWindowScaling();
    this.once = true; // on one click of button only one spot can be drawn
    let _this = this;
    let json;
    //removing resize for spots
    let HideControls = {
      'tl':false,
      'tr':false,
      'bl':false,
      'br':false,
      'ml':false,
      'mt':false,
      'mr':false,
      'mb':false,
      'mtr':false //removing rotating feature
    };

    let Name = 's'+(++this.spotsROI).toString();
    let spot, isDown, origX, origY;
    // removeEvents();
    // changeObjectSelection(false);
    // enableSelection();

    //when holding mouse down
    this.canvasROI.on('mouse:down', function(o) 
    {
      if(!_this.once) return
      
      isDown = true;
      let pointer = _this.canvasROI.getPointer(o.e);
      origX = pointer.x;
      origY = pointer.y;
      pointer = _this.canvasROI.getPointer(o.e);
      spot = new fabric.Rect({
        left: origX,
        top: origY,
        originX: 'left',
        originY: 'top',
        width: 3,
        height: 3,
        angle: 0,
        rx: 10,
        ry: 10,
        selectable:false,
        fill: '#51EF23',
        stroke: '#51EF23',
        transparentCorners: false,
        strokeUniform: true
      });
    });
  
    this.canvasROI.on('mouse:up', function(o) 
    {
      if(!_this.once) return

      isDown = false;
      spot.setCoords();

      let text = new fabric.Text(Name,{
        left:spot.left,
        top:spot.top,
        fontSize: 16,
        fill: '#FFFFFF',
        lockScalingFlip: true
      });

      let group = new fabric.Group([spot,text],{
        id: Name
      });

      _this.canvasROI.remove(spot);
      _this.canvasROI.add(group);
      group.setControlsVisibility(HideControls);
      group.addWithUpdate();
      group.lockMovementX = true;
      group.lockMovementY = true;
      // enableSelection();
      group.on('selected', function() {
        //triggers delete button rendering
        _this.deleteDisplay = true;
      });

      group.on('deselected', function() {
        //triggers delete button rendering
        _this.deleteDisplay = false;
      });

      _this.canvasROI.off('mouse:down').off('mouse:move').off('mouse:up');
      json = _this.canvasROI.toJSON();
      
      _this.arr_spot_roi.push([Math.round(json.objects[json.objects.length-1].left * _this.canvasScalingWidthROI), Math.round(json.objects[json.objects.length-1].top  * _this.canvasScalingHeightROI)]);
      _this.once = false;
    });
  }

  removeSpot()
  {
    this.arr_spot_roi.splice(((parseInt(this.canvasROI.getActiveObject().id.substring(1))) - 1), 1);
    this.canvasROI.remove(this.canvasROI.getActiveObject());
    this.rearrangeSpots();
    this.spotsROI--;
  }

  clearROI()
  {
    this.canvasROI.clear();
    this.arr_spot_roi.length = 0;
    this.spotsROI = 0;
    this.service.sendSpotArray([[1, 2], [2, 2], [2, 3], [1, 3]]).subscribe();
  }

  rearrangeSpots()
  {
    let canvasROIObjects = this.canvasROI.getObjects();
    for(let i = 0; i < canvasROIObjects.length; i++)
    {
      canvasROIObjects[i].id = 's' + (i + 1);
      canvasROIObjects[i]._objects[1].set({ text: 's' + (i + 1)});
    }
  }

  loadDefault()
  {
    this.service.loadDefault().subscribe();
    this.notifyService.showSuccess("Default ROI loaded !", "Notification");
  }

  save()
  { 
    if(this.arr_spot_roi.length == 0)
      this.service.sendSpotArray([[1, 2], [2, 2], [2, 3], [1, 3]]).subscribe();
    else
      this.service.sendSpotArray(this.arr_spot_roi).subscribe();
    this.notifyService.showSuccess("Saved!", "Notification");
  }

  canvasROIWindowScaling()
  {
    const canvasROI = document.getElementById('canvas-wrapper-roi');
    let canvasWidth = canvasROI.offsetWidth;
    let canvasHeight = canvasROI.offsetHeight;

    this.canvasScalingWidthROI = 640/canvasWidth;
    this.canvasScalingHeightROI = 480/canvasHeight;
  }

  clickRow(dateTime, id)
  {
    this.service.sendImageID(dateTime, id).subscribe((data) => {
      let objectURL1 = 'data:image/jpg;base64,' + data;   
      this.imageDatatable  = this.sanitizer.bypassSecurityTrustUrl(objectURL1);
    });
    this.selectedDateTime = dateTime;
    this.selectedID = id;
    this.modal = true;
  }

  backFromModal()
  {
    this.modal = false;
    this.error = false
  }

  async dataTablePage()
  {
    this.currView = this.views[3];
    this.searchDateTime();
    await this.delay(100);
    this.drawGraph();
  }

  drawGraph()
  {
    let dataX = [];
    let dataY = [];
    
    for(let i = 0; i < this.dataFromDB.length; i++)
    {
      dataX.push(this.dataFromDB[i][0]);
      dataY.push(this.dataFromDB[i][3]);
    }
    
    
    this.chart = new Chart('chart', {
      type: 'bar',
      data: {
        labels: dataX,
        datasets: [{
          borderColor: "#bae755",
          backgroundColor: "#e755ba",
          data: dataY
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: {
            title: {
              display: true,
              text: '',
              padding: {
                bottom: 10
              },
              font: {
                size: 18,
                family: 'SF Pro Display'
              }
            }
          },
          x: {
            title: {
              display: true,
              text: '',
              align: 'center',
              padding: {
                top: 10
              },
              font: {
                size: 18,
                family: 'SF Pro Display'
              }
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          title: {
            display: true,
            text: '',
            padding: {
              bottom: 10
            },
            font: {
              size: 18,
              family: 'SF Pro Display'
            }
          },
        },
      }
    });
  }

  toggleRunDemoVidOn()
  {
    this.demoVidToggled = true;
    this.runDemoVid();
  }

  toggleRunDemoVidOff()
  {
    this.demoVidToggled = false;
    this.demo_socket.complete();
  }
 
  runDemoVid()
  {
    let ipVideo1 = "ws://127.0.0.1:4000/roiDemoVideo";
    this.demo_socket = webSocket(ipVideo1);
    let videoFeed1 = this.demo_socket.subscribe((data) => {
      let objectURL1 = 'data:image/jpg;base64,' + data['encoded_imgg'];   
      this.demo_video = this.sanitizer.bypassSecurityTrustUrl(objectURL1);
    });
  }
}

