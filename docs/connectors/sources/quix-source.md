# Quix Environment Source

A specialised [Kafka Source](kafka-source.md) that simplify copying data from a Quix environment.

## How To Use

To use a Quix Environment source, you need to create an instance of `QuixEnvironmentSource` and pass it to the `app.dataframe()` method.

```python
from quixstreams import Application
from quixstreams.sources.core.kafka import QuixEnvironmentSource

def main():
    app = Application()
    source = QuixEnvironmentSource(
      name="my-source",
      app_config=app.config,
      topic="source-topic",
      quix_sdk_token="quix-sdk-token",
      quix_workspace_id="quix-workspace-id",
    )
    
    sdf = app.dataframe(source=source)
    sdf.print(metadata=True)
    
    app.run()

if __name__ == "__main__":
    main()
```

## SDK Token

The Quix Environment Source requires the SDK token of the source environment. [Click here](https://quix.io/docs/develop/authentication/streaming-token.html) for more information on SDK tokens.
