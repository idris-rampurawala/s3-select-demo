import ast

import boto3
from botocore.exceptions import ClientError
from flask import current_app
from werkzeug.local import LocalProxy

logger = LocalProxy(lambda: current_app.logger)


def get_s3_file_size(bucket: str, key: str) -> int:
    """Gets the file size of S3 object by a HEAD request

    Args:
        bucket (str): S3 bucket
        key (str): S3 object path

    Returns:
        int: File size in bytes. Defaults to 0 if any error.
    """
    aws_profile = current_app.config.get('AWS_PROFILE_NAME')
    s3_client = boto3.session.Session(profile_name=aws_profile).client('s3')
    file_size = 0
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        if response:
            file_size = int(response.get('ResponseMetadata').get('HTTPHeaders').get('content-length'))
    except ClientError:
        logger.exception(f'Client error reading S3 file {bucket} : {key}')
    return file_size


def stream_s3_file(bucket: str, key: str, file_size: int, chunk_bytes=5000) -> tuple[dict]:
    """Streams a S3 file via a generator.

    Args:
        bucket (str): S3 bucket
        key (str): S3 object path
        chunk_bytes (int): Chunk size in bytes. Defaults to 5000
    Returns:
        tuple[dict]: Returns a tuple of dictionary containing rows of file content
    """
    aws_profile = current_app.config.get('AWS_PROFILE_NAME')
    s3_client = boto3.session.Session(profile_name=aws_profile).client('s3')
    expression = 'SELECT * FROM S3Object'
    start_range = 0
    end_range = min(chunk_bytes, file_size)
    while start_range < file_size:
        response = s3_client.select_object_content(
            Bucket=bucket,
            Key=key,
            ExpressionType='SQL',
            Expression=expression,
            InputSerialization={
                'CSV': {
                    'FileHeaderInfo': 'USE',
                    'FieldDelimiter': ',',
                    'RecordDelimiter': '\n'
                }
            },
            OutputSerialization={
                'JSON': {
                    'RecordDelimiter': ','
                }
            },
            ScanRange={
                'Start': start_range,
                'End': end_range
            },
        )

        """
        select_object_content() response is an event stream which can be looped to concatenate the overall result set
        Hence, we are joining the results of the stream in string before converting it to a tuple of dict
        """
        result_stream = []
        for event in response['Payload']:
            if records := event.get('Records'):
                result_stream.append(records['Payload'].decode('utf-8'))
        yield ast.literal_eval(''.join(result_stream))
        start_range = end_range
        end_range = end_range + min(chunk_bytes, file_size - end_range)
