# AWS S3 Select Demo

[![The MIT License](https://img.shields.io/badge/license-MIT-orange.svg?style=flat-square)](LICENSE)

  This project showcases the rich `AWS S3 Select` feature to stream a large data file in a paginated style.
  
  Currently, `S3 Select` does not support `OFFSET` and hence we cannot paginate the results of the query. Hence, we use `scanrange` feature to stream the contents of the S3 file.

  <!-- You can find an in-depth article on this implementation [here](https://dev.to/idrisrampurawala/flask-boilerplate-structuring-flask-app-3kcd). -->

# Contributing
  We encourage you to contribute to Flask Boilerplate! Please check out the [Contributing](CONTRIBUTING.md) guidelines about how to proceed.

# Getting Started

### Prerequisites

- Python 3.9.2 or higher
- Up and running Redis client
- AWS account with an S3 bucket and an object
- `aws-cli` configured locally (having read access to S3)

:scroll: This project is a clone of one of my projects [Flask Boilerplate](https://github.com/idris-rampurawala/flask-boilerplate) to quickly get started on the topic :satisfied:

### Project setup
```sh
# clone the repo
$ git clone https://github.com/idris-rampurawala/s3-select-demo.git
# move to the project folder
$ cd s3-select-demo
```

### Creating virtual environment

- Install `pipenv` a global python project `pip install pipenv`
- Create a `virtual environment` for this project
```shell
# creating pipenv environment for python 3.9 (if you have multiple python versions, then check last command)
$ pipenv --three
# activating the pipenv environment
$ pipenv shell
# install all dependencies (include -d for installing dev dependencies)
$ pipenv install -d

# if you have multiple python 3 versions installed then
$ pipenv install -d --python 3.9
```
### Configuration

- There are 3 configurations `development`, `staging` and `production` in `config.py`. Default is `development`
- Create a `.env` file from `.env.example` and set appropriate environment variables before running the project

### Running app

- Run flask app `python run.py`
- Logs would be generated under `log` folder

### Running celery workers

- Run redis locally before running celery worker
- Celery worker can be started with following command
```sh
# run following command in a separate terminal
$ celery -A celery_worker.celery worker -l=info  
# (append `--pool=solo` for windows)
```

# Test
  Test if this app has been installed correctly and it is working via following curl commands (or use in Postman)
- Check if the app is running via `status` API
```shell
$ curl --location --request GET 'http://localhost:5000/status'
```
- Check if core app API and celery task is working via
```shell
$ curl --location --request GET 'http://localhost:5000/api/v1/core/test'
```
- Check if authorization is working via (change `API Key` as per you `.env`)
```shell
$ curl --location --request GET 'http://localhost:5000/api/v1/core/restricted' --header 'x-api-key: 436236939443955C11494D448451F'
```
- To test the file streaming task, please upload the `/data/data.csv` on your AWS S3 and then update the .env with its bucket, key and profile-name
```shell
$ curl --location --request GET 'http://localhost:5000/api/v1/core/s3_select'
```

# License
 This program is free software under MIT license. Please see the [LICENSE](LICENSE) file in our repository for the full text.