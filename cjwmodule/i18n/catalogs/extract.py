# -*- coding: utf-8 -*-
import logging
import os
import pathlib
import re
from io import BytesIO
from typing import Any, Dict, Generator, List, Tuple

from babel.messages.catalog import Catalog, Message
from babel.messages.extract import (
    check_and_call_extract_file,
    extract_from_dir,
    extract_python,
)
from babel.messages.pofile import read_po, write_po

from cjwmodule.i18n.locales import default_locale_id, supported_locale_ids
from cjwmodule.settings import ROOT_DIR

default_locale_id = "en"
supported_locale_ids = ["en", "el"]

logger = logging.getLogger(__name__)

_default_message_re = re.compile(r"\s*default-message:\s*(.*)\s*")


def _extract_python(
    fileobj: BytesIO, _keywords: Any, _comment_tags: Any, options: Dict[Any, Any]
) -> Generator[Tuple[int, str, List[Any], List[str]], None, None]:
    """Extract messages from project python code.
    
    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param _keywords: Ignored
    :param _comment_tags: Ignored
    :param options: a dictionary of additional options (optional)
    :rtype: ``iterator``
    """
    keywords = ["_trans_cjwmodule"]
    comment_tags = ["i18n"]
    for (message_lineno, funcname, messages, translator_comments,) in extract_python(
        fileobj, keywords, comment_tags, options
    ):
        # `messages` will have all the string parameters to our function
        # As we specify in the documentation of `trans`,
        # the first will be the message ID, the second will be the default message
        if len(messages) > 1 and messages[1]:
            # If we have a default, add it as a special comment
            # that will be processed by our `merge_catalogs` script
            translator_comments.append(
                (message_lineno, "default-message: " + messages[1])
            )

        # Pybabel expects a `funcname` of the `gettext` family, or `None`.
        funcname = None

        yield (
            message_lineno,
            funcname,
            messages[0],
            [comment[1] for comment in translator_comments],
        )


def catalog_path(locale_id: str) -> pathlib.Path:
    return pathlib.Path(ROOT_DIR) / "i18n" / f"{locale_id}.po"


def pot_catalog_path() -> pathlib.Path:
    return pathlib.Path(ROOT_DIR) / "i18n" / f"{default_locale_id}.pot"


def extract():
    mappings = [(ROOT_DIR, [("**.py", _extract_python)], {})]
    pot_catalog = Catalog(default_locale_id)

    for path, method_map, options_map in mappings:

        def callback(filename, method, options):
            if method == "ignore":
                return

            # If we explicitly provide a full filepath, just use that.
            # Otherwise, path will be the directory path and filename
            # is the relative path from that dir to the file.
            # So we can join those to get the full filepath.
            if os.path.isfile(path):
                filepath = path
            else:
                filepath = os.path.normpath(os.path.join(path, filename))

            optstr = ""
            if options:
                optstr = " (%s)" % ", ".join(
                    ['%s="%s"' % (k, v) for k, v in options.items()]
                )
            logger.info("extracting messages from %s%s", filepath, optstr)

        if os.path.isfile(path):
            current_dir = os.getcwd()
            extracted = check_and_call_extract_file(
                path, method_map, options_map, callback, {}, [], False, current_dir
            )
        else:
            extracted = extract_from_dir(
                path,
                method_map,
                options_map,
                keywords={},
                comment_tags=[],
                callback=callback,
                strip_comment_tags=False,
            )
        for filename, lineno, message, comments, context in extracted:
            if os.path.isfile(path):
                filepath = filename  # already normalized
            else:
                filepath = os.path.normpath(os.path.join(path, filename))

            pot_catalog.add(
                message,
                None,
                [(filepath, lineno)],
                auto_comments=comments,
                context=context,
            )

    with open(pot_catalog_path(), "wb") as pot_file:
        logger.info("writing PO template file to %s", pot_file)
        write_po(
            pot_file,
            pot_catalog,
            ignore_obsolete=True,
            width=10000000,  # we set a huge value for width, so that special comments do not wrap
            omit_header=True,
        )

    default_messages = {}
    for message in pot_catalog:
        if message.id:
            for comment in message.auto_comments:
                match = re.match(_default_message_re, comment)
                if match:
                    default_message = match.group(1).strip()
                    default_messages[message.id] = default_message
                    message.auto_comments.remove(comment)

    _update_default_catalog(pot_catalog, default_messages)
    for locale_id in supported_locale_ids:
        if locale_id != default_locale_id:
            _update_catalog(locale_id, pot_catalog)


def _update_default_catalog(pot_catalog: Catalog, default_messages: Dict[str, str]):
    catalog = Catalog(default_locale_id)
    for message in pot_catalog:
        if message.id:
            catalog.add(
                message.id,
                string=default_messages.get(message.id, ""),
                auto_comments=message.auto_comments,
                user_comments=message.user_comments,
                flags=message.flags,
                locations=message.locations,
            )

    with open(catalog_path(default_locale_id), "wb") as po_file:
        logger.info("writing PO file for %s to %s", default_locale_id, po_file)
        write_po(
            po_file, catalog,
        )


def _update_catalog(locale_id: str, pot_catalog: Catalog):
    try:
        with open(catalog_path(locale_id), "rb") as po:
            old_catalog = read_po(po)
    except FileNotFoundError:
        old_catalog = Catalog(locale_id)

    catalog = Catalog(locale_id)
    for message in pot_catalog:
        if message.id:
            old_message = old_catalog.get(message.id)
            catalog.add(
                message.id,
                string=old_message.string if old_message else "",
                auto_comments=message.auto_comments,
                user_comments=message.user_comments,
                flags=message.flags,
                locations=message.locations,
            )

    with open(catalog_path(locale_id), "wb") as po_file:
        logger.info("writing PO file for %s to %s", locale_id, po_file)
        write_po(
            po_file, catalog,
        )


if __name__ == "__main__":
    extract()
