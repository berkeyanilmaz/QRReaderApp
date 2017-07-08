/**
 * Created by berkeyanilmaz on 2017-06-27.
 */
// Camera
session.service("ALVideoDevice").then(function(vid) {
  var theVideoDevice = vid;
  VideoUtils.unsubscribeAllHandlers(theVideoDevice, "pepper"+"_camera").then(function() {
    VideoUtils.startVideo(theVideoDevice, "videoBuffer",2, 10, 0)
    $('#loading_video').hide();
  });
});

session.subscribeToEvent("QRReader/CustomerInfo", function (value) {
    console.log("Raised Event: QRReader/CustomerInfo")
    var customer = JSON.parse(value)
    printCustomerInfo(customer);
});

function printCustomerInfo(value) {
    document.getElementById("customer_info").innerHTML = value.first_name + " " + value.last_name
}


var c=document.getElementById("borders");
var ctx=c.getContext("2d");
ctx.fillStyle="#00FF00";
ctx.fillRect(200,100,80,15);
ctx.fillRect(200,100,15,80);

ctx.fillRect(200,300,15,80);
ctx.fillRect(200,365,80,15);

ctx.fillRect(400,100,80,15);
ctx.fillRect(465,100,15,80);

ctx.fillRect(465,300,15,80);
ctx.fillRect(400,365,80,15);