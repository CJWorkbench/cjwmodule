from cjwmodule.i18n import I18nMessage, _trans_cjwmodule

__all__ = ["HttpError"]


class HttpError(Exception):
    """
    An HTTP request did not complete.
    """

    @property
    def i18n_message(self) -> I18nMessage:
        """A message descrbing the error to the user.

        Must be overriden by subclasses.
        """
        raise NotImplementedError()


class HttpErrorTimeout(HttpError):
    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return _trans_cjwmodule(
            "http.errors.HttpErrorTimeout", "HTTP request timed out."
        )


class HttpErrorInvalidUrl(HttpError):
    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return _trans_cjwmodule(
            "http.errors.HttpErrorInvalidUrl",
            "Invalid URL. Please supply a valid URL, starting with http:// or https://.",
        )


class HttpErrorTooManyRedirects(HttpError):
    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return _trans_cjwmodule(
            "http.errors.HttpErrorTooManyRedirects",
            "HTTP server(s) redirected us too many times. Please try a different URL.",
        )


class HttpErrorNotSuccess(HttpError):
    def __init__(self, response):
        self.response = response

    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return _trans_cjwmodule(
            "http.errors.HttpErrorNotSuccess",
            "Error from server: HTTP {status_code} {reason}",
            {
                "status_code": self.response.status_code,
                "reason": self.response.reason_phrase,
            },
        )


class HttpErrorGeneric(HttpError):
    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return _trans_cjwmodule(
            "http.errors.HttpErrorGeneric",
            "Error during HTTP request: {type}",
            {"type": type(self.__cause__).__name__},
        )


HttpError.Timeout = HttpErrorTimeout
HttpError.Generic = HttpErrorGeneric
HttpError.InvalidUrl = HttpErrorInvalidUrl
HttpError.NotSuccess = HttpErrorNotSuccess
HttpError.TooManyRedirects = HttpErrorTooManyRedirects
