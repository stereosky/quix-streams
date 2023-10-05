import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import pytest
from confluent_kafka.admin import AdminClient, NewTopic, NewPartitions

from streamingdataframes.error_callbacks import (
    ConsumerErrorCallback,
    ProducerErrorCallback,
    ProcessingErrorCallback,
)
from streamingdataframes.kafka import (
    Partitioner,
    AutoOffsetReset,
    Consumer,
    Producer,
)
from streamingdataframes.models.rows import Row
from streamingdataframes.models.serializers import (
    JSONSerializer,
    JSONDeserializer,
)
from streamingdataframes.models.timestamps import (
    TimestampType,
    MessageTimestamp,
)
from streamingdataframes.models.topics import Topic
from streamingdataframes.rowconsumer import RowConsumer
from streamingdataframes.rowproducer import RowProducer
from streamingdataframes.runner import MessageProcessedCallback, Runner


@pytest.fixture()
def kafka_admin_client(kafka_container) -> AdminClient:
    return AdminClient({"bootstrap.servers": kafka_container.broker_address})


@pytest.fixture()
def random_consumer_group() -> str:
    return str(uuid.uuid4())


@pytest.fixture()
def consumer_factory(kafka_container, random_consumer_group):
    def factory(
        broker_address: str = kafka_container.broker_address,
        consumer_group: Optional[str] = None,
        auto_offset_reset: AutoOffsetReset = "latest",
        auto_commit_enable: bool = True,
        extra_config: dict = None,
    ) -> Consumer:
        consumer_group = consumer_group or random_consumer_group
        extra_config = extra_config or {}

        # Make consumers to refresh cluster metadata often
        # to react on re-assignment changes faster
        extra_config["topic.metadata.refresh.interval.ms"] = 3000

        return Consumer(
            broker_address=broker_address,
            consumer_group=consumer_group,
            auto_commit_enable=auto_commit_enable,
            auto_offset_reset=auto_offset_reset,
            extra_config=extra_config,
        )

    return factory


@pytest.fixture()
def consumer(consumer_factory) -> Consumer:
    return consumer_factory()


@pytest.fixture()
def producer_factory(kafka_container):
    def factory(
        broker_address: str = kafka_container.broker_address,
        extra_config: dict = None,
    ) -> Producer:
        extra_config = extra_config or {}

        return Producer(
            broker_address=broker_address,
            extra_config=extra_config,
        )

    return factory


@pytest.fixture()
def producer(producer_factory) -> Producer:
    return producer_factory()


@pytest.fixture()
def executor() -> ThreadPoolExecutor:
    executor = ThreadPoolExecutor(1)
    yield executor
    # Kill all the threads after leaving the test
    executor.shutdown(wait=False)


@pytest.fixture()
def topic_factory(kafka_admin_client):
    """
    For when you need to create a topic in Kafka.

    The factory will return the resulting topic name and partition count
    """

    def factory(
        topic: str = None, num_partitions: int = 1, timeout: float = 10.0
    ) -> (str, int):
        topic_name = topic or str(uuid.uuid4())
        futures = kafka_admin_client.create_topics(
            [NewTopic(topic=topic_name, num_partitions=num_partitions)]
        )
        futures[topic_name].result(timeout)
        return topic_name, num_partitions

    return factory


@pytest.fixture()
def topic_json_serdes_factory(topic_factory):
    """
    For when you need to create a topic in Kafka and want a `Topic` object afterward.
    Additionally, uses JSON serdes for message values by default.

    The factory will return the resulting Topic object.
    """

    def factory(topic: str = None, num_partitions: int = 1, timeout: float = 10.0):
        topic_name, _ = topic_factory(
            topic=topic, num_partitions=num_partitions, timeout=timeout
        )
        return Topic(
            topic_name,
            value_deserializer=JSONDeserializer(),
            value_serializer=JSONSerializer(),
        )

    return factory


@pytest.fixture()
def set_topic_partitions(kafka_admin_client):
    def func(
        topic: str = None, num_partitions: int = 1, timeout: float = 10.0
    ) -> (str, int):
        topic = topic or str(uuid.uuid4())
        futures = kafka_admin_client.create_partitions(
            [NewPartitions(topic=topic, new_total_count=num_partitions)]
        )
        futures[topic].result(timeout)
        return topic, num_partitions

    return func


@pytest.fixture()
def row_consumer_factory(kafka_container, random_consumer_group):
    def factory(
        broker_address: str = kafka_container.broker_address,
        consumer_group: Optional[str] = None,
        auto_offset_reset: AutoOffsetReset = "latest",
        auto_commit_enable: bool = True,
        extra_config: dict = None,
        on_error: Optional[ConsumerErrorCallback] = None,
    ) -> RowConsumer:
        extra_config = extra_config or {}
        consumer_group = consumer_group or random_consumer_group

        # Make consumers to refresh cluster metadata often
        # to react on re-assignment changes faster
        extra_config["topic.metadata.refresh.interval.ms"] = 3000
        return RowConsumer(
            broker_address=broker_address,
            consumer_group=consumer_group,
            auto_commit_enable=auto_commit_enable,
            auto_offset_reset=auto_offset_reset,
            extra_config=extra_config,
            on_error=on_error,
        )

    return factory


@pytest.fixture()
def row_producer_factory(kafka_container):
    def factory(
        broker_address: str = kafka_container.broker_address,
        partitioner: Partitioner = "murmur2",
        extra_config: dict = None,
        on_error: Optional[ProducerErrorCallback] = None,
    ) -> RowProducer:
        return RowProducer(
            broker_address=broker_address,
            partitioner=partitioner,
            extra_config=extra_config,
            on_error=on_error,
        )

    return factory


@pytest.fixture()
def row_factory():
    """
    This factory includes only the fields typically handed to a producer when
    producing a message; more generally, the fields you would likely
    need to validate upon producing/consuming.
    """

    def factory(value, topic="input-topic", key=b"key", headers=None) -> Row:
        headers = headers or {}
        return Row(
            key=key,
            value=value,
            headers=headers,
            topic=topic,
            partition=0,
            offset=0,
            size=0,
            timestamp=MessageTimestamp(0, TimestampType.TIMESTAMP_NOT_AVAILABLE),
        )

    return factory


@pytest.fixture()
def runner_factory(kafka_container, random_consumer_group):
    def factory(
        auto_offset_reset: AutoOffsetReset = "latest",
        consumer_extra_config: Optional[dict] = None,
        producer_extra_config: Optional[dict] = None,
        on_consumer_error: Optional[ConsumerErrorCallback] = None,
        on_producer_error: Optional[ProducerErrorCallback] = None,
        on_processing_error: Optional[ProcessingErrorCallback] = None,
        on_message_processed: Optional[MessageProcessedCallback] = None,
    ) -> Runner:
        return Runner(
            broker_address=kafka_container.broker_address,
            consumer_group=random_consumer_group,
            auto_offset_reset=auto_offset_reset,
            consumer_extra_config=consumer_extra_config,
            producer_extra_config=producer_extra_config,
            on_consumer_error=on_consumer_error,
            on_producer_error=on_producer_error,
            on_processing_error=on_processing_error,
            on_message_processed=on_message_processed,
        )

    return factory