.. winerp documentation master file, created by
   sphinx-quickstart on Wed Apr 13 21:56:45 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

API Reference
==================================

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

Client
~~~~~~

.. attributetable:: winerp.client.Client

.. autoclass:: winerp.client.Client
   :members:
   :exclude-members: route, event

   .. automethod:: winerp.client.Client.route()
      :decorator:
   
   .. automethod:: winerp.client.Client().event()
      :decorator:

Server
~~~~~~

.. attributetable:: winerp.server.Server

.. autoclass:: winerp.server.Server
   :members:

Errors
~~~~~~

.. automodule:: winerp.lib.errors
   :members: