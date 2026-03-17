class SignfetchError(Exception):
    # Base package error.


class DiscoveryError(SignfetchError):
    # Error during signposting discovery.


class DownloadError(SignfetchError):
    # Error during data download.
