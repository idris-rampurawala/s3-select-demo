from celery.utils.log import get_task_logger

from app import celery

from .utils import get_s3_file_size, stream_s3_file

logger = get_task_logger(__name__)


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
