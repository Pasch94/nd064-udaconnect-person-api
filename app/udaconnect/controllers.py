import grpc
import json
import os

from datetime import datetime

from app.udaconnect.models import Person
from app.udaconnect.schemas import (
    PersonSchema,
)
from app.udaconnect.proto.person_pb2 import PersonRequest, PersonListRequest
from app.udaconnect.proto.person_pb2_grpc import PersonServiceStub
from flask import request, Response
from flask_accepts import accepts, responds
from flask_restx import Namespace, Resource
from typing import Optional, List
from kafka import KafkaProducer

DATE_FORMAT = "%Y-%m-%d"

api = Namespace("UdaConnect", description="Connections via geolocation.")  # noqa

TOPIC_NAME = os.getenv('KAFKA_PERSON_TOPIC', 'person')
KAFKA_HOST = os.getenv('KAFKA_HOST', '192.168.65.4')
KAFKA_PORT = os.getenv('KAFKA_PORT', '9092')
KAFKA_SERVER = ':'.join([KAFKA_HOST, KAFKA_PORT])
kafka_producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVER,
        api_version=(2, 8, 0),
        client_id=__name__,
        value_serializer=lambda m: json.dumps(m).encode('utf-8'))

GRPC_PORT = os.getenv('GRPC_PERSON_PORT', '6005')
GRPC_HOST = os.getenv('GRPC_PERSON_HOST', 'localhost')

print(':'.join([GRPC_HOST, GRPC_PORT]))
GRPC_CHANNEL = grpc.insecure_channel(':'.join([GRPC_HOST, GRPC_PORT]), options=(('grpc.enable_http_proxy', 0),))
grpc_stub = PersonServiceStub(GRPC_CHANNEL)


@api.route("/persons")
class PersonsResource(Resource):
    @accepts(schema=PersonSchema)
    @responds(schema=PersonSchema)
    def post(self) -> Person:
        kafka_data = request.get_json()
        kafka_producer.send(TOPIC_NAME, kafka_data)
        return Response(status=202) 

    @responds(schema=PersonSchema, many=True)
    def get(self) -> List[Person]:
        person_list = grpc_stub.GetAll(PersonListRequest())
        return person_list.persons 


@api.route("/persons/<person_id>")
@api.param("person_id", "Unique ID for a given Person", _in="query")
class PersonResource(Resource):
    @responds(schema=PersonSchema)
    def get(self, person_id) -> Person:
        person = grpc_stub.Get(PersonRequest(id=int(person_id)))
        return person


