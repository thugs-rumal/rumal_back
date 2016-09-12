# Rumal_back
Code for Rumal Backend that will interface with Thug Daemon.

Rumal is based on a model that ensures that the backend (where the analysis will be done) and the frontend (client facing side and the social network) remain decoupled. Keeping this in mind the Backend comprises of a Django Project with models for Tasks that interacts with the Thug Daemon. The Daemon reads and writes to the models of the Django Project. The Django Project includes a message broker (Advanced Message Queuing Protocol) used by the frontend to submit tasks and receive results and files. Historical Data is moved to the frontend and is not maintained on the backend.

## Documentation

Documentation about Rumal architecture, installation and usage can be found at [http://thugs-rumal.github.io/](http://thugs-rumal.github.io/)

## License

Rumal is licensed under the GPLv2 or later. Rumal releases also include and make use of other libraries with their own separate licenses.

The license is available [here](https://github.com/pdelsante/rumal/blob/master/COPYING).