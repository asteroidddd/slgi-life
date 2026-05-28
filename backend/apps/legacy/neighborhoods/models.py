"""
Migration anchor for the removed neighborhoods app.

Runtime code and API endpoints were moved to service-specific apps. This app
keeps the historical `neighborhoods` migration label so existing applied
migrations and cross-app dependencies continue to load.
"""
