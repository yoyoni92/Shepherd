"""Feature registry: feature name -> async handler(ctx, route)."""

from __future__ import annotations

from app.flows.access import access_denied, enroll, menu
from app.flows.accident import accident
from app.flows.attendance_admin import attendance_admin
from app.flows.attendance_csv import attendance_csv
from app.flows.broadcast import broadcast
from app.flows.clock import clock
from app.flows.doc_scan import doc_scan
from app.flows.fleet_summary import fleet_summary
from app.flows.maintenance import maintenance
from app.flows.my_vehicle import my_vehicle
from app.flows.update_details import update_details
from app.flows.update_driver import update_driver
from app.flows.vehicle_issue import vehicle_issue

FEATURES = {
    "menu": menu,
    "access_denied": access_denied,
    "enroll": enroll,
    "clock": clock,
    "vehicle_issue": vehicle_issue,
    "my_vehicle": my_vehicle,
    "attendance_csv": attendance_csv,
    "update_details": update_details,
    "accident": accident,
    "attendance_admin": attendance_admin,
    "fleet_summary": fleet_summary,
    "broadcast": broadcast,
    "update_driver": update_driver,
    "maintenance": maintenance,
    "doc_scan": doc_scan,
}
