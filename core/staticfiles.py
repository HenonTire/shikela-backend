# core/staticfiles.py
import logging

from whitenoise.storage import CompressedStaticFilesStorage

logger = logging.getLogger(__name__)


class ResilientCompressedStaticFilesStorage(CompressedStaticFilesStorage):
    """
    Same as whitenoise's CompressedStaticFilesStorage, but if an individual
    file goes missing between being collected and being compressed, log a
    warning and skip it instead of crashing the entire collectstatic run.
    """

    def post_process(self, paths, dry_run=False, **options):
        if dry_run:
            return

        extensions = getattr(self, "_skip_compress_extensions", None)
        compressor = self.create_compressor(extensions=extensions, quiet=True)

        for path in paths:
            if not compressor.should_compress(path):
                continue
            full_path = self.path(path)
            prefix_len = len(full_path) - len(path)
            try:
                for compressed_path in compressor.compress(full_path):
                    yield path, compressed_path[prefix_len:], True
            except FileNotFoundError:
                logger.warning(
                    "Skipping compression for missing static file: %s", path
                )
                continue