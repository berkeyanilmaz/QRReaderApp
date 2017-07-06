/**
 * Created by berkeyanilmaz on 2017-06-27.
 */
// Camera
session.service("ALVideoDevice").then(function(vid) {
  var theVideoDevice = vid;
  VideoUtils.unsubscribeAllHandlers(theVideoDevice, "pepper"+"_camera").then(function() {
    VideoUtils.startVideo(theVideoDevice, "videoBuffer", 0, 10, 0)
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