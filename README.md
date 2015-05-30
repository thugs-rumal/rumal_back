# rumal_back
Code for Rumal Backend that will interface with Thug Daemon

## Purpose & Design
Rumal is based on a model that ensures that the backend (where the analysis will be done) and the frontend (client facing side and the social network) remain decoupled. Keeping this in mind the Backend comprises of a Django Project with models for Tasks that interacts with the Thug Daemon. The Daemon reads and writes to the models of the Django Project. The Django Project includes a RESTful API that communicates with the frontend to take tasks and allow fetching of results by frontend when required. Historical Data is moved to the frontend and is not maintained on the backend.

### API
The API has two end points one for submitting Tasks and the other fo retriving Results. The APIs have been built very closely around the APIs in the orignal Rumal draft. Infact the APIs for fetching analysis are the same as their purpouse was exactly same. The API for submitting tasks has been modified to remove User and Sharing info which are irreleevant to the backend. Also an additional key is added for frontend_id which allows frontend to later fetch the results. Only API Authentication is support as users will never interact with the backend directly.

### Install

Like Rumāl's orignal draft the backend needs to make sure you are using a supported Thug version, to avoid any incompatibilities in arguments and behaviours. To do so, Thug was included as a submodule.

Requirments:
Django 1.7
Pymongo 2.6

It is also critical to have Mongo DB running in the background.

You can start by

    $ python manage.py migrate
    $ python manage.py createsuperuser

Running the web server is as simple as doing:

    $ python manage.py runserver

Or, if you want your server to be reachable from the external network:

    $ python manage.py runserver 0.0.0.0:8000

Now you can connect to the GUI by pointing your browser to http://127.0.0.1:8000/ (or to whatever IP/port you chose).
