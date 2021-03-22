import datetime


def fill_template(filename):
    """jinja2-like template filling"""
    filename = filename.replace('{datetime}', datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    return filename
