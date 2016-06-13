from django.core.management.base import BaseCommand, CommandError
import pika
import logging
import thread
import json
from bson.objectid import ObjectId
import yaml

from django.core import serializers
from django.utils.encoding import smart_str

import pymongo
import time

from main.models import *
from main.utils import *

RPC_HOST = '0.0.0.0'
RPC_PORT = 5672
RPC_QUEUE = 'rpc_queue'

NEW_SCAN_TASK = 1

STATUS_NEW = 0
STATUS_PROCESSING = 1
STATUS_FAILED = 2
STATUS_COMPLETED = 3

logger = logging.getLogger(__name__)

client = pymongo.MongoClient()
db = client.thug


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
        body = yaml.safe_load(body)
        if int(body["task"]) == NEW_SCAN_TASK:  # new scan message
            body.pop("task")
            self.new_task(ch, method, props, body)

    def new_task(self, ch, method, props, body):
        """
        Process post new task received
        :param ch:
        :param method:
        :param props:
        :param body:
        :return:
        """
        frontend_id = str(body['frontend_id'])
        logger.debug("Task received {}".format(frontend_id))
        task_dict = [{"model": "main.task",
                      "fields": body
                      }]
        task_dict = json.dumps(task_dict)
        task_dict = smart_str(task_dict)
        for obj in serializers.deserialize('json', task_dict):
            obj.save()
        logger.debug("Task saved {}".format(frontend_id))
        logger.info("Waiting for task to finish {}".format(frontend_id))

        # wait until scan is completed or failed.
        while (Task.objects.get(frontend_id=frontend_id).status is STATUS_PROCESSING) or \
                (Task.objects.get(frontend_id=frontend_id).status is STATUS_NEW):
            time.sleep(2)

        logger.debug("Task Completed {}".format(frontend_id))
        task = Task.objects.get(frontend_id=frontend_id)
        task_status = task.status
        if task_status == STATUS_COMPLETED:  # Successful scan
            result = db.analysiscombo.find({'frontend_id': frontend_id})
            self.reply(ch, method, props, {"status": STATUS_COMPLETED,
                                           "data": result[0]
                                           })
        if task_status == STATUS_FAILED:  # Failed scan
            self.reply(ch, method, props, {"status": STATUS_FAILED,
                                           "data": frontend_id
                                           })
        logger.debug("Response sent for task {}".format(frontend_id))

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

    def handle(self, *args, **options):
        """
        Main function to create connection to queue and qit for messages.
        on_request: un when message is received
        :param args:
        :param options:
        :return:
        """
        try:
            parameters = pika.ConnectionParameters(host=RPC_HOST, port=RPC_PORT)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=RPC_QUEUE)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(self.on_request, queue=RPC_QUEUE)
            logger.debug(" [x] Awaiting RPC requests")
            channel.start_consuming()
        except pika.exceptions.ConnectionClosed:
            logger.debug("Cannot connect to RabbitMQ")
        except KeyboardInterrupt:
            connection.close()
