"""Tornado handlers for the live notebook view."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from collections import namedtuple
import os
from tornado import web, gen
from tornado.httpclient import HTTPRequest,HTTPResponse,HTTPError
import tornado
from tornado import log
import requests
import json
import shutil
HTTPError = web.HTTPError

from ..base.handlers import (
    IPythonHandler, FilesRedirectHandler, path_regex,
)
from ..utils import url_escape
from ..transutils import _


def get_custom_frontend_exporters():
    from nbconvert.exporters.base import get_export_names, get_exporter

    ExporterInfo = namedtuple('ExporterInfo', ['name', 'display'])

    for name in sorted(get_export_names()):
        exporter = get_exporter(name)()
        ux_name = getattr(exporter, 'export_from_notebook', None)
        if ux_name is not None:
            display = _('{} ({})'.format(ux_name, exporter.file_extension))
            yield ExporterInfo(name, display)

## add accesstoken as global variable since token age is 24hrs
AccessToken = ''
# progress urls constants prod and stage as global variables
project_progress_url_stage = "https://fuse-ai-stage-api.fuse.ai/v1/project/progress"
assignment_progress_url_stage = "https://fuse-ai-stage-api.fuse.ai/v1/assignment/progress"
project_progress_url_prod = "https://fuse-ai-prod-api.fusemachines.com/v1/project/progress"
assignment_progress_url_prod = "https://fuse-ai-prod-api.fusemachines.com/v1/assignment/progress"
# submit urls constants prod and stage as global variables
project_submit_url_stage = 'https://fuse-ai-stage-api.fuse.ai/v1/project/submit'
assignment_submit_url_stage = 'https://fuse-ai-stage-api.fuse.ai/v1/assignment/submit'
project_submit_url_prod = 'https://fuse-ai-prod-api.fusemachines.com/v1/project/submit'
assignment_submit_url_prod = 'https://fuse-ai-prod-api.fusemachines.com/v1/assignment/submit'

## test notebook progress handler
class FuseProgressHandler(tornado.web.RequestHandler):
    ### add cors
    def set_default_headers(self):
        print('set headers!!')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', '*')
        self.set_header('Access-Control-Max-Age', 1000)
        self.set_header('Content-type', 'application/json')
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.set_header('Access-Control-Allow-Headers',
                        'Content-Type, Access-Control-Allow-Origin, Access-Control-Allow-Headers, X-Requested-By, Access-Control-Allow-Methods')

    def OPTIONS(self):
        pass

    ## post the progess
    def post(self):
    ## know if it is stage or prod
        environment = self.get_argument('environment')
    ## know if it is of Project or Assignment or playground
        value = self.get_argument('value') ## Assignment/Project Name
        type = self.get_argument('type') ## Either Assignment or Project or Playground
        email = self.get_argument('email')
        programId = self.get_argument('programId')
        batchId = self.get_argument('batchId')

        payload = {'email': email,
               'status': 'progress',
               'name': value,
               'programId':programId,
               'batchId':batchId}

        print("The payload for fuse.ai PROGRESS API is: ")
        print(payload)
        if environment=='production':
            response_json = self.get_response(type,payload, project_progress_url_prod, assignment_progress_url_prod)
        elif environment=='stage':
            response_json = self.get_response(type,payload, project_progress_url_stage, assignment_progress_url_stage)
        else :
            response_json = {'message':'The environment is other than PRODUCTION && STAGE'}
        print('Response after hitting Progress API:',response_json)
        self.flush()
        self.write(response_json)

    def get_response(self,type,payload,url_project,url_assignment):
        print('Inside the get response method')
        print(type,' ',payload,' ',url_project+' ',url_assignment)

        access_token = get_accesstoken(self)
        headers = {'Authorization':'bearer'+' '+access_token,
                   'Content-Type':'application/json'}
        print('Token: ',access_token)
        print('Headers: ',headers)
        print('Payload:  ',payload)
        print('Assignment URL ',url_assignment)
        if type =='Project':
            try:
                response = requests.post(url_project,json=payload, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as errh:
                print ("Http Error:",errh)
            except requests.exceptions.ConnectionError as errc:
                print ("Error Connecting:",errc)
            except requests.exceptions.Timeout as errt:
                print ("Timeout Error:",errt)
            except requests.exceptions.RequestException as err:
                print ("OOps: Something Else",err)
        elif type == 'Assignment':

            try :
                response = requests.post(url_assignment,json=payload, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as errh:
                print ('Http Error:',errh)
            except requests.exceptions.ConnectionError as errc:
                print ('Error Connecting:',errc)
            except requests.exceptions.Timeout as errt:
                print ('Timeout Error:',errt)
            except requests.exceptions.RequestException as err:
                print ('OOps: Something Else',err)
        print('####The response json is#####')
        print(response.json()) ## it is dict or simply JSON object
        print(response.text) ## it is str(JSON string)
        ## remember : json.loads convert str(JSON string) to dict, or simply JSON object
        ## json.dumps covert dict to json string
        ## json.dumps(response.json()) or below
        return response.text

def get_accesstoken(self):
    url = 'https://accounts-fuse-ai-stage.auth0.com/oauth/token'
    data = {
            'grant_type': 'client_credentials',
            'client_id': 'Ad1njz0gloC7SiPHY7gdnk23AUu512M2',
            'client_secret': 'kY9YEC5xuNujuGnIY2bIBq5Z_IFo3OSQ_OHaUwbGJvwuhfC5XiD7Y06Bb7jF734_',
            'audience': 'https://fuse-ai-api-stage.fusemachines.com/',
        }

    try:
        response = requests.post(url, data)
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        print('Http Error:',errh)
    except requests.exceptions.ConnectionError as errc:
        print('Error Connecting:',errc)
    except requests.exceptions.Timeout as errt:
        print('Timeout Error:',errt)
    except requests.exceptions.RequestException as err:
        print('OOPs: Something Else',err)

    response_json = json.loads(response.text)
    print('Response for the access_token: ',response_json)
    access_token = json.loads(response.text)[u'access_token']
    print('Access tokenn is: ',access_token)
    AccessToken = access_token
    return access_token

class FuseSubmitHandler(tornado.web.RequestHandler):

    def post(self):
        print("FuseSubmitHandler works like a charm")
        ## know if it is stage or prod
        environment = self.get_argument('environment')
        ## know if it is of Project or Assignment or playground
        value = self.get_argument('value')  ## Assignment/Project Name
        type = self.get_argument('type')  ## Either Assignment or Project
        email = self.get_argument('email')
        correct = self.get_argument('correct')
        score = self.get_argument('score')
        totalScore = self.get_argument('totalScore')
        programId = self.get_argument('programId')
        batchId = self.get_argument('batchId')
        ## send the assignment score to the fuse.ai
        payload = {'email': email,
                    'status': 'progress',
                     'score': score,
                     'totalScore': totalScore,
                     'correct': correct,
                     'name': value,
                     'programId': programId,
                     'batchId':batchId }

        print("The payload for fuse.ai SUBMIT API is: ")
        print(payload)
        if environment == 'production':
            response_json = self.get_submit_response(type, payload, project_submit_url_prod, assignment_submit_url_prod)
        elif environment == 'stage':
            response_json = self.get_submit_response(type, payload, project_submit_url_stage, assignment_submit_url_stage)
        else:
            response_json = {'message': 'The environment is other than PRODUCTION && STAGE'}
        print('Response after hitting Submit API:', response_json)
        self.flush()
        self.write(response_json)

    def get_submit_response(self, type, payload, url_project, url_assignment):
        print('Inside the get response method')
        print(type, ' ', payload, ' ', url_project + ' ', url_assignment)

        access_token = get_accesstoken(self)
        headers = {'Authorization': 'bearer' + ' ' + access_token,
                   'Content-Type': 'application/json'}
        print('Token: ', access_token)
        print('Headers: ', headers)
        print('Payload:  ', payload)
        print('Assignment URL ', url_assignment)
        if type == 'Project':
            try:
                response = requests.post(url_project,json=payload, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as errh:
                print ("Http Error:",errh)
            except requests.exceptions.ConnectionError as errc:
                print ("Error Connecting:",errc)
            except requests.exceptions.Timeout as errt:
                print ("Timeout Error:",errt)
            except requests.exceptions.RequestException as err:
                print ("OOps: Something Else",err)
        elif type == 'Assignment':
            print('##########################################')
            print('Dont forget it is assignment!')
            try :
                response = requests.post(url_assignment,json=payload, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as errh:
                print ('Http Error:',errh)
            except requests.exceptions.ConnectionError as errc:
                print ('Error Connecting:',errc)
            except requests.exceptions.Timeout as errt:
                print ('Timeout Error:',errt)
            except requests.exceptions.RequestException as err:
                print ('OOps: Something Else',err)
        print('The submit API response is: ',response.text)
        return response.text

class AssignmentResetHandler(tornado.web.RequestHandler):

    def post(self):
        print('Inside assignment reset handler')
        environment = self.get_argument('environment')
        assignment = self.get_argument('assignment')
        email = self.get_argument('email')
        current_user = self.get_current_user()
        print('Current user inside notebook is :',current_user)

        if os.path.exists('/tmp/assignments/fuse-ai-assignments') :
            print('fuse-ai-assignments is present')
            if os.path.exists('/tmp/assignments/fuse-ai-assignments/ai_course_id'+'/'+assignment):
                print('Assignment user wants to is rest is present')
                if os.path.exists('/home/fusemachines'+'/'+assignment):
                    print('Assignment user wants to delete is present, so lets overrite the file')
                    try :
                        shutil.copy('/tmp/assignments/fuse-ai-assignments/ai_course_id'+'/'+assignment,'/home/fusemachines'+'/'+assignment)
                    except OSError:
                        print('Oops! There was problem copying the new assignment')
            else :
                print('There is no assignment there, couldnt copy the assignment ')
        else :
            print('The path you have stated doesnot exists')

        response = {'response': 'Success',
                    'assignment': assignment,
                    'user': email,
                    'environment':environment,
                    'message': 'Notebook was successfully reset'}
        return json.dumps(response)


class NotebookHandler(IPythonHandler):
    @web.authenticated
    def get(self, path):
        """get renders the notebook template if a name is given, or 
        redirects to the '/files/' handler if the name is not given."""
        path = path.strip('/')
        cm = self.contents_manager

        print('#####################################################')
        print('This is inside the notebook')
        print('Path is: '+path)
        # will raise 404 on not found
        try:
            model = cm.get(path, content=False)
        except web.HTTPError as e:
            if e.status_code == 404 and 'files' in path.split('/'):
                # 404, but '/files/' in URL, let FilesRedirect take care of it
                return FilesRedirectHandler.redirect_to_files(self, path)
            else:
                raise
        if model['type'] != 'notebook':
            # not a notebook, redirect to files
            return FilesRedirectHandler.redirect_to_files(self, path)
        name = path.rsplit('/', 1)[-1]
        self.write(self.render_template('notebook.html',
            notebook_path=path,
            notebook_name=name,
            kill_kernel=False,
            mathjax_url=self.mathjax_url,
            mathjax_config=self.mathjax_config,
            get_custom_frontend_exporters=get_custom_frontend_exporters
            )
        )


#-----------------------------------------------------------------------------
# URL to handler mappings
#-----------------------------------------------------------------------------


default_handlers = [
    (r"/notebooks%s" % path_regex, NotebookHandler),
    (r"/progressfuse", FuseProgressHandler),
    (r"/submitfuse", FuseSubmitHandler),
    (r"/resetAssignment",AssignmentResetHandler)
]

