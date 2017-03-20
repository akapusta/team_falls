#!/usr/bin/env python
#
#
# FHIR Client for using smart-on-fhir rest-api to read and write fhir resources, specifically for a
# falls-prevention FHIR app made for Georgia Tech class CS6440. Project was Improving Fall Prevention
# among Older Adults
#
#
# Author: Ari Kapusta (akapusta@gatech.edu)
# Team: Team Falls
# Members: Shujun Bian, Andrew Dean, Ari Kapusta, Lusenii Kromah
#
#

import json
import requests
import copy
import time

# Requires a smart-on-fhir api-server running on localhost. Find code to run that at
# https://github.com/smart-on-fhir/api-server
class FallsFHIRClient(object):
    def __init__(self):
        self.api_base = 'http://localhost:8080/'
        self.patient_id = None
        self.encounter_id = None
        self.load_standards_document()

    # Loads the latest standards document. Should probably be run occasionally or whenever things are
    # called to make sure questions are being kept up to date.
    # Input: nothing (it loads the document from a known location)
    # Returns: nothing
    # Note: We can change this to take input so you can tell it where the document is.
    def load_standards_document(self):
        with open('./fixtures/initial.json') as question_file:
            self.standards_document_dict = json.load(question_file)
        self.questions_text = []
        self.questions_code = []
        for question in self.standards_document_dict:
            if question['model'] == 'app.Question':
                self.questions_text.append(str(question['fields']['content']))
                self.questions_code.append(str(question['pk']))
        print 'Client has loaded the current standards document'

    # Search for a patient by name
    # Input: first_name, last_name
    # Returns: list of patients. Each is a dict.
    # Note: Patient_id is found at patient['resource']['identifier'][0]['value']
    # Requires: api-server running
    def search_patient(self, first_name, last_name):
        search_headers = {'Accept': 'application/json'}
        search_params = {'family': last_name, 'given': first_name}
        resp = requests.get(self.api_base + 'Patient/', headers=search_headers, params=search_params)
        if resp.status_code != 200 or resp.json()['total'] < 1:
            # This means something went wrong.
            print 'Something went wrong'
            return []
        else:
            # print resp.json()
            patient_list = resp.json()['entry']
            return patient_list

    # Search for a patient by name and date of birth. DoB can be entered by year, year and month, or year, month and
    # date.
    # Input: first_name, last_name, DoB as str(YYYY-MM-DD).
    # Returns: list of patients. Each is a dict.
    # Note: Checks from left to right, needs full amount. So you can enter YYYY or YYYY-MM or
    # YYYY-MM-DD
    # Patient_id is found at patient['resource']['identifier'][0]['value']
    # Requires: api-server running
    def search_patient_dob(self, first_name, last_name, date_of_birth):
        search_headers = {'Accept': 'application/json'}
        search_params = {'birthdate': date_of_birth,'family': last_name, 'given': first_name,  'gender': 'male'}
        resp = requests.get(self.api_base + 'Patient/', headers=search_headers, params=search_params)
        if resp.status_code != 200 or resp.json()['total'] < 1:
            # This means something went wrong.
            print 'Something went wrong'
            return []
        else:
            print resp.json()
            patient_list = resp.json()['entry']
            return patient_list

    # Function to select the patient (i.e., set the client's patient_id to the desired patient) based
    # on a returned list from search_patient or search_patient_dob.
    # Input: patient_list, index of desired patient (defaults to first on list)
    # Returns: nothing
    def select_patient_from_patient_result(self, patient_list, list_index=0):
        if len(patient_list) < list_index-1:
            print 'The index of the patient selected is higher than the number of patients available.'
            self.patient_id = None
        else:
            self.patient_id = patient_list[list_index]['resource']['identifier'][0]['value']

    # Function to select the patient (i.e., set the client's patient_id to the desired patient) based on
    # the function's input
    # Input: patient_id
    # Returns: nothing
    def select_patient(self, patient_id):
        self.patient_id = str(patient_id)

    # Search for encounters on a date and by patient_id. Sets client encounter_id if there is only one
    # matching encounter.
    # Input: Date str(YYYY-MM-DD), patient_id (by default uses the client's patient_id, if it has
    # been set)
    # Returns: list of encounters. Each is a dict.
    # Requires: api-server running
    def search_encounter(self, date, pat=None):
        if pat == None:
            pat = self.patient_id
        if not pat:
            print 'I am missing a patient_id to search for relevant encounters'
            return None
        encounter_list = []
        search_headers = {'Accept': 'application/json'}
        for stat in ['planned', 'arrived', 'in-progress']:
            search_params = {'subject': pat, 'status': stat}
            resp = requests.get(self.api_base + 'Encounter/', headers=search_headers, params=search_params)
            for enc in resp.json()['entry']:
                encounter_list.append(enc)
        matching_encounters = []
        for enc in encounter_list:
            if enc['resource']['period']['start'] == date:
                matching_encounters.append(enc)
        if len(matching_encounters) > 1:
            print 'There is more than one encounter that matches the date. Pick one.'
            print matching_encounters
            return matching_encounters
        else:
            self.encounter_id = enc['id']
            print matching_encounters
            return matching_encounters

    # Function to select the encounter (i.e., set the client's encounter_id to the desired patient)
    # based on the function's input
    # Input: encounter_id
    # Returns: nothing
    def select_encounter(self, encounter_id):
        self.encounter_id = str(encounter_id)

    # Function to look up the relevant procedure. If none exists, it will create one. This is primarily
    # for record keeping, to know when things have been done. Not currently particularly working or
    # valuable.
    # Input: patient_id, encounter_id (the default uses client values if they have been set)
    # Returns: The first matching procedure,
    # Note: Not particularly working yet.
    def pullup_procedure(self, pat=None, enc=None):
        if pat == None:
            pat = self.patient_id
        if enc == None:
            enc = self.encounter_id
        if not pat or not enc:
            print 'I am missing a patient_id or encounter_id to search for relevant observations'
            return None
        search_headers = {'Accept': 'application/json'}
        search_params = {'subject': pat, 'encounter': enc, 'category': 'fall_prevention'}
        resp = requests.get(self.api_base + 'Procedure/', headers=search_headers, params=search_params)
        if resp['total'] > 0:
            self.procedure = resp.json()['entry'][0]
            return self.procedure
        else:
            self.create_new_procedure()

    # Function to create a new procedure. This is primarily for record keeping, to know when things
    # have been done. Not currently working or.
    # Input: patient_id, encounter_id (the default uses client values if they have been set)
    # Returns: True if succeeds in creating a new procedure or False if fails.
    # Note: Not working.
    def create_new_procedure(self, pat=None, enc=None):
        if pat == None:
            pat = self.patient_id
        if enc == None:
            enc = self.encounter_id
        if not pat or not enc:
            print 'I am missing a patient_id or encounter_id to search for relevant observations'
            return None
        write_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        print 'I cannot make new procedures quite yet'
        resp = False
        if resp == '201':
            return True
        else:
            print 'Something went wrong when trying to write to the server'
            return False

    # Search for observations that are relevant to the app based on standards document.
    # Input: dict of standards, patient_id, encounter_id (by default uses the client's values, if they
    # have been set)
    # Returns: list of observations. Each is a dict. The key of the dict is the observation code.
    # Requires: api-server running
    def search_observations(self, standards_dict=None, pat=None, enc=None):
        output_dict = {}
        if pat == None:
            pat = self.patient_id
        if enc == None:
            enc = self.encounter_id
        if standards_dict == None:
            standards_dict = self.standards_document_dict
        if not pat or not enc or not standards_dict:
            print 'I am missing a patient_id, encounter_id, or standards_dict to search for relevant observations'
            return None
        search_headers = {'Accept': 'application/json'}
        search_params = {'subject': pat, 'encounter': enc, 'category': 'fall_prevention'}
        resp = requests.get(self.api_base + 'Observation/', headers=search_headers, params=search_params)
        if resp.json()['total'] > 0:
            for obs in resp.json()['entry']:
                if obs['resource']['code']['coding'][0]['system'] == 'fall_prevention':
                    for standards_question in standards_dict:
                        if standards_question['model'] == 'app.Question':
                            if obs['resource']['code']['coding'][0]['code'] == standards_question['pk']:
                                output_dict[str(standards_question['pk'])] = obs
        return output_dict

    # Function to create a new observation for a yes/no or true/false question.
    # Input: question_code from the standards document, response to question, patient_id, encounter_id
    # (the default uses client values if they have been set)
    # Returns: True if succeeds in creating a new procedure or False if fails.
    # Note: Some of the coding names are a bit made up. We can probably just use them.
    # Sets effective date as current date.
    def create_new_observation_yes_no(self, falls_question_code, response, pat_id=None, enc_id=None):
        if pat_id == None:
            pat_id = self.patient_id
        if enc_id == None:
            enc_id = self.encounter_id
        if not pat_id or not enc_id:
            print 'I am missing a patient_id or encounter_id to search for relevant observations'
            return None
        write_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        save_obs = {}
        save_obs['resourceType'] = "Observation"
        save_obs['status'] = "final"

        save_obs['category'] = {}
        save_obs['category']['coding'] = []
        save_obs['category']['coding'].append({})
        save_obs['category']['coding'][0]['code'] = 'fall_prevention'
        save_obs['category']['coding'][0]['display'] = 'Fall Prevention Assessment Results'
        save_obs['category']['coding'][0]['system'] = 'fall_prevention'
        save_obs['category']['coding'][0]['text'] = 'Fall Prevention Assessment Results'
        save_obs['code'] = {}
        save_obs['code']['coding'] = []
        save_obs['code']['coding'].append({})
        # save_obs['code']['coding']['system'] = 'http://fall_prevention_algorithm.org'
        save_obs['code']['coding'][0]['system'] = 'fall_prevention'
        # save_obs['code']['coding']['code'] = str(questions_code[i])
        save_obs['code']['coding'][0]['code'] = str(falls_question_code)
        # save_obs['code']['coding']['display'] = str(questions[i])
        save_obs['code']['coding'][0]['display'] = self.questions_text[self.questions_code.index(str(falls_question_code))]
        save_obs['code']['coding'][0]['text'] = self.questions_text[self.questions_code.index(str(falls_question_code))]
        save_obs['subject'] = {}
        save_obs['subject']['reference'] = 'Patient/'+str(pat_id)
        save_obs['encounter'] = {}
        save_obs['encounter']['reference'] = enc_id
        save_obs['effectiveDateTime'] = (time.strftime("%Y-%m-%dT%H:%M:%S"))
        save_obs['valueQuantity'] = {}
        save_obs['valueQuantity']['value'] = str(response)
        save_obs['valueQuantity']['unit'] = 'True or False (1 or 0)'
        save_obs['valueQuantity']['system'] = "True or False (1 or 0)"
        save_obs['valueQuantity']['code'] = "True or False (1 or 0)"
        resp = requests.post(self.api_base + 'Observation/', data=json.dumps(save_obs), headers=write_headers)
        if resp == '201':
            return True
        else:
            print 'Something went wrong when trying to write to the server'
            return False


if __name__ == "__main__":
    client = FallsFHIRClient()
    patients = client.search_patients('Sarah', 'Graham')
    print patients[0]
    client.select_patient(patients[0]['resource']['id'])
    observations = client.search_observations()
    print observations[0]

    print 'Made Client!!'
