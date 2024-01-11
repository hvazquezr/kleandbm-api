from confluent_kafka import Producer

from application.models.kleandbm import Project, ProjectCreate
from application.config import get_settings

class ProjectService:
    settings = get_settings()
    producer = Producer({'bootstrap.servers':settings.kafka_server})

    @staticmethod
    def kafka_produce(topic, key, value, use_local_producer=False):
        # Due to this celeri/kafka-python issue the producer has to be local
        # https://github.com/dpkp/kafka-python/issues/1098
        if use_local_producer:
            producer = Producer({'bootstrap.servers':ProjectService.settings.kafka_server})
            producer.produce(topic, key=key, value=value)
            producer.flush()
        else:
            ProjectService.producer.produce(topic, key=key, value=value)
            ProjectService.producer.flush()

    # TODO: Change the return type to Project and handle that in Celeri
    # This function cannot be async because it's not supported by celery
    @staticmethod
    def create_project(new_project: ProjectCreate):
        ProjectService.kafka_produce('project-updates', new_project.id, new_project.json(), use_local_producer=True)
        return ({'result': 'success'})