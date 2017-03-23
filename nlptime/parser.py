import datetime
import logging
import re
from dateutil.relativedelta import relativedelta

log = logging.getLogger()

cardinal_time_pattern = re.compile("((0?\d|1[0-2]):([0-5]\d)[ap]m|([0,1]?\d|2[0-3]):([0-5]\d))")

date_pattern = re.compile("([1-9]|1[0-2])[\/\.]([1-9]|[12]\d|3[01])[\/\.]\d{0,4}")

class NoTimesFoundError(Exception):
    pass

class WordTypeNotFoundError(Exception):
    pass

class Parse:

    def get_delta(self):
        """
        Use all of the available data
        :return:
        """
        #Make sure that the word type is already defined
        assert self.word_type
        if not self.multiplier:
            self.multiplier = 1
        #Start with monday as 0, following python datetime convention
        weekday_mappings = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6
        }
        month_mappings = {
            "january": 0,
            "february": 1,
            "march": 2,
            "april": 3,
            "may": 4,
            "june": 5,
            "july": 6,
            "august": 7,
            "september": 8,
            "october": 9,
            "november": 10,
            "december": 11
        }
        if self.word_type == "hour":
            base_delta = relativedelta(hours=+self.multiplier)
        elif self.word_type == "minute":
            base_delta = relativedelta(minutes=+self.multiplier)
        elif self.word_type == "day":
            base_delta = relativedelta(days=+self.multiplier)
        elif self.word_type == "microsecond":
            base_delta = relativedelta(microseconds=+self.multiplier)
        elif self.word_type == "month":
            base_delta = relativedelta(months=+self.multiplier)
        elif self.word_type == "years":
            base_delta = relativedelta(years=+self.multiplier)
        elif self.word_type == "week":
            base_delta = relativedelta(weeks=+self.multiplier)
        elif self.word_type in weekday_mappings.keys():
            current_weekday = datetime.datetime.today().weekday()
            word_day_mapping = weekday_mappings[self.word_type]
            if word_day_mapping > current_weekday or self.prefer == "past":
                base_delta = relativedelta(days=word_day_mapping-current_weekday)
            else:
                base_delta = relativedelta(days=7 + word_day_mapping)

        elif self.word_type in month_mappings.keys():
            current_month = datetime.datetime.today().month
            month_mapping = weekday_mappings[self.word_type]
            if month_mapping > current_month:
                base_delta = relativedelta(months=month_mapping-current_month)
            else:
                base_delta = relativedelta(months=12+month_mapping)
        #Check the return delta setting
        if self.return_delta:
            self.datetime_found = base_delta
        #Check to see whether it's in the past
        else:
            raise WordTypeNotFoundError("No handlers registered for word type {0}".format(self.word_type))

    def dependency_parse(self):
        """
        First and most accurate parsing step, using lexical dependencies.
        For each type of dependency check a language specific resource for associated time words

        """
        parsed_sentence = self.parsed
        word_type = None
        multiplier = None
        for word in parsed_sentence:
            #If there's a word prefaced by a number
            if word.dep_ == "nummod":
                first_left = word.lefts[0]
                if first_left.is_digit:
                    word_type = self.check_time_word(word, "nummod")
                    multiplier = int(first_left)
            elif word.dep_ == "pobj":
                #Check for a cardinal time
                if cardinal_time_pattern.match(word.orth_):
                    log.debug("Found cardinal time {0}".format(word.orth_))
                    word_type = "cardinal_time"
                elif date_pattern.match(word.orth_):
                    log.debug("Found date {0}".format(word.orth_))
                    if "/" in word.orth_:
                        word_type = "slashdate"
                    else:
                        word_type = "dotdate"
                else:
                    word_type = self.check_time_word(word, "pobj")
        self.word_type = word_type
        self.multiplier = multiplier

    def offset_time(self, final_time):
        """
        Take the final time and offset it according to the passed LST offset

        :param final_time: A datetime object representing the time that was found
        :return formatted_time: A datetime object, final_time offset by self.lst_offset
        """
        if self.lst_offset:
            t_delta = datetime.timedelta(hours=self.lst_offset)
            formatted_time = final_time + t_delta
        else:
            formatted_time = final_time
        return formatted_time

    def check_time_word(self, token, dep_type):
        """
        Go through the loaded time words for the language and try to classify a token based on them.
        Use the highest similarity from each classification and compare them

        :param token: A possible time word to check
        :return classification: The best guess for the classification
        """
        for word_type, word_list in self.time_words.items():
            if dep_type == dep_type:
                type_similarities = {}
                for word in word_list:
                    type_similarities.update({token.similarity(word):word})
                return type_similarities[max(type_similarities)]

    def parse(self, parse_str):
        """
        Run all the possible parsing steps and return the most accurate answer or guess that can be found

        :param parse_str: The string to parse
        :return datetime_found: The final found datetime object
        """
        self.parsed = self.model(parse_str)
        steps = [self.dependency_parse]
        for step in steps:
            step()
            if self.word_type:
                break
        if not self.word_type:
            error_string = "Couldn't find any times in {0}. {1} steps attempted.".format(parse_str, len(steps))
            log.error(error_string)
            if self.allow_none:
                return None
            else:
                raise NoTimesFoundError(error_string)
        #TODO: Parse the datetime from the found word type and possible multiplier
        return self.datetime_found

    def __init__(self, time_words, preference, model=None, lst_offset=None, return_delta=False, allow_none=False):
        self.model = model
        self.lst_offset = lst_offset
        self.time_words = time_words
        self.preference = preference
        self.datetime_found = None
        self.return_delta = return_delta
        self.allow_none = allow_none
        #Words for various dependency types
        #Time words that are often prefaced by cardinal numbers

