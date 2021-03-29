
from flask import Blueprint, current_app
from werkzeug.local import LocalProxy

from authentication import require_appkey

from .tasks import s3_file_processing_task, test_task

core = Blueprint('core', __name__)
logger = LocalProxy(lambda: current_app.logger)


@core.before_request
def before_request_func():
    current_app.logger.name = 'core'


@core.route('/test', methods=['GET'])
def test():
    logger.info('app test route hit')
    test_task.delay()
    return 'Congratulations! Your core-app test route is running!'


@core.route('/restricted', methods=['GET'])
@require_appkey
def restricted():
    return 'Congratulations! Your core-app restricted route is running via your API key!'


@core.route('/s3_select', methods=['GET'])
def s3_select():
    s3_file_processing_task.apply_async(
        kwargs={
            'bucket': current_app.config.get('AWS_S3_BUCKET'),
            'key': current_app.config.get('AWS_S3_KEY')
        }
    )
    return 'S3 file processing task initiated'
