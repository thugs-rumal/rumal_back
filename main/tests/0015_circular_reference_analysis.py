#!/usr/bin/env python
#
# 0015_circular_reference_analysis.py
#
# Issue 15 https://github.com/thugs-rumal/rumal_back/issues/15
#
# Thug returns the analysis results in a set of mongodb collections.
# The particular scan of http://www.cesenainbolgia.net produces a circular reference while creating the tree resulting
# in the manipulation of the data never ending and run_thug hanging.
# This test imports the json data from the the analysis of this site to test if it loops infinitely.
# You would need to run the mongo daemon to perform this test.
#

import unittest
from bson import json_util
import os
import pymongo
import django

# Set up django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rumal_back.settings')
django.setup()

from main.management.commands import run_thug

client = pymongo.MongoClient()
db = client.thug

CIRCULAR_ANALYSIS_OBJECT_ID = '577ba91b2975c20001c6511f'
TREE_SIZE = 21

class TestCircularAnalysis(unittest.TestCase):

    @staticmethod
    def import_data(json_file, mongo_collection):

        with open(json_file, 'r') as f:
            for line in f:
                try:
                    mongo_collection.insert(json_util.loads(line))
                except pymongo.errors.DuplicateKeyError:
                    pass
                except pymongo.errors.ServerSelectionTimeoutError:
                    print "Connection Error with MongoDB. You have run the mongo daemon."

    def test_circular_analysis(self):

        self.import_data('files/0015_circular_reference_analysis/connections.json',
                         db.connections)

        self.import_data('files/0015_circular_reference_analysis/analyses.json',
                         db.analyses)

        self.import_data('files/0015_circular_reference_analysis/behaviors.json',
                         db.behaviors)

        self.import_data('files/0015_circular_reference_analysis/certificates.json',
                         db.certificates)

        self.import_data('files/0015_circular_reference_analysis/codes.json',
                         db.codes)

        self.import_data('files/0015_circular_reference_analysis/graphs.json',
                         db.graphs)

        self.import_data('files/0015_circular_reference_analysis/locations.json',
                         db.locations)

        self.import_data('files/0015_circular_reference_analysis/pcaps.json',
                         db.pcaps)

        self.import_data('files/0015_circular_reference_analysis/urls.json',
                         db.urls)

        self.assertTrue(run_thug.Command().club_collections(CIRCULAR_ANALYSIS_OBJECT_ID))
        print "Club Collections finished."

        tree = run_thug.Command().make_flat_tree({},  CIRCULAR_ANALYSIS_OBJECT_ID)
        self.assertTrue(len(tree["flat_tree"]), TREE_SIZE)
        print "Make flat tree finished with {} nodes.".format(len(tree["flat_tree"]))





