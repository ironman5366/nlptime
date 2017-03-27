import logging

from . import utils
from . import parser

import os

log = logging.getLogger()

backends_available = []

try:
    import spacy
    from spacy.symbols import ORTH, DEP, LEMMA
    backends_available.append("spacy")
except ImportError:
    log.warn("Couldn't import spacy, spacy backend will not be available")

try:
    import nltk
    backends_available.append("nltk")
except ImportError:
    log.warn("Couldn't import nltk, nltk backend will not be available")

class BackendNotAvaialbleError(Exception):
    pass

class NoTimeFoundError(Exception):
    pass

class PreferenceNotFoundError(Exception):
    pass

class nlptime:

    def parse(self, parse_str):
        """
        Parse a string into a datetime object

        :param parse_str:
        :return datetime object:
        """
        #Run the time string through the parser with the specified options
        p = self.parser.parse(
            parse_str=parse_str
        )
        log.debug("Got time output {0}".format(p))
        return p

    def __init__(self, language="en", spacy_model=None, log=log, lst_offset=None, preference=None, return_delta=False, allow_none=False):
        """
        Create an nlptime class. Define the backend and language, and, if using spacy, optionally pass a preloaded model

        :param backend: The nlp backend to use
        :param language: The language
        :param spacy_model: If the backend is spacy, optionally provide a preloaded model instead of loading one
        :param log: Optionally provide a logging interface. Otherwise use logging.getLogger
        :param lst_offset: The amount to offset the local time by
        :param preference: Prefer the past or future for local time
        :param return_delta: Whether to return a dateutil.relativedelta object instead of an absolute datetime object
        :param allow_none: Whether to suppress errors and return None instead of raising an error when no time can be found. Useful for batch parsing
        """
        self.lst_offset = lst_offset
        self.preference = preference
        self.return_delta = return_delta
        self.allow_none = allow_none
        #The offset from LST or "Local Standard Time"
        preferences_available = ["past", "future"]
        log.debug("Loading spacy backend")
        if spacy_model:
            assert type(spacy_model) == spacy.en.English
            self.model = spacy_model
        else:
            if "spacy" in backends_available:
                self.model = spacy.load(language)
            else:
                error_string = "Spacy backend was specified, but spacy is unavailable on this system"
                log.error(error_string)
                raise BackendNotAvaialbleError(error_string)
        #Setting for whether to prefer the future or past
        if preference:
            if preference not in preferences_available:
                raise PreferenceNotFoundError
        if lst_offset:
            assert type(lst_offset) == int
        log.debug("Loading language utilities")
        self.lang_utils = utils.lang_utils(self.model, language)
        self.time_words = self.lang_utils.time_load()

        self.parser = parser.Parse(
            time_words=self.time_words,
            model=self.model,
            preference=self.preference,
            lst_offset=self.lst_offset,
            return_delta=self.return_delta,
            allow_none=self.allow_none,
        )