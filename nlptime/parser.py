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
    def parse_cardinal_time(self, word):
        word_type = "minute"
        if ":" in word.orth_:
            c_split = word.orth_.split(":")
            hour_int, minute_int = (int(i) for i in c_split)
        else:
            hour_int = int(word.orth_)
            minute_int = 0
        now = datetime.datetime.now()
        am = any([word.orth_.lower() == "am" for word in self.parsed])
        pm = any([word.orth_.lower() == "pm" for word in self.parsed])
        if now.minute > minute_int:
            minute_difference = -(now.minute - minute_int)
        elif now.minute == minute_int:
            minute_difference = 0
        else:
            minute_difference = (60 - minute_int) + now.minute
        if hour_int > now.hour:
            log.debug("Hour {0} is greater than the current hour {1}".format(hour_int, now.hour))
            hour_difference = hour_int - now.hour
        elif hour_int == now.hour or hour_int+12 == now.hour:
            log.debug("Hour {0} and current hour {1} are the same".format(hour_int, now.hour))
            hour_difference = 0
        else:
            log.debug("Hour {0} is less than the current hour {1}".format(hour_int, now.hour))
            if now.hour > 12:
                if hour_int <= 12:
                    if pm or self.preference == "future":
                        if hour_int + 12 > now.hour:
                            hour_difference = hour_int + 12 - now.hour
                    elif am:
                        hour_difference = (24-now.hour)+hour_int
                else:
                    # Both are greater than twelve but hour_int is less than now.hour
                    if am:
                        hour_difference = (24+hour_int)
                    else:
                        hour_difference = (hour_int + 24) - now.hour
            else:
                # Both are less than 12, and hour_int is less than now.hour
                hour_difference = (hour_int + 12) - now.hour
        multiplier = (60 * hour_difference) + minute_difference
        log.debug("Found cardinal time {0}. Hour difference is {1} and minute difference is {2} for a total"
                  " multiplier of {3}".format(word.orth_, hour_difference, minute_difference, multiplier))
        return [word_type, multiplier]
    def get_delta(self):
        """
        Use all of the available data
        :return:
        """
        #Make sure that the word type is already defined
        assert self.word_type
        if not self.multiplier:
            self.multiplier = 1
        log.debug("Fetching delta from word type {0} and multiplier {1}".format(self.word_type, self.multiplier))
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
        now = datetime.datetime.now()
        if self.word_type == "hour":
            base_delta = relativedelta(hours=+self.multiplier, seconds=-(datetime.datetime.now().second))
        elif self.word_type == "minute":
            base_delta = relativedelta(minutes=+self.multiplier, seconds=-(datetime.datetime.now().second))
        elif self.word_type == "day":
            base_delta = relativedelta(days=+self.multiplier, seconds=-(datetime.datetime.now().second))
        elif self.word_type == "second":
            base_delta = relativedelta(seconds=+self.multiplier)
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
        else:
            raise WordTypeNotFoundError("No handlers registered for word type {0}, of type {1}".format(self.word_type,
                                                                                                       type(self.word_type)))
        log.debug("Found delta {0}".format(base_delta))
        if not self.relative and "seconds" not in self.word_type:
            base_delta.seconds = -(now.second)
        #Check the return delta setting
        if self.return_delta:
            self.datetime_found = base_delta
        else:
            #Get a datetime from the delta
            self.datetime_found = datetime.datetime.now()+base_delta


    def dependency_parse(self):
        """
        First and most accurate parsing step, using lexical dependencies.
        For each type of dependency check a language specific resource for associated time words

        """
        parsed_sentence = self.parsed
        word_type = None
        multiplier = None
        sentence_deps = set([w.dep_ for w in parsed_sentence])
        for word in parsed_sentence:
            #If there's a word prefaced by a number
            #Add a special case for am, treat it as AM.
            #To somewhat mitigate the special case being incorrectly triggered by the actual word 'am',
            #only do this if there are entities in the sentence
            if list(word.lefts) and "nummod" in sentence_deps:
                first_left = list(word.lefts)[0]
                log.debug("Found nummod type pair {0} and {1}".format(word.orth_, first_left.orth_))
                if first_left.is_digit:
                    word_type = self.check_time_word(word, "nummod")
                    multiplier = int(first_left.orth_)
                    break
            elif word.dep_ == "pobj":
                #Check for a cardinal time
                if cardinal_time_pattern.match(word.orth_):
                    word_type, multiplier = self.parse_cardinal_time(word)
                    break
                elif date_pattern.match(word.orth_):
                    log.debug("Found date {0}".format(word.orth_))
                    if "/" in word.orth_:
                        word_type = "slashdate"
                    else:
                        word_type = "dotdate"
                    break
                else:
                    self.relative == True
                    word_type = self.check_time_word(word, "pobj")
                    break
            #Only use a number for a parse if there's not a significant dependency in the sentence
            elif word.is_digit and "pobj" not in sentence_deps:
                word_type, multiplier = self.parse_cardinal_time(word)
                break
        self.word_type = word_type
        self.multiplier = multiplier

    def offset_time(self):
        """
        Take the final time and offset it according to the passed LST offset

        :param final_time: A datetime object representing the time that was found
        :return formatted_time: A datetime object, final_time offset by self.lst_offset
        """
        final_time = self.datetime_found
        if self.lst_offset:
            t_delta = datetime.timedelta(hours=self.lst_offset)
            formatted_time = final_time + t_delta
        else:
            formatted_time = final_time
        self.datetime_found = final_time

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
                #Use [0].orth_ instead of .text here. It would work with .text, but this has the added bonuns of
                #always being a single word
                return type_similarities[max(type_similarities)][0].orth_

    def parse(self, parse_str):
        """
        Run all the possible parsing steps and return the most accurate answer or guess that can be found

        :param parse_str: The string to parse
        :return datetime_found: The final found datetime object
        """
        self.parsed = self.model(parse_str)
        word_steps = [self.dependency_parse]
        parse_steps = [self.get_delta]
        for step in word_steps:
            step()
            if self.word_type:
                break
        if not self.word_type:
            error_string = "Couldn't find any times in {0}. {1} steps attempted.".format(parse_str, len(word_steps))
            log.error(error_string)
            if self.allow_none:
                return None
            else:
                raise WordTypeNotFoundError(error_string)
        for step in parse_steps:
            step()
            if self.datetime_found:
                break
        if not self.datetime_found:
            error_string = "Couldn't find any times in {0}. {1} steps attempted.".format(parse_str, len(parse_steps))
            if self.allow_none:
                return None
            else:
                raise NoTimesFoundError(error_string)
        self.offset_time()
        return self.datetime_found

    def __init__(self, time_words, preference, model=None, lst_offset=None, return_delta=False, allow_none=False):
        self.model = model
        self.lst_offset = lst_offset
        self.time_words = time_words
        self.preference = preference
        self.datetime_found = None
        self.return_delta = return_delta
        self.allow_none = allow_none
        self.relative = False
        #Words for various dependency types
        #Time words that are often prefaced by cardinal numbers

