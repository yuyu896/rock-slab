from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_DECODED_IMAGE_PIXELS = 40_000_000
MAIN_IMAGE_MAX_EDGE = 2048
THUMBNAIL_MAX_EDGE = 240
MAIN_IMAGE_QUALITY = 82
THUMBNAIL_QUALITY = 75
SUPPORTED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}


class ImageProcessingError(ValueError):
    """The uploaded or stored file is not a supported, decodable image."""


def _load_image(source):
    try:
        source.seek(0)
        with Image.open(source) as opened:
            if opened.format not in SUPPORTED_IMAGE_FORMATS:
                raise ImageProcessingError('仅支持 JPG、PNG、WebP 格式的图片')
            width, height = opened.size
            if width <= 0 or height <= 0 or width * height > MAX_DECODED_IMAGE_PIXELS:
                raise ImageProcessingError('图片解码尺寸超出限制')
            opened.verify()

        source.seek(0)
        with Image.open(source) as opened:
            opened.seek(0)
            image = ImageOps.exif_transpose(opened).copy()
            image.load()
            has_alpha = (
                image.mode in ('RGBA', 'LA')
                or 'transparency' in image.info
            )
            return image.convert('RGBA' if has_alpha else 'RGB')
    except ImageProcessingError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageProcessingError('图片解码尺寸超出限制') from exc
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise ImageProcessingError('无法读取有效图片文件') from exc


def _encode_webp(image, max_edge, quality):
    output = BytesIO()
    resized = image.copy()
    resized.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    resized.save(output, format='WEBP', quality=quality, method=6)
    return output.getvalue()


def _already_optimized_webp(source, image, source_format, orientation, is_animated):
    if (
        source_format != 'WEBP'
        or max(image.size) > MAIN_IMAGE_MAX_EDGE
        or orientation not in (None, 1)
        or is_animated
    ):
        return None
    source.seek(0)
    return source.read()


def normalize_uploaded_image(source):
    """Return (main_webp, thumbnail_webp), validating decoded dimensions first."""
    try:
        source.seek(0)
        with Image.open(source) as opened:
            source_format = opened.format
            width, height = opened.size
            orientation = opened.getexif().get(274)
            is_animated = getattr(opened, 'is_animated', False)
            if (
                width <= 0
                or height <= 0
                or width * height > MAX_DECODED_IMAGE_PIXELS
            ):
                raise ImageProcessingError('图片解码尺寸超出限制')
        image = _load_image(source)
    except ImageProcessingError:
        raise
    except Exception as exc:
        raise ImageProcessingError('无法读取有效图片文件') from exc

    try:
        main_webp = _already_optimized_webp(
            source, image, source_format, orientation, is_animated,
        )
        if main_webp is None:
            main_webp = _encode_webp(image, MAIN_IMAGE_MAX_EDGE, MAIN_IMAGE_QUALITY)
        thumbnail_webp = _encode_webp(image, THUMBNAIL_MAX_EDGE, THUMBNAIL_QUALITY)
        return main_webp, thumbnail_webp
    except Exception as exc:
        raise ImageProcessingError('无法压缩图片文件') from exc


def create_thumbnail(source):
    """Create a bounded WebP thumbnail from a legacy image without modifying it."""
    return _encode_webp(_load_image(source), THUMBNAIL_MAX_EDGE, THUMBNAIL_QUALITY)
