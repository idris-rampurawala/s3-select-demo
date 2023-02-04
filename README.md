# AWS S3 Select Demo

[![The MIT License](https://img.shields.io/badge/license-MIT-orange.svg?style=flat-square)](LICENSE)

  This project showcases the rich `AWS S3 Select` feature to stream a large data file in a `paginated style`.
  
  Currently, `S3 Select` does not support `OFFSET` and hence we cannot paginate the results of the query. Hence, we use `scanrange` feature to stream the contents of the S3 file.


# Background
Importing (reading) a large file leads `Out of Memory` error. It can also lead to a system crash event. There are libraries viz. Pandas, Dask, etc. which are very good at processing large files but again the file is to be present locally i.e. we will have to import it from S3 to our local machine. But what if we do not want to fetch and store the whole S3 file locally at once? :thinking:

Well, we can make use of `AWS S3 Select` to stream a large file via it's `ScanRange` parameter. This approach is similar to how a pginated API works. Instead of limit and offset on records, we provide the limit and offset on the `bytes to stream`. `S3 Select` is intelligent enough to skip the whole row of the file if it does not fit in the byte range.

You can find an in-depth article on this implementation [here](https://dev.to/idrisrampurawala/efficiently-streaming-a-large-aws-s3-file-via-s3-select-4on).

# Getting Started

### Prerequisites

- Python 3.9.13 or higher
- Up and running Redis client
- AWS account with an S3 bucket and an object (or upload from `/data/data.csv`)
- `aws-cli` configured locally (having read access to S3)

:scroll: This project is a clone of one of my projects [Flask Boilerplate](https://github.com/idris-rampurawala/flask-boilerplate) to quickly get started on the topic :satisfied:

### Project setup
```sh
# clone the repo
$ git clone https://github.com/idris-rampurawala/s3-select-demo.git
# move to the project folder
$ cd s3-select-demo
```
If you want to install redis via docker
```sh
# at the root of this project 
$ docker run -d --name="flask-boilerplate-redis" -p 6379:6379 redis
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
$ celery -A celery_worker.celery worker -l INFO
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
- To test the file parallel processing task, please upload the `/data/data.csv` on your AWS S3 and then update the .env with its bucket, key and profile-name
```shell
$ curl --location --request GET 'http://localhost:5000/api/v1/core/s3_select_parallel'
```

# Resouces
- [My post explaining this approach](https://dev.to/idrisrampurawala/efficiently-streaming-a-large-aws-s3-file-via-s3-select-4o)
- [AWS S3 Select userguide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/selecting-content-from-objects.html)
- [AWS S3 Select Example](https://aws.amazon.com/blogs/aws/s3-glacier-select/)
- [AWS S3 Select boto3 reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.select_object_content)

# License
 This program is free software under MIT license. Please see the [LICENSE](LICENSE) file in our repository for the full text.