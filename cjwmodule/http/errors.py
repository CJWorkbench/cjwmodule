from cjwmodule.i18n.cjwmodule import trans
from cjwmodule.i18n import I18nMessage


__all__ = ["HttpError"]


class HttpError(Exception):
    """
    An HTTP request did not complete.
    """

    @property
    def i18n_message(self) -> I18nMessage:
        return I18nMessage("TODO_i18n", {"text": self.args[0]}, "cjwmodule")


class HttpErrorTimeout(HttpError):
    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return trans("http.errors.HttpErrorTimeout", "HTTP request timed out.")
    


class HttpErrorInvalidUrl(HttpError):
    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return trans(
            "http.errors.HttpErrorInvalidUrl", 
            "Invalid URL. Please supply a valid URL, starting with http:// or https://."
        )


class HttpErrorTooManyRedirects(HttpError):
    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return trans(
            "http.errors.HttpErrorTooManyRedirects", 
            "HTTP server(s) redirected us too many times. Please try a different URL."
        )


class HttpErrorNotSuccess(HttpError):
    def __init__(self, response):
        self.response = response

    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return trans(
            "http.errors.HttpErrorNotSuccess", 
            "Error from server: HTTP {status_code} {description}",
            {
                "status_code": self.response.status_code, 
                "description": self.response.reason_phrase
            }
        )


class HttpErrorGeneric(HttpError):
    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return trans(
            "http.errors.HttpErrorGeneric", 
            "Error during HTTP request: {error}",
            {
                "error": type(self.__cause__).__name__
            }
        )


HttpError.Timeout = HttpErrorTimeout
HttpError.Generic = HttpErrorGeneric
HttpError.InvalidUrl = HttpErrorInvalidUrl
HttpError.NotSuccess = HttpErrorNotSuccess
HttpError.TooManyRedirects = HttpErrorTooManyRedirects
