import ast
from typing import Tuple

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


def stream_s3_file(bucket: str, key: str, file_size: int, chunk_bytes=5000) -> Tuple[dict]:
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


def store_scrm_file_s3_content_in_local_file(bucket: str, key: str, file_path: str, start_range: int, end_range: int,
                                             delimiter: str, header_row: str):
    """Retrieves S3 file content via S3 Select ScanRange and store it in a local file.
       Make sure the header valdiation is done before calling this.

    Args:
        bucket (str): S3 bucket
        key (str): S3 key
        file_path (str): Local file path to store the contents
        start_range (int): Start range of ScanRange parameter of S3 Select
        end_range (int): End range of ScanRange parameter of S3 Select
        delimiter (str): S3 file delimiter
        header_row (str): Header row of the local file. This will be inserted as first line in local file.
    """
    aws_profile = current_app.config.get('AWS_PROFILE_NAME')
    s3_client = boto3.session.Session(profile_name=aws_profile).client('s3')
    expression = 'SELECT * FROM S3Object'
    try:
        response = s3_client.select_object_content(
            Bucket=bucket,
            Key=key,
            ExpressionType='SQL',
            Expression=expression,
            InputSerialization={
                'CSV': {
                    'FileHeaderInfo': 'USE',
                    'FieldDelimiter': delimiter,
                    'RecordDelimiter': '\n'
                }
            },
            OutputSerialization={
                'CSV': {
                    'FieldDelimiter': delimiter,
                    'RecordDelimiter': '\n',
                },
            },
            ScanRange={
                'Start': start_range,
                'End': end_range
            },
        )

        """
        select_object_content() response is an event stream which can be looped to concatenate the overall result set
        """
        f = open(file_path, 'wb')  # we receive data in bytes and hence opening file in bytes
        f.write(header_row.encode())
        f.write('\n'.encode())
        for event in response['Payload']:
            if records := event.get('Records'):
                f.write(records['Payload'])
        f.close()
    except ClientError:
        logger.exception(f'Client error reading S3 file {bucket} : {key}')
    except Exception:
        logger.exception(f'Error reading S3 file {bucket} : {key}')


def validate_scrm_file_headers_via_s3_select(
        bucket: str, key: str, delimiter: str, desired_headers: Tuple[str]) -> Tuple[bool, str]:
    """Validates the SCRM file headers via S3 Select query

    Args:
        bucket (str): S3 bucket
        key (str): S3 key
        delimiter (str): File delimiter
        desired_headers (Tuple[str]): The headers against which the validation will run

    Returns:
        Tuple[bool, str]: Returns a bool result (True if validation successfull) along with the header row
    """
    row_headers = []
    result = False
    aws_profile = current_app.config.get('AWS_PROFILE_NAME')
    s3_client = boto3.session.Session(profile_name=aws_profile).client('s3')
    expression = 'SELECT * FROM S3Object LIMIT 1'
    try:
        response = s3_client.select_object_content(
            Bucket=bucket,
            Key=key,
            ExpressionType='SQL',
            Expression=expression,
            InputSerialization={
                'CSV': {
                    'FileHeaderInfo': 'NONE',  # This will make S3 Select return headers as well
                    'FieldDelimiter': delimiter,
                    'RecordDelimiter': '\n'
                }
            },
            OutputSerialization={
                'CSV': {
                    'FieldDelimiter': delimiter,
                    'RecordDelimiter': '\n',
                },
            },
        )

        """
        select_object_content() response is an event stream which can be looped to concatenate the overall result set
        Hence, we are joining the results of the stream in string before converting it to a desired data type
        """
        result_stream = []
        for event in response['Payload']:
            if records := event.get('Records'):
                result_stream.append(records['Payload'].decode('utf-8'))
        row_headers = ''.join(result_stream).split(delimiter)
        # removing line break character from last element
        row_headers[-1] = row_headers[-1].replace('\r', '').replace('\n', '')
        if not set(desired_headers).issubset(row_headers):
            logger.error('Error in file. Desired headers not found!!')
            logger.error(f'Columns not found -> {set(desired_headers) - set(row_headers)}')
        else:
            result = True
    except ClientError:
        logger.exception(f'Boto3 Client error reading S3 file {bucket} : {key}')
    except Exception:
        logger.exception(f'Error reading S3 file {bucket} : {key}')
    return result, delimiter.join(row_headers)
