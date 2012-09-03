"""
wbdata: A wrapper for the World Bank API
"""

#Copyright (C) 2012  Oliver Sherouse <Oliver DOT Sherouse AT gmail DOT com>

#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; either version 2
#of the License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, unicode_literals

import datetime
import logging

try:
    import pandas as pd
except ImportError:
    pd = None

import fetcher

BASE_URL = "http://api.worldbank.org"
COUNTRIES_URL = "{0}/countries".format(BASE_URL)
ILEVEL_URL = "{0}/incomeLevels".format(BASE_URL)
INDICATOR_URL = "{0}/indicator".format(BASE_URL)
LTYPE_URL = "{0}/lendingTypes".format(BASE_URL)
SOURCES_URL = "{0}/sources".format(BASE_URL)
TOPIC_URL = "{0}/topics".format(BASE_URL)
INDIC_ERROR = "Cannot specify more than one of indicator, source, and topic"
FETCHER = fetcher.Fetcher()


def __parse_value_or_iterable(arg):
    """
    :arg: either a single object or a sequence of objects
    :returns: a string with either the single value or list joined by ';'
    """
    if isinstance(arg, basestring):
        return str(arg)
    return ";".join(arg)


def __parse_monthly_date(data_date):
    return data_date.strftime("%YM%m")


def __parse_quarterly_date(data_date):
    return "{0}Q{1}".format(data_date.year, data_date.month // 4)


def __parse_yearly_date(data_date):
    return data_date.strftime("%Y")


def __parse_data_date(frequency, data_date):
    if isinstance(data_date, datetime.date):
        try:
            return {"M": __parse_monthly_date,
                    "Q": __parse_quarterly_date,
                    "Y": __parse_yearly_date}[frequency](data_date)
        except KeyError:
            raise ValueError("Bad Frequency")
    elif len(data_date) == 2:
        try:
            parser = {"M": __parse_monthly_date,
                      "Q": __parse_quarterly_date,
                      "Y": __parse_yearly_date}[frequency]
            return ":".join((parser(data_date[0]), parser(data_date[1])))
        except KeyError:
            raise ValueError("Bad Frequency")
    raise TypeError("Bad data_date")


def __cast(value):
    try:
        return float(value)
    except:
        return None


def __convert_to_dataframe(data, column_name):
    if not pd:
        raise ValueError("Pandas must be installed to be used")
    return pd.DataFrame({"country": [i["country"]["value"] for i in data],
                         "date": [i["date"] for i in data],
                         column_name: [__cast(i["value"]) for i in data]})


def get_data(indicator, countries="all", aggregates=None, data_date=None,
             mrv=None, gapfill=None, frequency="Y", pandas=True,
             column_name="value"):
    """
    Retrieve indicators for given countries and years

    :indicator: the desired indicator code
    :countries: a country code, sequence of country codes, or "all" (default)
    :aggregates: the regional or aggregate code, or sequence thereof
    :date: the desired date as a datetime.date object or a 2-sequence with
        start and end dates
    :mrv: the number of most recent values to retrieve
    :gapfill: with mrv, fills gaps with the most recent values
    :frequency: 'Q', 'M', or 'Y' for quarterly, monthly, or annual data
    :pandas: if True, return results as a pandas DataFrame
    :column_name: the desired name for the pandas column
    :returns: list of dictionaries or pandas DataFrame
    """
    query_url = COUNTRIES_URL
    if aggregates:
        if countries != "all":
            raise ValueError("Cannot Specify both countries and aggregates")
        try:
            c_part = __parse_value_or_iterable(aggregates)
        except TypeError:
            raise TypeError("aggregates must be a string, iterable, or None")
    else:
        try:
            c_part = __parse_value_or_iterable(countries)
        except TypeError:
            raise TypeError("'countries' must be a string or iterable'")
    query_url = "/".join((query_url, c_part, "indicators", indicator))
    args = []
    if data_date:
        args.append(("date", __parse_data_date(frequency, data_date)))
    if mrv:
        args.append(("MRV", mrv))
    if gapfill:
        args.append(("Gapfill", "Y"))
    data = FETCHER.fetch(query_url, args)
    if pandas:
        return __convert_to_dataframe(data, column_name)
    return data


def __id_only_query(query_url, id_or_ids):
    """@todo: Docstring for __id_only_query

    :query_url: @todo
    :id_or_ids: @todo
    :returns: @todo
    """
    if id_or_ids:
        if type(id_or_ids) == "int":
            query_url = "{0}/{1}".format(query_url, type)
        else:
            id_part = "/".join([str(i) for i in id_or_ids])
            query_url = "{0}/{1}".format(query_url, id_part)
    return FETCHER.fetch(query_url)


def get_source(source_id=None):
    """
    Retrieve information on a source

    :source_id: an id number or sequence thereof.  None returns all sources.
    :returns: @todo
    """
    return __id_only_query(SOURCES_URL, source_id)


def get_incomelevel(level_id=None):
    """@todo: Docstring for get_incomelevel

    :level_id: @todo
    :returns: @todo
    """
    return __id_only_query(ILEVEL_URL, level_id)


def get_topic(topic_id=None):
    """@todo: Docstring for get_topic

    :topic_id: @todo
    :returns: @todo
    """
    return __id_only_query(TOPIC_URL, topic_id)


def get_lendingtype(type_id=None):
    """@todo: Docstring for get_lendingtype

    :level_id: @todo
    :returns: @todo
    """
    return __id_only_query(LTYPE_URL, type_id)


def get_indicator(indicator=None, source=None, topic=None):
    """
    Retrieve information about an indicator or indicators.  Only one of
    indicator, source, and topic can be specified.  Specifying none of the
    three will return all indicators.

    :indicator: the specific indicator code
    :source: a source id
    :topic: a topic id
    :returns: a list of dictionary objects representing indicators
    """
    if indicator:
        if source or topic:
            raise ValueError(INDIC_ERROR)
        query_url = "/".join((INDICATOR_URL, indicator))
        return FETCHER.fetch(query_url)
    if source:
        if topic:
            raise ValueError(INDIC_ERROR)
        query_url = "/".join((SOURCES_URL, str(source), "indicators"))
        return FETCHER.fetch(query_url)
    if topic:
        query_url = "/".join((TOPIC_URL, str(topic), "indicators"))
        return FETCHER.fetch(query_url)
    return FETCHER.fetch(INDICATOR_URL)


def search_indicators(query, source=None, topic=None):
    """
    Search indicators for a certain term.  Very simple.  Only one of source or
    topic can be specified

    :query: the term to match against indicator names
    :source: if present, id of desired source
    :topic: if present, id of desired topic
    :returns: a list of dictionaries representing indicators

    """
    indicators = get_indicator(source=source, topic=topic)
    lower = query.lower()
    return [i for i in indicators if lower in i["name"].lower()]


def examine(objs):
    """
    Courtesy function to display ids and names from lists returned by wbdata.
    This will mostly be useful in interactive mode.

    :objs: a list of dictionary objects as returned by wbdata
    """
    try:
        max_length = str(max((len(i['id']) for i in objs)))
    except ValueError:
        return
    for i in objs:
        templ = "{id:" + max_length + "}\t{name}"
        print(templ.format(**i))
