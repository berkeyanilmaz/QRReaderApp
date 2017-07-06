#!/usr/bin/env python

import sys
import qi
import os
import json

from datetime import datetime
from customer_query import CustomerQuery
from kairos_face import enroll


class QRReader(object):
    subscriber_list = []
    loaded_topic = ""

    def __init__(self, application):
        # Get session
        self.application = application
        self.session = application.session
        self.service_name = self.__class__.__name__

        # Get logger -> stored in: /var/log/naoqi/servicemanager/{application id}.{service name}
        self.logger = qi.Logger(self.service_name)
        # Do initialization before the service is registered to NAOqi
        self.logger.info("Initializing...")

        # Autonomous Life
        self.life = self.session.service("ALAutonomousLife")
        self.customerInfo = CustomerQuery()

        # Memory
        self.memory = self.session.service("ALMemory")
        self.logger.info("Initializing - ALMemory")

        # Camera
        self.camera = self.session.service("ALPhotoCapture")
        self.logger.info("Initializing - ALPhotoCapture")

        # Preferences
        self.preferences = self.session.service("ALPreferenceManager")
        self.preferences.update()
        self.connect_to_preferences()
        self.logger.info("Initializing - ALPreferenceManager")

        # Face Detection
        self.face_detection = self.session.service("ALFaceDetection")
        self.face_detection.subscribe(self.service_name)
        self.logger.info("Initializing - ALFaceDetection")

        # Barcode Reader
        self.barcode_reader = self.session.service("ALBarcodeReader")
        self.logger.info("Initializing - ALBarcodeReader")

        # Create Signals
        self.create_signals()

        self.logger.info("Initialized!")


    @qi.nobind
    def connect_to_preferences(self):
        # connects to cloud preferences library and gets the initial prefs
        try:
            self.gallery_name = self.preferences.getValue('my_friend', "gallery_name")
            self.folder_path = self.preferences.getValue('my_friend', "folder_path")
            self.logger.info(self.folder_path)
            self.threshold = float(str(self.preferences.getValue('my_friend', "threshold")))

            self.logger.info(self.threshold)
            self.record_folder = self.preferences.getValue('my_friend', "record_folder")
            self.photo_count = int(self.preferences.getValue('my_friend', "photo_count"))
            self.resolution = int(self.preferences.getValue('my_friend', "resolution"))
            self.logger.info("Resolution: " + self.resolution)
            self.camera_id = int(self.preferences.getValue('my_friend', "camera_id"))
            self.picture_format = self.preferences.getValue('my_friend', "picture_format")
            self.file_name = self.preferences.getValue('my_friend', "file_name")
        except Exception, e:
            self.logger.info("failed to get preferences".format(e))
        self.logger.info("Successfully connected to preferences system")

    def create_signals(self):
        # Create events and subscribe them here
        self.logger.info("Creating events...")

        event_name = "BarcodeReader/BarcodeDetected"
        self.memory.declareEvent(event_name)
        event_subscriber = self.memory.subscriber(event_name)
        event_connection = event_subscriber.signal.connect(self.on_barcode_detected)
        self.subscriber_list.append([event_subscriber, event_connection])
        self.logger.info("Subscribed to event: " + event_name)

        event_name = "FaceDetected"
        event_subscriber = self.memory.subscriber(event_name)
        event_connection = event_subscriber.signal.connect(self.on_face_detected)
        self.subscriber_list.append([event_subscriber, event_connection])
        self.logger.info("Subscribed to event: " + event_name)

        self.logger.info("Subscribed to all events.")

    def disconnect_signals(self):
        self.logger.info("Deleting events...")
        for sub, i in self.subscriber_list:
            try:
                sub.signal.disconnect(i)
            except Exception, e:
                self.logger.info("Error unsubscribing: {}".format(e))
        self.logger.info("Unsubscribe done!")

    # Signal related methods end

    # ---------------------------

    # Event CallBacks Start

    def on_face_detected(self, value):
        if not self.face_detection:
            self.logger.info("Face detected. Take photo at  {}".format(str(datetime.now())))
            self.face_detected = True
            self.take_picture()
            self.face_detection.unsubscribe(self.service_name)

    def on_barcode_detected(self, value):
        self.logger.info("Barcode detected...")
        try:
            encoded_info = str(value[0][0]).replace(" ", "")
            self.logger.info("Information in QR: " + encoded_info)
            self.customerInfo.query_customer(value1=encoded_info, type1="U")
            # If any faulty customer information returns
            if self.customerInfo.name is not '':
                self.logger.info("Customer found! Query successful...")
            else:
                self.logger.info("Customer name is null")
        except Exception, e:
            self.logger.info("Error while querying customer: {}".format(e))

        customer = {"first_name": self.customerInfo.name, "last_name": self.customerInfo.last_name, "card_number": self.customerInfo.card_number,
                    "citizen_id": self.customerInfo.citizen_id, "gsm_number": self.customerInfo.gsm_number, "segment": self.customerInfo.segment,
                    "email_address": self.customerInfo.email_address, "customer_number": self.customerInfo.customer_number}

        event_name = "QRReader/CustomerInfo"
        self.memory.raiseEvent(event_name, json.dumps(customer))
        self.logger.info("Event raised: " + event_name)

        self.register_face(self.customerInfo.customer_number, self.file_name)

        # Redirect to next app
        next_app = str(self.memory.getData("Global/RedirectingApp"))
        try:
            self.logger.info("Switching to {}".format(next_app))
            self.life.switchFocus(next_app)
        except Exception, e:
            self.logger.info("Error while switching to next app: {} {}".format(next_app, e))

    # Event CallBacks End

    # -------------------

    # Initiation methods for services start

    @qi.nobind
    def show_screen(self):
        folder = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
        self.logger.info("Loading tablet page for app: {}".format(folder))
        try:
            ts = self.session.service("ALTabletService")
            ts.loadApplication(folder)
            ts.showWebview()

            self.logger.info("Tablet loaded.")
        except Exception, e:
            self.logger.error("Error starting tablet page{}".format(e))

    @qi.nobind
    def hide_screen(self):
        self.logger.info("Stopping tablet")
        try:
            ts = self.session.service("ALTabletService")
            ts.hideWebview()
            self.logger.info("Tablet stopped.")
        except Exception, e:
            self.logger.error("Error hiding tablet page{}".format(e))

    @qi.nobind
    def start_dialog(self):
        self.logger.info("Loading dialog")
        dialog = self.session.service("ALDialog")
        dir_path = os.path.dirname(os.path.realpath(__file__))
        topic_path = os.path.realpath(os.path.join(dir_path, "barcode_detected", "barcode_detected_enu.top"))
        self.logger.info("File is: {}".format(topic_path))
        try:
            self.loaded_topic = dialog.loadTopic(topic_path)
            dialog.activateTopic(self.loaded_topic)
            dialog.subscribe(self.service_name)
            self.logger.info("Dialog loaded!")
        except Exception, e:
            self.logger.info("Error while loading dialog: {}".format(e))

    @qi.nobind
    def stop_dialog(self):
        self.logger.info("Unloading dialog")
        try:
            dialog = self.session.service("ALDialog")
            dialog.unsubscribe(self.service_name)
            dialog.deactivateTopic(self.loaded_topic)
            dialog.unloadTopic(self.loaded_topic)
            self.logger.info("Dialog unloaded!")
        except Exception, e:
            self.logger.info("Error while unloading dialog: {}".format(e))

    # Initiation methods for services end

    # -----------------------------------

    # App Start/End Methods start

    @qi.nobind
    def start_app(self):
        # do something when the service starts
        self.logger.info("Starting app...")
        self.show_screen()
        self.start_dialog()
        self.logger.info("Started!")

    @qi.nobind
    def stop_app(self):
        # To be used if internal methods need to stop the service from inside.
        # external NAOqi scripts should use ALServiceManager.stopService if they need to stop it.
        self.logger.info("Stopping service...")
        self.application.stop()
        self.logger.info("Stopped!")

    @qi.nobind
    def cleanup(self):
        # called when your module is stopped
        self.logger.info("Cleaning...")

        self.disconnect_signals()
        self.stop_dialog()
        self.hide_screen()

        self.logger.info("Cleaned!")
        try:
            self.audio.stopMicrophonesRecording()
        except Exception, e:
            self.logger.info("Microphone already closed")

    # App Start / End methods end

    # ---------------------------

    # Kairos Starts

    @qi.nobind
    def take_picture(self):
        self.life.setAutonomousAbilityEnabled("BasicAwareness", False)

        self.camera.setResolution(self.resolution)
        self.camera.setCameraID(self.camera_id)
        self.camera.setPictureFormat(self.picture_format)
        self.camera.setHalfPressEnabled(True)
        self.camera.takePictures(self.photo_count, self.record_folder, self.file_name)

        self.life.setAutonomousAbilityEnabled("BasicAwareness", True)

    @qi.bind(methodName="registerFace", paramsType=(qi.String, qi.String,), returnType=qi.Bool)
    def register_face(self, customer_id, picture_name):
        try:
            file_path = self.get_picture_path(picture_name)
            self.logger.info("Photo send with file name: {} at {}".format(file_path, str(datetime.now())))
            response = enroll.enroll_face(subject_id=customer_id, gallery_name=self.gallery_name, file=file_path)
            self.logger.info(response)
            return True
        except Exception, e:
            self.logger.error(e)
            return False

    @qi.nobind
    def get_picture_path(self, picture_name):
        image_path = self.folder_path + picture_name
        return image_path


    # Kairos ends

if __name__ == "__main__":
    # with this you can run the script for tests on remote robots
    # run : python main.py --qi-url 123.123.123.123
    app = qi.Application(sys.argv)
    app.start()
    service_instance = QRReader(app)
    service_id = app.session.registerService(service_instance.service_name, service_instance)
    service_instance.start_app()
    app.run()
    service_instance.cleanup()
    app.session.unregisterService(service_id)

