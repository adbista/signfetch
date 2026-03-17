class SignfetchError(Exception):
    # Base package error.
    pass

class DiscoveryError(SignfetchError):
    # Error during signposting discovery.
    pass

class DownloadError(SignfetchError):
    # Error during data download.
    pass