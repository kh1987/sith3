#
# Copyright 2023 © AE UTBM
# ae@utbm.fr / ae.info@utbm.fr
#
# This file is part of the website of the UTBM Student Association (AE UTBM),
# https://ae.utbm.fr.
#
# You can find the source code of the website at https://github.com/ae-utbm/sith3
#
# LICENSED UNDER THE GNU GENERAL PUBLIC LICENSE VERSION 3 (GPLv3)
# SEE : https://raw.githubusercontent.com/ae-utbm/sith3/master/LICENSE
# OR WITHIN THE LOCAL FILE "LICENSE"
#
#

from datetime import date

# Image utils
from io import BytesIO
from typing import Optional

import PIL
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpRequest
from django.utils import timezone
from PIL import ExifTags
from PIL.Image import Resampling


def get_start_of_semester(today: Optional[date] = None) -> date:
    """Return the date of the start of the semester of the given date.
    If no date is given, return the start date of the current semester.

    The current semester is computed as follows:

    - If the date is between 15/08 and 31/12  => Autumn semester.
    - If the date is between 01/01 and 15/02  => Autumn semester of the previous year.
    - If the date is between 15/02 and 15/08  => Spring semester

    Args:
        today: the date to use to compute the semester. If None, use today's date.

    Returns:
        the date of the start of the semester
    """
    if today is None:
        today = timezone.now().date()

    autumn = date(today.year, *settings.SITH_SEMESTER_START_AUTUMN)
    spring = date(today.year, *settings.SITH_SEMESTER_START_SPRING)

    if today >= autumn:  # between 15/08 (included) and 31/12 -> autumn semester
        return autumn
    if today >= spring:  # between 15/02 (included) and 15/08 -> spring semester
        return spring
    # between 01/01 and 15/02 -> autumn semester of the previous year
    return autumn.replace(year=autumn.year - 1)


def get_semester_code(d: Optional[date] = None) -> str:
    """Return the semester code of the given date.
    If no date is given, return the semester code of the current semester.

    The semester code is an upper letter (A for autumn, P for spring),
    followed by the last two digits of the year.
    For example, the autumn semester of 2018 is "A18".

    Args:
        d: the date to use to compute the semester. If None, use today's date.

    Returns:
        the semester code corresponding to the given date
    """
    if d is None:
        d = timezone.now().date()

    start = get_start_of_semester(d)

    if (start.month, start.day) == settings.SITH_SEMESTER_START_AUTUMN:
        return "A" + str(start.year)[-2:]
    return "P" + str(start.year)[-2:]


def scale_dimension(width, height, long_edge):
    ratio = long_edge / max(width, height)
    return int(width * ratio), int(height * ratio)


def resize_image(im, edge, img_format):
    (w, h) = im.size
    (width, height) = scale_dimension(w, h, long_edge=edge)
    img_format = img_format.upper()
    content = BytesIO()
    # use the lanczos filter for antialiasing and discard the alpha channel
    im = im.resize((width, height), Resampling.LANCZOS)
    if img_format == "JPEG":
        # converting an image with an alpha channel to jpeg would cause a crash
        im = im.convert("RGB")
    try:
        im.save(
            fp=content,
            format=img_format,
            quality=90,
            optimize=True,
            progressive=True,
        )
    except IOError:
        PIL.ImageFile.MAXBLOCK = im.size[0] * im.size[1]
        im.save(
            fp=content,
            format=img_format,
            quality=90,
            optimize=True,
            progressive=True,
        )
    return ContentFile(content.getvalue())


def exif_auto_rotate(image):
    for orientation in ExifTags.TAGS.keys():
        if ExifTags.TAGS[orientation] == "Orientation":
            break
    exif = dict(image._getexif().items())

    if exif[orientation] == 3:
        image = image.rotate(180, expand=True)
    elif exif[orientation] == 6:
        image = image.rotate(270, expand=True)
    elif exif[orientation] == 8:
        image = image.rotate(90, expand=True)

    return image


def get_client_ip(request: HttpRequest) -> str | None:
    headers = (
        "X_FORWARDED_FOR",  # Common header for proixes
        "FORWARDED",  # Standard header defined by RFC 7239.
        "REMOTE_ADDR",  # Default IP Address (direct connection)
    )
    for header in headers:
        if (ip := request.META.get(header)) is not None:
            return ip

    return None
