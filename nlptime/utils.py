import logging
import os
import json

log = logging.getLogger()

class LanguageNotAvailableError(Exception):
    pass

class UtilNotFoundError(Exception):
    pass

class lang_utils:
    def time_load(self, time_word_file="dependency_words.json"):
        """
        Load the time words for the specified language

        :param time_word_file: the filename to look for in the language utilities
        :return parsed_time_words: the time words from the file, parsed with whatever backend used
        """
        #Check to make sure utilities for that language for that language are supported
        time_word_path = os.path.join(self.lang_dir, time_word_file)
        if os.path.isfile(time_word_path):
            time_words = json.load(open(time_word_path))
            #Use self.nlp to parse all the time words
            parsed_time_words = {}
            for time_type, word_list in time_words.items():
                parsed_time_words.update({
                    time_type: [self.nlp(w) for w in word_list]
                })
            log.debug("Opened time words file {0} and parsed all time words".format(time_word_path))
            return parsed_time_words
        else:
            raise UtilNotFoundError(time_word_path)

    def __init__(self, nlp, lang):
        self.lang_dir = os.path.join(os.path.dirname(__file__), lang)
        if os.path.isdir(self.lang_dir):
            self.nlp = nlp
            self.lang = lang
        else:
            raise LanguageNotAvailableError("Couldn't find utilities for language {0} in directory {1}".format(lang, self.lang_dir))

