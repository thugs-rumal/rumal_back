#!/usr/bin/env python
#
# views.py
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA  02111-1307  USA
#
# Author:   Tarun Kumar <reach.tarun.here@gmail.com>
#
from bson import ObjectId
import json


class DownloadError(Exception):
    pass


def is_text(mime):
    if mime.startswith('text/'):
        return True

    if mime in ['application/xml']:
        return True

    return False


def clone_without_object_ids(aDict, key_exclude_filter=None):
    if isinstance(aDict, dict):
        # if key_exclude_filter is defined use it to filter
        if key_exclude_filter:
            return {key: value for key, value in aDict.iteritems() if not
                    isinstance(value, ObjectId) and key != key_exclude_filter}
        # otherwise just remove ObjectId keys
        return {key: value for key, value in aDict.iteritems() if not isinstance(value, ObjectId)}
    # if argument is not a dict just return it as it was
    return aDict


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        else:
            return obj
