from django.core.management.base import BaseCommand, CommandError
import pika
import logging
import thread
import json
import yaml

from django.core import serializers
from django.utils.encoding import smart_str

from main.models import *

RPC_HOST = '0.0.0.0'
RPC_PORT = 5672
RPC_QUEUE = 'rpc_queue'

logger = logging.getLogger(__name__)

class Command(BaseCommand):


    def on_request(self, ch, method, props, body):
        body = yaml.safe_load(body)
        print body
        logger.debug("Task received")
        dict = [{"model": "main.task",
          "fields" :
              body
        }]

        dict = (json.dumps(dict))
        list  = smart_str(dict)
        print list
        for obj in  serializers.deserialize('json', list):
            obj.save()
        logger.debug("Task saved")

        self.reply(ch, method, props, body)


    def reply(self, ch, method, props, body):
        ch.basic_publish(exchange='',
                         routing_key=props.reply_to,
                         properties=pika.BasicProperties(correlation_id= \
                                                             props.correlation_id),
                         body='test')

        ch.basic_ack(delivery_tag=method.delivery_tag)


    def handle(self, *args, **options):
        try:
            parameters = pika.ConnectionParameters(host=RPC_HOST, port=RPC_PORT)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=RPC_QUEUE)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(self.on_request, queue=RPC_QUEUE)
            logger.debug(" [x] Awaiting RPC requests")
            channel.start_consuming()
        except KeyboardInterrupt:
            connection.close()
