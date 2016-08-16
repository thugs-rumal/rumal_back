from django.core.management.base import BaseCommand, CommandError
import pika
import logging

from django.core import serializers
from django.utils.encoding import smart_str

import pymongo
import gridfs
import time

from main.models import settings, Task
from main.utils import DownloadError, Encoder, is_text, STATUS_COMPLETED, STATUS_NEW, STATUS_PROCESSING, STATUS_FAILED,\
    NEW_SCAN_TASK, RPC_PORT, PRIVATE_QUEUE, PRIVATE_HOST, ANY_QUEUE

from bson import json_util
import json
import base64
import magic
import hexdump

import ConfigParser
import os
import threading
import ast


config = ConfigParser.ConfigParser()
config.read(os.path.join(settings.BASE_DIR, "conf", "backend.conf"))
BACKEND_HOST = config.get('backend', 'host', 'localhost')  # host of master backend where any queue is located
try:
    IS_BACKEND_MASTER = ast.literal_eval(config.get('backend', 'is_master', 'True'))  # master backend should define the any queue
except ValueError:
    IS_BACKEND_MASTER = True


logger = logging.getLogger(__name__)

client = pymongo.MongoClient()
db = client.thug
dbfs = client.thugfs
fs = gridfs.GridFS(dbfs)


class Command(BaseCommand):

    def on_request(self, ch, method, props, body):
        """
        Process message based upon task field when message received
        :param ch: channel
        :param method:
        :param props: properties
        :param body: message in queue
        :return:
        """
        body = json.loads(body)
        if int(body["task"]) == NEW_SCAN_TASK:  # new scan message
            body.pop("task")
            self.new_task(ch, method, props, body)

    def new_task(self, ch, method, props, body):
        """
        Processes new task message by writing it to DB and send response back (completed or failed)
        :param ch: channel
        :param method:
        :param props: callback queue
        :param body: message
        :return:
        """
        frontend_id = str(body['frontend_id'])
        logger.debug("Task received {}".format(frontend_id))

        #  Tasks are unique. If they want to be rerun frontend needs to send them again.
        [x.delete() for x in Task.objects.filter(frontend_id=frontend_id)]

        task_dict = [{"model": "main.task",
                      "fields": body
                      }]
        task_dict = json.dumps(task_dict)
        task_dict = smart_str(task_dict)
        obj = serializers.deserialize('json', task_dict).next()
        obj.save()

        logger.debug("Task saved {}".format(frontend_id))
        logger.info("Waiting for task to finish {}".format(frontend_id))

        # wait until scan is completed or failed.
        while (Task.objects.get(frontend_id=frontend_id).status is STATUS_PROCESSING) or \
                (Task.objects.get(frontend_id=frontend_id).status is STATUS_NEW):
            time.sleep(2)

        # Task completed or failed
        logger.debug("Task Completed {}".format(frontend_id))

        task = Task.objects.get(frontend_id=frontend_id)
        task_status = task.status

        if task_status == STATUS_COMPLETED:  # Successful scan
            result = db.analysiscombo.find({'frontend_id': frontend_id})
            files = self.generate_files(result[0])

            self.reply(ch, method, props, {"status": STATUS_COMPLETED,
                                           "data": result[0],
                                           "files": json_util.dumps(files)
                                           })

        if task_status == STATUS_FAILED:  # Failed scan
            self.reply(ch, method, props, {"status": STATUS_FAILED,
                                           "data": frontend_id
                                           })

        logger.debug("Response sent for task {}".format(frontend_id))

    def generate_files(self, analysis):
        data = []
        for x in analysis["locations"]:
            if x['content_id'] is not None:
                data.append({"content_id": x['content_id'],
                             "data": self.get_file(x['content_id'])
                             })

        for x in analysis["samples"]:
            data.append({"sample_id": x['sample_id'],
                         "data": self.get_file(x['sample_id'])
                         })

        for x in analysis["pcaps"]:
            if x['content_id'] is not None:
                data.append({"content_id": x["content_id"],
                             "data": self.get_file(x['content_id'])
                             })

        return data

    def get_file(self, file_id):
        try:
            download_file = base64.b64decode(fs.get(file_id).read())
        except:
            raise DownloadError

        hexdumped = False
        mime = magic.from_buffer(download_file, mime=True)
        if not is_text(mime):
            download_file = hexdump.hexdump(download_file, result='return')
            hexdumped = True

        # Ensure to use Unicode for the content, else JsonResopnse may fail
        if not isinstance(download_file, unicode):
            download_file = unicode(download_file, errors='ignore')

        return download_file

    def reply(self, ch, method, props, body):
        """
        Reply to callback queue with analysis result or failed status
        :param ch:
        :param method:
        :param props:
        :param body: message in reply
        :return:
        """

        ch.basic_publish(exchange='',
                         routing_key=props.reply_to,
                         properties=pika.BasicProperties(
                             correlation_id=props.correlation_id),
                         body=json.dumps(body, cls=Encoder))

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def create_connection(self, host, port, queue_name):
        """
        RabbitMQ connection to either remote or local any queue and local private queue (running in 2 separate threads )
        :param host: remote or local host
        :param port: port is 5672
        :param queue_name: any_queue or private_queue
        :return:
        """
        try:
            parameters = pika.ConnectionParameters(host=host,
                                                   port=port
                                                   )
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            if IS_BACKEND_MASTER or queue_name != ANY_QUEUE:
                #  create any queue for master or create private queue.
                channel.queue_declare(queue=queue_name)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(self.on_request, queue=queue_name)

            logger.debug(" [x] Awaiting RPC requests in {} on {}:{}".format(queue_name, host, port))
            channel.start_consuming()

        except DownloadError:
            logger.debug("Something went wrong when downloading files")

        except pika.exceptions.ConnectionClosed:
            logger.debug("Cannot connect to RabbitMQ")

        except KeyboardInterrupt:
            connection.close()

    def handle(self, *args, **options):
        """
            Starts 2 threads for any_queue(remote or local) and the private_queue
            They should be restarted in the case of exceptions
            :param args:
            :param options:
            :return:
            """
        any_queue = None
        private_queue = None

        # Starting both queues, restarts them if they die
        while True:

            if any_queue is None or not any_queue.isAlive():

                if any_queue is None:
                    logger.debug("Any queue is starting")
                else:
                    logger.debug("Any queue is restarting")

                any_queue = threading.Thread(
                    target=self.create_connection,
                    kwargs={'host': BACKEND_HOST,
                            'port': RPC_PORT,
                            'queue_name': ANY_QUEUE
                            }
                )

                any_queue.start()

            if private_queue is None or not private_queue.isAlive():

                if private_queue is None:
                    logger.debug("Private queue is starting")
                else:
                    logger.debug("Private queue is restarting")

                private_queue = threading.Thread(
                    target=self.create_connection,
                    kwargs={'host': PRIVATE_HOST,
                            'port': RPC_PORT,
                            'queue_name': PRIVATE_QUEUE})

                private_queue.start()

            time.sleep(10)
