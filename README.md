# Url Shortener Task

We need to build two applications in Python:
- an URL shortening API (similar to bit.ly, tinyurl etc.)
- CLI for management (adding, updating, deleting) 

## CLI

The user should be able to input an URL using CLI with some command, eg.

```
> add [url]
```

After invoking add command from CLI user should get the short url which might be similar to: `http://localhost:9000/XYZ123` 

**The path component should have at most SHORT_URL_MAX_LEN characters. This value should be configurable.**

Once we run add command, when a URL is created.

Submitting a URL that was already processed should not result in creating a new short URL, we should simply use an existing entry.

## API

After the short URL is obtained, visiting `http://localhost:9000/XYZ123` should result in a redirect to the original URL that was shortened.

We also need to allow checking what the short URL points to instead of redirecting immediately. This is done by prepending the shortened URL's path
component with a ! character. For example, if I'm given a shortened url `http://localhost:9000/XYZ` I need to be able to go to `http://localhost:9000/!XYZ` and view:
the real URL with a clickable link pointing to the destination.

## Additional instructions

Prepare instruction in HOWTO.md on how to run database and applications

If you have any questions, please sumbit a new issue in your repository and assign someone form our team to it.

## Use:
- Python
- redis or mongodb
- preferably docker/docker-compose
