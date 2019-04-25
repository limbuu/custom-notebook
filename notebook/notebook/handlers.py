"""Tornado handlers for the live notebook view."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from collections import namedtuple
import os
from tornado import web
from tornado.httpclient import HTTPRequest,HTTPResponse,HTTPError
import tornado
from tornado import log
import requests
import json
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
    # progress urls constants prod and stage
        project_progress_url_stage = "https://fuse-ai-stage-api.fuse.ai/v1/project/progress"
        assignment_progress_url_stage = "https://fuse-ai-stage-api.fuse.ai/v1/assignment/progress"
        project_progress_url_prod = "https://fuse-ai-prod-api.fusemachines.com/v1/project/progress"
        assignment_progress_url_prod = "https://fuse-ai-prod-api.fusemachines.com/v1/assignment/progress"

    ## know if it is stage or prod
        environment = self.get_argument('environment')
    ## know if it is of Project or Assignment or playground
        value = self.get_argument('value') ## Assignment/Project Name
        type = self.get_argument('type') ## Either Assignment or Project
        email = self.get_argument('email')

        payload = {'email': email,
               'status': 'progress',
               'name': value}

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
        self.write('Success')

    def get_response(self,value,payload,url_project,url_assignment):
        print('Inside the get response method')
        print(value,' ',payload,' ',url_project+' ',url_assignment)

        access_token = get_accesstoken(self)
        headers = {'Authorization':'bearer'+' '+access_token,
                   'Content-Type':'application/json'}
        print('Token: ',access_token)
        print('Headers: ',headers)
        print('Payload:  ',payload)
        print('Assignment URL ',url_assignment)


        if value=='Project':
            response = requests.post(url_project,json=payload, headers=headers)
        elif value == 'Assignment':
            print("####The response is#####")
            response = requests.post(url_assignment,json=payload, headers=headers)
            print(json.loads(response.text))
        else :
            response = {'message':'It is playground-practice notebook!'}
        return json.loads(response.text)

def get_accesstoken(self):
    url = 'https://accounts-fuse-ai-stage.auth0.com/oauth/token'
    data = {
            'grant_type': 'client_credentials',
            'client_id': 'Ad1njz0gloC7SiPHY7gdnk23AUu512M2',
            'client_secret': 'kY9YEC5xuNujuGnIY2bIBq5Z_IFo3OSQ_OHaUwbGJvwuhfC5XiD7Y06Bb7jF734_',
            'audience': 'https://fuse-ai-api-stage.fusemachines.com/',
        }

    response = requests.post(url, data)
    response_json = json.loads(response.text)
    print("Response for the access_token: ",response_json)
    access_token = json.loads(response.text)[u'access_token']
    print("Access tokenn is: ",access_token)
    return access_token

class FuseSubmitHandler(tornado.web.RequestHandler):

    def post(self):
        project_submit_url_stage = 'https://fuse-ai-stage-api.fuse.ai/v1/project/submit'
        assignment_submit_url_stage = 'https://fuse-ai-stage-api.fuse.ai/v1/assignment/submit'
        project_submit_url_prod = 'https://fuse-ai-prod-api.fusemachines.com/v1/project/submit'
        assignment_submit_url_prod = 'https://fuse-ai-prod-api.fusemachines.com/v1/assignment/submit'

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
        ## send the assignment score to the fuse.ai
        payload = {'email': email,
                    'status': 'progress',
                     'score': score,
                     'totalScore': totalScore,
                     'correct': correct,
                     'name': value }

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
        self.write('Success')

    def get_submit_response(self, value, payload, url_project, url_assignment):
        print('Inside the get response method')
        print(value, ' ', payload, ' ', url_project + ' ', url_assignment)

        access_token = get_accesstoken(self)
        headers = {'Authorization': 'bearer' + ' ' + access_token,
                   'Content-Type': 'application/json'}
        print('Token: ', access_token)
        print('Headers: ', headers)
        print('Payload:  ', payload)
        print('Assignment URL ', url_assignment)
        if value == 'Project':
            response = requests.post(url_project, json=payload, headers=headers)
        elif value == 'Assignment':
            print("##########################################")
            print("Dont forget it is assignment!")
            response = requests.post(url_assignment, json=payload,headers=headers)
        else:
            response = {'message': 'It is playground-practice notebook!'}
        print('The submit API response is: ',json.loads(response.text))
        return json.loads(response.text)


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
    (r"/submitfuse", FuseSubmitHandler)
]

