'''
E2E test cases using the REST API
'''

TEST_TENANT = 'test'
BASE_URL = 'http://127.0.0.1:8000'

import os
import importlib.util
import json
import argparse
from urllib import request
import requests
import time
import sys

parser = argparse.ArgumentParser(description='Runs test cases for mapper')
parser.add_argument('-f', '--folder', nargs='?', help='folder name')
parser.add_argument('-t', '--test', nargs='?', help='test number')
parser.add_argument('--nocdscompile', help='no cds compiliation', action='store_true')
parser.add_argument('--tenant', nargs='?', help='test tenant')
parser.add_argument('--nocleanup', help='no cleanup after test execution', action='store_true')
args = parser.parse_args()

current_path = sys.path[0]
src_path = current_path[:-len('tests')] + 'src'
sys.path.append(src_path)

def round_dict(d, k):
    if k in d:
        d[k] = round(d[k], 1)

def round_esh_response(res):
    round_dict(res, '@com.sap.vocabularies.Search.v1.ResponseTime')
    round_dict(res, '@com.sap.vocabularies.Search.v1.SearchTime')
    if '@com.sap.vocabularies.Search.v1.SearchStatistics' in res and 'ConnectorStatistics' in res['@com.sap.vocabularies.Search.v1.SearchStatistics']:
        for c in res['@com.sap.vocabularies.Search.v1.SearchStatistics']['ConnectorStatistics']:
            round_dict(c, '@com.sap.vocabularies.Search.v1.SearchTime')
            round_dict(c, '@com.sap.vocabularies.Search.v1.CPUTime')
    return res

folders = next(os.walk(current_path))[1]

# Check passed arguments
if args.test and not args.folder:
    print(f'Error. Test number provided but no --folder')
    exit(-1)
if args.folder:
    if args.folder in folders:
        folders = [args.folder]
    else:
        print(f'Error. Folder {args.folder} does not exit')
        exit(-1)
    if args.test:
        selected_cds_file_name = str(args.test).zfill(2) + '.cds'
        selected_cson_file_name = str(args.test).zfill(2) + '.cson.json'
        if not os.path.exists(os.path.join(current_path, args.folder, selected_cds_file_name)):
            print(f'Test number {args.test} does not exist in folder {args.folder}')
            exit(-1)
        if args.nocdscompile:
            if not os.path.exists(os.path.join(current_path, args.folder, selected_cson_file_name)):
                print(f'CSON file does not exist for test number {args.test} does not exist in folder {args.folder}')
                exit(-1)

if args.tenant:
    tenant_name = args.tenant
else:
    tenant_name = TEST_TENANT


for folder in folders:
    folder_path = os.path.join(current_path, folder)
    if args.test:
        file_names = set([str(args.test).zfill(2) + '.cds'])
    else:
        file_names = set(os.listdir(folder_path))
    # use cds compiler to convert cds files to cson files
    if not args.nocdscompile:
        for file_name in file_names:
            if file_name.endswith('.cds'):
                cds_file_name = file_name
                cson_file_name = cds_file_name[:-4] + '.cson.json'
                full_cds_file_name = os.path.join(folder_path, cds_file_name)
                full_cson_file_name = os.path.join(folder_path, cson_file_name)
                command_line_statement = f'cds compile {full_cds_file_name} --to json > {full_cson_file_name}'
                print(command_line_statement)
                os.system(command_line_statement)

    if args.test:
        cson_file_names = [selected_cson_file_name]
    else:
        cson_file_names = [w for w in os.listdir(folder_path) if w.endswith('.cson.json')]

    for cson_file_name in cson_file_names:
        test_name = cson_file_name[:-10]
        data_file_name = test_name + '.data.json'
        search_request_file_name = test_name + '.searchRequest.json'
        search_response_file_name = test_name + '.searchResponse.json'
        if os.path.exists(os.path.join(folder_path, search_request_file_name)):
            with open(os.path.join(folder_path, search_request_file_name), encoding = 'utf-8') as f:
                search_request = json.load(f)
        else:
            search_request = None
        if os.path.exists(os.path.join(folder_path, data_file_name)):
            with open(os.path.join(folder_path, cson_file_name), encoding = 'utf-8') as f:
                cson = json.load(f)
            with open(os.path.join(folder_path, data_file_name), encoding = 'utf-8') as f:
                data = json.load(f)
            res = []
            r = requests.delete(f'{BASE_URL}/v1/tenant/{tenant_name}')
            ts = time.time()
            r = requests.post(f'{BASE_URL}/v1/tenant/{tenant_name}')
            res.append(r.status_code)
            r = requests.post(f'{BASE_URL}/v1/deploy/{tenant_name}', json=cson)
            res.append(r.status_code)
            r = requests.post(f'{BASE_URL}/v1/data/{tenant_name}', json=data)
            res.append(r.status_code)
            if search_request:
                tstart = time.time()
                r = requests.post(f'{BASE_URL}/v1/search/{tenant_name}', json=search_request)
                print(time.time() - tstart)
                res.append(r.status_code)
                with open(os.path.join(folder_path, search_response_file_name), 'w', encoding = 'utf-8') as fw:
                    search_response = [round_esh_response(w) for w in r.json()]
                    json.dump(search_response, fw, indent=4)
            if not args.nocleanup:
                r = requests.delete(f'{BASE_URL}/v1/tenant/{tenant_name}')
                res.append(r.status_code)
            trun = round((time.time() - ts), 1)
            if set(res) == set([200]):
                print(f'Test {folder}.{test_name} sucessfully executed in {trun} s')
            else:
                res_str = ', '.join([str(w) for w in res])
                print(f'Test {folder}.{test_name} failed with HTTP codes {res_str} in {trun} s')
