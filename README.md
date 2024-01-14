# plex-sad-destroy
A Python project which searches for Movies and/or TV shows which should be reviewed for deletion.

## Development

`pulsar-client` does not support Python > 3.10

```shell
docker run -it --rm -v ${PWD}:/app -w /app python:3.10-slim bash
pip install --upgrade pip
pip install --upgrade plexapi pulsar-client pygogo 
pip freeze > requirements.txt
```

# Pulsar Messages

This application will process messages sent to the configured topic, it is expected that the message follows this JSON
format:

```json
{
  "plexKey": "value",
  "library": "Movies"
}
```
