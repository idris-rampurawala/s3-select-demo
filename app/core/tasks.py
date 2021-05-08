import csv
from os import path, unlink

from celery import group
from celery.utils.log import get_task_logger
from flask import current_app

from app import celery

from .utils import (get_s3_file_size, store_scrm_file_s3_content_in_local_file,
                    stream_s3_file, validate_scrm_file_headers_via_s3_select)

logger = get_task_logger(__name__)

S3_FILE_DELIMITER = ','
S3_FILE_PROCESSING_CHUNK_SIZE = int(1024 * 1024 * 0.5)  # in bytes to retrieve via S3 Select ScanRange


@celery.task(name='core.tasks.test',
             soft_time_limit=60, time_limit=65)
def test_task():
    logger.info('running test task')
    return True


@celery.task(name='core.tasks.s3_file_processing')
def s3_file_processing_task(*args, **kwargs):
    bucket = kwargs.get('bucket')
    key = kwargs.get('key')
    file_size = get_s3_file_size(bucket=bucket, key=key)
    logger.debug(f'Initiating streaming file of {file_size} bytes')
    chunk_size = 524288  # 512KB or 0.5MB
    for file_chunk in stream_s3_file(bucket=bucket, key=key,
                                     file_size=file_size, chunk_bytes=chunk_size):
        logger.info(f'\n{30 * "*"} New chunk {30 * "*"}')
        id_set = set()
        for row in file_chunk:
            # perform any other processing here
            id_set.add(int(row.get('id')))
        logger.info(f'{min(id_set)} --> {max(id_set)}')


# ######################### Parallel processing tasks ##############################################
@celery.task(name='core.tasks.s3_parallel_file_processing', bind=True)
def s3_parallel_file_processing_task(self, **kwargs):
    """ Creates celery tasks to process chunks of file in parallel
    """
    bucket = kwargs.get('bucket')
    key = kwargs.get('key')
    try:
        filename = key
        # 1. Check file headers for validity -> if failed, stop processing
        desired_row_headers = (
            'id',
            'name',
            'age',
            'latitude',
            'longitude',
            'monthly_income',
            'experienced'
        )
        is_headers_valid, header_row_str = validate_scrm_file_headers_via_s3_select(
            bucket=bucket,
            key=key,
            delimiter=S3_FILE_DELIMITER,
            desired_headers=desired_row_headers)
        if not is_headers_valid:
            logger.error(f'{filename} file headers validation failed')
            return False
        logger.info(f'{filename} file headers validation successful')

        # 2. fetch file size via S3 HEAD
        file_size = get_s3_file_size(bucket=bucket, key=key)
        if not file_size:
            logger.error(f'{filename} file size invalid {file_size}')
            return False
        logger.info(f'We are processing {filename} file about {file_size} bytes :-o')

        # 2. Create celery group tasks for chunk of this file size for parallel processing
        start_range = 0
        end_range = min(S3_FILE_PROCESSING_CHUNK_SIZE, file_size)
        tasks = []
        while start_range < file_size:
            tasks.append(
                chunk_file_processor.signature(
                    kwargs={
                        'bucket': bucket,
                        'key': key,
                        'filename': filename,
                        'start_byte_range': start_range,
                        'end_byte_range': end_range,
                        'header_row_str': header_row_str
                    }
                )
            )
            start_range = end_range
            end_range = end_range + min(S3_FILE_PROCESSING_CHUNK_SIZE, file_size - end_range)
        job = (group(tasks) | chunk_file_processor_callback.s(data={'filename': filename}))
        _ = job.apply_async()
    except Exception:
        logger.exception(f'Error processing file: {filename}')


@celery.task(name='core.tasks.chunk_file_processor', bind=True)
def chunk_file_processor(self, **kwargs):
    """ Creates and process a single file chunk based on S3 Seelct ScanRange start and end bytes
    """
    bucket = kwargs.get('bucket')
    key = kwargs.get('key')
    filename = kwargs.get('filename')
    start_byte_range = kwargs.get('start_byte_range')
    end_byte_range = kwargs.get('end_byte_range')
    header_row_str = kwargs.get('header_row_str')
    local_file = filename.replace('.csv', f'.{start_byte_range}.csv')
    file_path = path.join(current_app.config.get('BASE_DIR'), 'temp', local_file)

    logger.info(f'Processing {filename} chunk range {start_byte_range} -> {end_byte_range}')
    try:
        # 1. fetch data from S3 and store it in a file
        store_scrm_file_s3_content_in_local_file(
            bucket=bucket, key=key, file_path=file_path, start_range=start_byte_range,
            end_range=end_byte_range, delimiter=S3_FILE_DELIMITER, header_row=header_row_str)

        # 2. Process the chunk file in temp folder
        id_set = set()
        with open(file_path) as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=S3_FILE_DELIMITER)
            for row in csv_reader:
                # perform any other processing here
                id_set.add(int(row.get('id')))
        logger.info(f'{min(id_set)} --> {max(id_set)}')

        # 3. delete local file
        if path.exists(file_path):
            unlink(file_path)
    except Exception:
        logger.exception(f'Error in file processor: {filename}')


@celery.task(name='core.tasks.chunk_file_processor_callback', bind=True, ignore_result=False)
def chunk_file_processor_callback(self, *args, **kwargs):
    """ Callback task called post chunk_file_processor()
    """
    logger.info('Callback called')
